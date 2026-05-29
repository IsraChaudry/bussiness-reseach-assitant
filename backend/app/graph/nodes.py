from app.graph.state import AgentState
from app.services import llm_service, tavily_service
from app.services.session_store import set_active_agent


# ---------------------------------------------------------------------------
# 1. Clarity Agent
# ---------------------------------------------------------------------------

def clarity_agent(state: AgentState) -> AgentState:
    """Decide whether the user query is specific enough to research."""
    set_active_agent(state["session_id"], "Clarity Agent")
    state["debug_steps"].append("clarity_agent")

    # Short-circuit: clarity already resolved externally (e.g. after clarification answer).
    if state.get("clarity_status") == "clear" and state.get("company_name"):
        state["needs_clarification"] = False
        if not state.get("clarified_query"):
            state["clarified_query"] = state["user_query"]
        return state

    user_query = state["user_query"]
    messages = state.get("messages", [])
    company_name = state.get("company_name")

    # Build conversation history summary for the LLM
    history_text = ""
    if messages:
        history_text = "\n".join(
            f"{m['role'].capitalize()}: {m['content']}" for m in messages[-6:]
        )

    system_prompt = (
        "You are a query clarity checker for a business research assistant. "
        "Your job is to determine if the user's query is specific enough to research a company.\n\n"
        "Rules — apply in order, stop at the first match:\n"
        "1. If a proper noun, brand name, or company name appears anywhere in the query, "
        "   mark as 'clear' and extract that name.\n"
        "2. If the query is a short follow-up or uses pronouns ('them', 'their', 'its', "
        "   'the company', 'the CEO', 'what about', 'more', etc.) AND a company is known "
        "   from session context or conversation history, resolve it and mark as 'clear'.\n"
        "3. If the session already has a company context, ALWAYS prefer using it over asking "
        "   for clarification — only ask when there is genuinely zero way to identify a company.\n"
        "4. Only mark 'needs_clarification' when NO company name can be identified at all "
        "   and there is no session context whatsoever.\n\n"
        "IMPORTANT: Do NOT ask for clarification when a name is already present in the query "
        "or when a company is known from session. Treat 'research X' as clear.\n\n"
        "Respond ONLY with a valid JSON object. No explanation, no markdown.\n"
        "JSON fields:\n"
        "  clarity_status: 'clear' or 'needs_clarification'\n"
        "  clarification_question: string or null\n"
        "  company_name: string or null\n"
        "  clarified_query: string (explicit resolved query)"
    )

    user_prompt = (
        f"Session company context: {company_name or 'None'}\n\n"
        f"Conversation history:\n{history_text or 'No history yet'}\n\n"
        f"Current user query: {user_query}"
    )

    result = llm_service.call_llm_json(system_prompt, user_prompt)

    resolved_company = result.get("company_name") or company_name
    resolved_status  = result.get("clarity_status", "needs_clarification")

    # Hard override: if the LLM identified ANY company name, it must be clear.
    # Never ask for confirmation when a company is already in hand.
    if resolved_company:
        resolved_status = "clear"

    state["clarity_status"]        = resolved_status
    state["company_name"]          = resolved_company
    state["clarified_query"]       = result.get("clarified_query") or user_query
    state["clarification_question"] = result.get("clarification_question") if resolved_status == "needs_clarification" else None
    state["needs_clarification"]   = resolved_status == "needs_clarification"

    return state


# ---------------------------------------------------------------------------
# 2. Research Agent
# ---------------------------------------------------------------------------

