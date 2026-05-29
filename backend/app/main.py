import re
import random

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import BACKEND_CORS_ORIGINS
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.session_store import get_session, update_session, append_message, set_active_agent, get_active_agent
from app.graph.workflow import run_graph
from app.graph.state import AgentState

app = FastAPI(title="Business Research Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status/{session_id}")
def status(session_id: str):
    return get_active_agent(session_id)


CONVERSATIONAL = {
    "ok", "okay", "k", "sure", "yes", "yep", "yeah", "no", "nope",
    "got it", "got that", "i see", "i got it", "understood",
    "thanks", "thank you", "thx", "ty", "great", "cool", "nice",
    "good", "alright", "fine", "noted", "awesome", "perfect",
    "go on", "continue", "more", "and", "so", "hmm", "hm",
    "oki", "oki!", "lol", "lmao", "haha", "hehe", "nice one",
}

# Matches elongated conversational words like "okiiii", "yayyy", "thanksss", "sureeee"
_CONVERSATIONAL_RE = re.compile(
    r"^("
    r"o+k+[iy!]*|"
    r"okay+|"
    r"ye+s+|ye+p+|ye+a+h*|"
    r"no+p*e*|"
    r"su+re+|"
    r"alright+|"
    r"thanks+|thank\s*you+|thx+|ty+|"
    r"great+|cool+|nice+|awesome+|perfect+|noted+|good+|"
    r"hmm+|hm+|uh+|ah+|"
    r"lol+|lmao+|haha+|hehe+"
    r")[!?. ]*$",
    re.IGNORECASE,
)

def _conversational_reply(company: str | None) -> str:
    if company:
        templates = [
            f"Glad I could help with **{company}**! Let me know if you want to dig deeper — financials, leadership, competitors, or anything else.",
            f"Happy to help! If you have more questions about **{company}** or want to explore another company, just ask.",
            f"Got it! I've pulled up what I know about **{company}**. Want me to look into a specific angle — like their recent news or key rivals?",
            f"No problem! Feel free to ask a follow-up about **{company}**, or just name another company and I'll research it for you.",
            f"Sure thing! We can keep exploring **{company}** or switch to a different company whenever you're ready.",
        ]
    else:
        templates = [
            "Of course! Whenever you're ready, just name a company and I'll research it for you.",
            "Sure! Type something like **'Research Tesla'** or **'Tell me about Apple's competitors'** and I'll get started.",
            "Ready when you are! Just give me a company name and I'll dig in.",
            "No problem — just drop a company name whenever you'd like and I'll pull up the research.",
            "Happy to help! Ask me about any company — financials, news, leadership, competitors — whenever you're ready.",
        ]
    return random.choice(templates)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id
    user_message = request.message.strip()

    session = get_session(session_id)

    # Intercept pure conversational replies (ok, okiiii, thanks, sure, etc.)
    # — skip the graph entirely and reply with a context-aware friendly message.
    normalized = user_message.lower().strip()
    is_conversational = (normalized in CONVERSATIONAL or bool(_CONVERSATIONAL_RE.match(normalized)))
    if is_conversational and not session.get("pending_clarification"):
        reply = _conversational_reply(session.get("company_name"))
        append_message(session_id, "user", request.message)
        append_message(session_id, "assistant", reply)
        return ChatResponse(answer=reply, needs_clarification=False)

    # Pre-resolved clarity fields (set when clarification has already been answered)
    pre_clarity_status = None
    pre_company_name = session.get("company_name")
    pre_clarified_query = None

    # Handle clarification response: user's message IS the company name / answer
    if session.get("pending_clarification") and session.get("pending_query"):
        original_query = session["pending_query"]
        company_answer = user_message  # e.g. "Tesla", "Claude AI", "Apple"

        # Build a clean, explicit query instead of a confusing concatenation
        user_message = f"{original_query} — company: {company_answer}"

        # Pre-resolve clarity so the Clarity Agent doesn't ask again
        pre_clarity_status = "clear"
        pre_company_name = company_answer
        pre_clarified_query = f"{original_query} {company_answer}"

        update_session(session_id, {
            "pending_clarification": False,
            "pending_query": None,
            "company_name": company_answer,
        })

    append_message(session_id, "user", request.message)

    # Build initial LangGraph state
    state: AgentState = {
        "session_id": session_id,
        "messages": session["messages"][:-1],  # history before current message
        "user_query": user_message,
        "clarified_query": pre_clarified_query,
        "company_name": pre_company_name,
        "clarity_status": pre_clarity_status,
        "clarification_question": None,
        "research_findings": None,
        "sources": [],
        "confidence_score": None,
        "validation_result": None,
        "validation_notes": None,
        "attempts": 0,
        "final_answer": None,
        "needs_clarification": False,
        "debug_steps": [],
    }

    try:
        result_state = run_graph(state)
    except Exception as exc:
        err_str = str(exc).lower()
        if "rate limit" in err_str or "429" in err_str or "tokens per day" in err_str:
            fallback = (
                "**Rate limit reached.** You've hit Groq's free-tier daily token limit (100,000 tokens/day). "
                "Please wait a few minutes for it to reset, then try again. "
                "You can also upgrade at [console.groq.com/settings/billing](https://console.groq.com/settings/billing)."
            )
        else:
            fallback = "Sorry, I ran into a technical issue. Please try again in a moment."
        append_message(session_id, "assistant", fallback)
        return ChatResponse(answer=fallback, needs_clarification=False, debug={"error": str(exc)})
    finally:
        set_active_agent(session_id, None)

    # Handle clarification needed
    if result_state.get("needs_clarification"):
        clarification_q = (
            result_state.get("clarification_question")
            or "Could you please clarify which company you are asking about?"
        )
        update_session(session_id, {
            "pending_clarification": True,
            "pending_query": request.message,
        })
        append_message(session_id, "assistant", clarification_q)
        return ChatResponse(
            needs_clarification=True,
            clarification_question=clarification_q,
            debug={"steps": result_state.get("debug_steps", [])},
        )

    # Persist resolved company name for follow-up queries
    if result_state.get("company_name"):
        update_session(session_id, {"company_name": result_state["company_name"]})

    final_answer = result_state.get("final_answer") or "I was unable to find relevant information for your query."
    append_message(session_id, "assistant", final_answer)

    sources = [s for s in result_state.get("sources", []) if s.get("url")]

    return ChatResponse(
        answer=final_answer,
        needs_clarification=False,
        sources=sources[:5],
        debug={
            "steps": result_state.get("debug_steps", []),
            "confidence_score": result_state.get("confidence_score"),
            "attempts": result_state.get("attempts"),
            "validation_result": result_state.get("validation_result"),
        },
    )