def research_agent(state: AgentState) -> AgentState:
    """Search for company information using Tavily and assess confidence."""
    set_active_agent(state["session_id"], "Research Agent")
    state["debug_steps"].append("research_agent")
    state["attempts"] = state.get("attempts", 0) + 1

    query = state.get("clarified_query") or state["user_query"]
    company = state.get("company_name", "")

    # Build search queries
    search_queries = [query]
    if company and company.lower() not in query.lower():
        search_queries.append(f"{company} company overview recent news")

    all_results: list[dict] = []
    for q in search_queries:
        results = tavily_service.search(q, max_results=5)
        all_results.extend(results)

    # Deduplicate by URL
    seen_urls: set = set()
    unique_results: list[dict] = []
    for r in all_results:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            unique_results.append(r)

    state["sources"] = unique_results[:8]

    # Summarize findings with LLM
    sources_text = "\n\n".join(
        f"Source: {r['title']}\nURL: {r['url']}\nContent: {r['content'][:600]}"
        for r in unique_results[:6]
    )

    system_prompt = (
        "You are a business research analyst. Given search results, extract and summarize "
        "relevant business information. Focus on: company overview, recent news, financials, "
        "leadership, competitors, and recent developments as relevant to the query.\n\n"
        "Also provide a confidence score (0-10) based on:\n"
        "- 8-10: Company clearly identified, multiple relevant sources, query fully answerable\n"
        "- 5-7: Company identified, some relevant sources, query mostly answerable\n"
        "- 0-4: Weak or ambiguous results, query hard to answer\n\n"
        "Respond ONLY with a valid JSON object. Do not include any explanation, markdown, or extra text.\n"
        "JSON fields:\n"
        "  findings: string (detailed research summary)\n"
        "  confidence_score: integer 0-10"
    )

    user_prompt = (
        f"Research query: {query}\n"
        f"Company: {company or 'Unknown'}\n\n"
        f"Search results:\n{sources_text or 'No results found.'}"
    )

    result = llm_service.call_llm_json(system_prompt, user_prompt)

    state["research_findings"] = result.get("findings", "No findings available.")
    state["confidence_score"] = int(result.get("confidence_score", 0))

    return state


# ---------------------------------------------------------------------------
# 3. Validator Agent
# ---------------------------------------------------------------------------

def validator_agent(state: AgentState) -> AgentState:
    """Check whether research quality is sufficient to synthesize an answer."""
    set_active_agent(state["session_id"], "Validator Agent")
    state["debug_steps"].append("validator_agent")

    query = state.get("clarified_query") or state["user_query"]
    findings = state.get("research_findings", "")
    sources = state.get("sources", [])
    attempts = state.get("attempts", 1)

    system_prompt = (
        "You are a research quality validator for a business research assistant. "
        "Assess whether the research findings adequately answer the user's query.\n\n"
        "Consider:\n"
        "- Relevance: Do findings address what the user asked?\n"
        "- Completeness: Is enough information present for a useful answer?\n"
        "- Source quality: Are sources credible and relevant?\n"
        "- Actionability: Can a clear answer be synthesized from this?\n\n"
        f"This is research attempt #{attempts}. If attempts >= 3, always return 'sufficient' "
        "to avoid infinite loops.\n\n"
        "Respond ONLY with a valid JSON object. Do not include any explanation, markdown, or extra text.\n"
        "JSON fields:\n"
        "  validation_result: 'sufficient' or 'insufficient'\n"
        "  validation_notes: string (brief explanation)"
    )

    sources_summary = f"{len(sources)} sources found" if sources else "No sources"
    user_prompt = (
        f"User query: {query}\n"
        f"Sources: {sources_summary}\n\n"
        f"Research findings:\n{findings}"
    )

    result = llm_service.call_llm_json(system_prompt, user_prompt)

    # Force sufficient if we've already tried 3 times
    if attempts >= 3:
        state["validation_result"] = "sufficient"
        state["validation_notes"] = "Max attempts reached; proceeding with available findings."
    else:
        state["validation_result"] = result.get("validation_result", "sufficient")
        state["validation_notes"] = result.get("validation_notes", "")

    return state


# ---------------------------------------------------------------------------
# 4. Synthesis Agent
# ---------------------------------------------------------------------------

def synthesis_agent(state: AgentState) -> AgentState:
    """Create the final structured, user-facing answer."""
    set_active_agent(state["session_id"], "Synthesis Agent")
    state["debug_steps"].append("synthesis_agent")

    query = state.get("clarified_query") or state["user_query"]
    findings = state.get("research_findings", "")
    sources = state.get("sources", [])
    messages = state.get("messages", [])
    company = state.get("company_name", "")

    history_text = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}" for m in messages[-6:]
    ) if messages else "No prior conversation."

    sources_text = "\n".join(
        f"- [{r['title']}]({r['url']})" for r in sources[:5] if r.get("url")
    )

    system_prompt = (
        "You are a professional business research analyst writing a report for a user. "
        "Using the research findings and conversation context, write a clear, well-structured answer. "
        "Use sections and bullet points where helpful. Be concise but complete. "
        "If sources are available, reference them naturally. "
        "Tailor the response to what the user specifically asked — don't dump everything."
    )

    user_prompt = (
        f"User query: {query}\n"
        f"Company: {company or 'N/A'}\n\n"
        f"Conversation history:\n{history_text}\n\n"
        f"Research findings:\n{findings}\n\n"
        f"Available sources:\n{sources_text or 'None'}"
    )

    final_answer = llm_service.call_llm(system_prompt, user_prompt)
    state["final_answer"] = final_answer

    return state
