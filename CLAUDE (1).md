# CLAUDE.md

## Project Goal

Build a production-grade full-stack AI application for a take-home assignment.

The application is a **Multi-Agent Business Research Assistant** using **LangGraph**. It helps users research businesses by collecting company data, recent news, financial information, competitors, leadership details, and recent developments.

The system must support:

- 4 specialized agents
- LangGraph conditional routing
- Human-in-the-loop clarification
- Multi-turn conversation memory
- Follow-up questions
- Tavily search-based research
- FastAPI backend
- Simple React frontend
- Clean, production-style code
- Easy ZIP submission

This project is for an internship take-home assignment. Keep the implementation realistic, clean, understandable, and easy to demo.

---

## Important Assignment Rules

The assignment allows AI tools, but the final code should be understandable and explainable by the developer.

Do not create an over-engineered system.

Do not use GitHub, YouTube, or public posting.

The final submission must include:

- All code and related files
- A text document listing AI prompts used and reasoning
- A short screen-recording demo
- A ZIP folder containing the full project

---

## Required Tech Stack

### Backend

Use:

- Python
- FastAPI
- LangGraph
- LangChain
- Tavily API for search
- Pydantic
- Uvicorn
- python-dotenv
- **groq** (Python SDK: `groq`)

**LLM Provider: Groq**

Use the Groq API as the sole LLM provider. Do NOT use OpenAI or Anthropic.

Preferred Groq model: `llama-3.3-70b-versatile`

Keep the model name configurable via environment variables.

### Frontend

Use:

- React
- TypeScript
- Vite
- Basic CSS or Tailwind if already convenient

Keep frontend simple and clean.

---

## Required Folder Structure

Create this structure:

```text
business-research-assistant/
  backend/
    app/
      main.py
      config.py

      graph/
        state.py
        nodes.py
        workflow.py

      services/
        tavily_service.py
        llm_service.py
        session_store.py

      schemas/
        chat.py

    requirements.txt
    .env.example

  frontend/
    src/
      App.tsx
      main.tsx

      components/
        ChatWindow.tsx
        MessageBubble.tsx

      api/
        chat.ts

      styles.css

    package.json
    index.html
    vite.config.ts
    tsconfig.json

  README.md
  AI_PROMPTS_USED.md
  CLAUDE.md
  .gitignore
```

---

## Core Backend API Requirement

Create a FastAPI backend with a `/chat` endpoint.

### Request Body

```json
{
  "session_id": "string",
  "message": "string"
}
```

### Response Body

```json
{
  "answer": "string",
  "needs_clarification": false,
  "clarification_question": null,
  "sources": [],
  "debug": {}
}
```

If clarification is needed:

```json
{
  "answer": null,
  "needs_clarification": true,
  "clarification_question": "Which company are you asking about?",
  "sources": [],
  "debug": {}
}
```

---

## LLM Service — Groq

Implement `backend/app/services/llm_service.py` using the Groq Python SDK.

### Rules

- Read `GROQ_API_KEY` and `GROQ_MODEL` from environment variables.
- Default model: `llama-3.3-70b-versatile`
- Do NOT import or use `openai`, `anthropic`, or LangChain LLM wrappers.
- Use the `groq` Python package directly.
- Provide a simple reusable function for making LLM calls.
- Support structured JSON output by prompting the model to respond in JSON.
- Include safe JSON parsing with a fallback.
- Never hardcode the API key.

### Example Service Structure

```python
import os
import json
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Call Groq LLM and return the text response."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


def call_llm_json(system_prompt: str, user_prompt: str) -> dict:
    """Call Groq LLM expecting a JSON response. Falls back to empty dict on failure."""
    raw = call_llm(system_prompt, user_prompt)
    try:
        # Strip markdown code fences if model wraps output
        clean = raw.strip().strip("```json").strip("```").strip()
        return json.loads(clean)
    except Exception:
        return {}
```

### When Using JSON Mode in Agents

Always add an explicit instruction at the end of the system prompt such as:

```
Respond ONLY with a valid JSON object. Do not include any explanation, markdown, or extra text.
```

---

## Environment Variables

### Required `.env` File

Create `backend/.env` based on `backend/.env.example`.

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
TAVILY_API_KEY=your_tavily_api_key_here
BACKEND_CORS_ORIGINS=http://localhost:5173
```

### `.env.example`

```env
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
TAVILY_API_KEY=
BACKEND_CORS_ORIGINS=http://localhost:5173
```

Do NOT commit `.env` to any version control.

---

## `requirements.txt`

```
fastapi
uvicorn[standard]
python-dotenv
pydantic
langgraph
langchain
langchain-core
tavily-python
groq
```

Do NOT include `openai`, `anthropic`, `langchain-openai`, or `langchain-anthropic`.

---

## Config Module

Implement `backend/app/config.py`:

```python
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
BACKEND_CORS_ORIGINS: list[str] = os.getenv(
    "BACKEND_CORS_ORIGINS", "http://localhost:5173"
).split(",")
```

---

## Required Agents

The LangGraph system must have exactly 4 specialized agents implemented in `backend/app/graph/nodes.py`.

All agents must use the Groq LLM service (`llm_service.py`).

---

### 1. Clarity Agent

**Purpose:** Decide whether the user query is specific enough to research.

**Checks:**
- Is a company name provided?
- Can the query be resolved using conversation history?
- Is the query too vague?
- Is clarification needed?

**Examples of unclear queries (when no previous context exists):**
```
Tell me about them
Research this company
What about competitors?
Tell me about the CEO
```

**Examples of clear queries:**
```
Research Tesla
Tell me about Tesla competitors
Compare Apple and Microsoft recent AI developments
What about their competitors?   ← clear IF previous company is in session memory
```

**Output fields to update in state:**
```python
clarity_status: "clear" | "needs_clarification"
clarification_question: str | None
company_name: str | None
clarified_query: str
```

**Routing:**
- `needs_clarification` → interrupt, return clarification question to user
- `clear` → route to Research Agent

---

### 2. Research Agent

**Purpose:** Search for company information using Tavily.

**Must use:** `tavily_service.py` — real API calls, no mocked results unless `TAVILY_API_KEY` is missing.

**Collects:**
- Company overview
- Recent news
- Financial information if available
- Competitors if asked
- Leadership/CEO if asked
- Relevant sources

**Output fields to update in state:**
```python
research_findings: str
sources: list
confidence_score: int   # 0–10
attempts: int
```

**Confidence guidance:**
- High (>=6): company clearly identified, relevant sources found, query answerable
- Low (<6): weak results, ambiguous company, missing sources

**Routing:**
- `confidence_score < 6` → Validator Agent
- `confidence_score >= 6` → Synthesis Agent

---

### 3. Validator Agent

**Purpose:** Check whether research quality is sufficient.

**Assesses:**
- Relevance of findings
- Completeness
- Source quality
- Whether the findings answer the user's query
- Whether another research attempt is warranted

**Output fields to update in state:**
```python
validation_result: "sufficient" | "insufficient"
validation_notes: str
attempts: int
```

**Routing:**
- `insufficient` AND `attempts < 3` → back to Research Agent
- `sufficient` → Synthesis Agent
- `attempts >= 3` → Synthesis Agent (force proceed)

---

### 4. Synthesis Agent

**Purpose:** Create the final user-facing response.

**Must:**
- Use research findings and conversation history
- Answer the user's actual question
- Preserve context across turns
- Structure the response clearly with sections/bullets
- Include sources if available
- Be concise and demo-friendly

**Output fields to update in state:**
```python
final_answer: str
```

**Routing:** → `END`

---

## LangGraph Flow

```text
START
  |
Clarity Agent
  |-- (needs_clarification) --> INTERRUPT --> return clarification question to user
  |-- (clear)
Research Agent
  |-- (confidence_score < 6)
Validator Agent
  |-- (insufficient AND attempts < 3) --> back to Research Agent
  |-- (sufficient OR attempts >= 3)
Synthesis Agent
  |
END
```

If confidence is high (>=6), skip Validator:
```text
Research Agent --> Synthesis Agent --> END
```

---

## State Schema

Implement in `backend/app/graph/state.py`:

```python
from typing import TypedDict, List, Optional, Dict, Any


class AgentState(TypedDict):
    session_id: str
    messages: List[Dict[str, str]]

    user_query: str
    clarified_query: Optional[str]

    company_name: Optional[str]

    clarity_status: Optional[str]
    clarification_question: Optional[str]

    research_findings: Optional[str]
    sources: List[Dict[str, Any]]
    confidence_score: Optional[int]

    validation_result: Optional[str]
    validation_notes: Optional[str]

    attempts: int

    final_answer: Optional[str]

    needs_clarification: bool
    debug_steps: List[str]
```

---

## Tavily Service

Implement `backend/app/services/tavily_service.py`:

```python
import os
from tavily import TavilyClient

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY", ""))


def search(query: str, max_results: int = 5) -> list[dict]:
    """Search using Tavily and return normalized results."""
    try:
        response = client.search(query=query, max_results=max_results)
        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
            })
        return results
    except Exception as e:
        print(f"[Tavily Error] {e}")
        return []
```

---

## Session Store

Implement `backend/app/services/session_store.py` as a simple in-memory store:

```python
from typing import Dict, Any

SESSION_STORE: Dict[str, Dict[str, Any]] = {}


def get_session(session_id: str) -> Dict[str, Any]:
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = {
            "messages": [],
            "company_name": None,
            "last_query": None,
            "pending_clarification": False,
            "pending_query": None,
        }
    return SESSION_STORE[session_id]


def update_session(session_id: str, data: Dict[str, Any]) -> None:
    session = get_session(session_id)
    session.update(data)


def append_message(session_id: str, role: str, content: str) -> None:
    session = get_session(session_id)
    session["messages"].append({"role": role, "content": content})
```

### Conversation Memory Behavior

Memory must support follow-up questions:

```text
User: Research Tesla
Assistant: [Tesla research]

User: What about their competitors?
--> System resolves "their" to Tesla from session memory

User: Tell me more about the CEO
--> System resolves company from previous session context
```

When a query is ambiguous:

```text
User: Tell me about them
--> Store: { pending_clarification: true, pending_query: "Tell me about them" }
--> Return: { needs_clarification: true, clarification_question: "Which company are you asking about?" }

User: Tesla
--> Combine pending_query + clarification answer
--> Resolved query: "Tell me about Tesla"
--> Continue workflow normally
```

---

## Workflow Module

Implement `backend/app/graph/workflow.py` to build and compile the LangGraph graph.

- Import all agent node functions from `nodes.py`
- Define conditional edges using the routing logic described above
- Compile to a runnable graph
- Export a single `run_graph(state: AgentState) -> AgentState` function

---

## Main FastAPI App

Implement `backend/app/main.py`:

- Include CORS middleware using `BACKEND_CORS_ORIGINS` from config
- Define `POST /chat` endpoint
- Accept `ChatRequest`, return `ChatResponse` (from `schemas/chat.py`)
- Load session state, inject into graph, run graph, update session
- Handle clarification flow using session `pending_clarification` flag

---

## Schemas

Implement `backend/app/schemas/chat.py`:

```python
from pydantic import BaseModel
from typing import Optional, List, Any, Dict


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    answer: Optional[str] = None
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    sources: List[Dict[str, Any]] = []
    debug: Dict[str, Any] = {}
```

---

## Frontend Requirements

Create a simple React + TypeScript chat app using Vite.

### Features

- Chat input box
- Scrollable message history
- User and assistant message bubbles styled differently
- Loading indicator while waiting for response
- Display clarification questions prominently
- Send clarification as a normal user message
- Display sources as clickable links under assistant answers
- `session_id` stored in React state (generate a UUID on load)
- Call `POST http://localhost:8000/chat`

### `api/chat.ts`

```typescript
export async function sendMessage(sessionId: string, message: string) {
  const res = await fetch("http://localhost:8000/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  return res.json();
}
```

UI does not need to be fancy. Keep it clean and demo-ready.

---

## Backend Coding Standards

- Clean, readable Python with type hints
- Pydantic for request/response models
- No hardcoded API keys anywhere
- CORS enabled for frontend
- Graceful error handling with meaningful messages
- Small focused functions
- Comments only where logic is non-obvious
- No databases, Docker, or auth unless explicitly asked

---

## Backend Commands

```bash
cd backend
python -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

---

## Frontend Commands

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`
Backend: `http://localhost:8000`

---

## Demo Scenarios to Support

### Scenario 1 — Direct Research

```
User: Research Tesla
```

Expected: Clarity Agent marks clear --> Research Agent (Tavily) --> Synthesis Agent --> structured summary with sources

---

### Scenario 2 — Follow-up with Context

```
User: What about their competitors?
```

Expected: System uses Tesla from session memory --> researches Tesla competitors

---

### Scenario 3 — Follow-up on Leadership

```
User: Tell me more about the CEO
```

Expected: System resolves company from session --> researches Tesla CEO

---

### Scenario 4 — Ambiguous Query + Clarification

```
User: Tell me about them
--> "Which company are you asking about?"

User: Tesla
--> Resolves to "Tell me about Tesla" --> continues workflow
```

---

### Scenario 5 — Multi-Company Comparison

```
User: Compare Apple and Microsoft recent AI developments
```

Expected: Clear query --> research both --> structured comparison

---

## Required README.md

Generate a `README.md` with:

- Project title and overview
- Architecture explanation
- ASCII/text architecture diagram
- Agent descriptions (all 4)
- Setup instructions
- Backend and frontend run commands
- Environment variables table
- Demo scenarios
- Known limitations and tradeoffs

---

## Required AI_PROMPTS_USED.md

Create `AI_PROMPTS_USED.md` with honest entries, for example:

```md
# AI Prompts Used

## Prompt 1: Architecture Planning
Prompt: "Help me design a LangGraph multi-agent research assistant with clarity, research, validator, and synthesis agents."
Reasoning: Used to plan the system architecture and agent responsibilities.

## Prompt 2: Groq LLM Integration
Prompt: "Show how to call the Groq API using the groq Python SDK for a multi-agent LangGraph system."
Reasoning: Used to implement the LLM service using Groq instead of OpenAI.

## Prompt 3: LangGraph Routing
Prompt: "Show how to implement conditional routing in LangGraph for clarity, research confidence, and validation loops."
Reasoning: Used to correctly implement the graph routing logic.

## Prompt 4: FastAPI Structure
Prompt: "Create a clean FastAPI project structure for a LangGraph backend with a /chat endpoint."
Reasoning: Used to organize backend files cleanly.

## Prompt 5: Frontend Chat UI
Prompt: "Create a simple React TypeScript chat interface for a multi-turn assistant with sources and clarification handling."
Reasoning: Used to build the demo frontend.

## Prompt 6: Debugging
Prompt: "Review this code for missing assignment requirements and suggest corrections."
Reasoning: Used to check completeness and improve reliability.
```

---

## `.gitignore`

```gitignore
.env
venv/
node_modules/
__pycache__/
.pytest_cache/
.DS_Store
dist/
*.pyc
```

---

## Implementation Rules for Claude Code

When generating or editing any file in this project:

1. Use **Groq** as the LLM provider. Never import or call OpenAI or Anthropic directly.
2. Use the `groq` Python SDK (`from groq import Groq`).
3. Use `GROQ_API_KEY` and `GROQ_MODEL` from environment variables.
4. Do NOT remove or bypass the 4-agent architecture.
5. Do NOT mock Tavily results unless `TAVILY_API_KEY` is missing — label it clearly if mock mode is used.
6. Do NOT hardcode any API keys.
7. Do NOT remove conversation memory or the human-in-the-loop clarification flow.
8. Do NOT add databases, Docker, authentication, or deployment config unless explicitly asked.
9. Keep all code local and runnable with simple `pip install` and `npm install`.
10. Keep code clean enough to explain in a technical interview.

---

## Testing Checklist

Before final submission, verify:

- [ ] Backend starts without errors
- [ ] Frontend starts and connects to backend
- [ ] `/chat` endpoint returns correct JSON
- [ ] Groq API is being called via `llm_service.py`
- [ ] Tavily search is being called in Research Agent
- [ ] `Research Tesla` works end-to-end
- [ ] `What about their competitors?` resolves Tesla from session memory
- [ ] `Tell me more about the CEO` resolves Tesla from session memory
- [ ] `Tell me about them` triggers clarification question
- [ ] Answering clarification continues the workflow correctly
- [ ] Research Agent produces a `confidence_score`
- [ ] Validator Agent can loop back to Research Agent
- [ ] Synthesis Agent produces a structured final answer
- [ ] Sources appear in the frontend as clickable links
- [ ] README.md is complete
- [ ] AI_PROMPTS_USED.md is present
- [ ] No API keys committed in any file
- [ ] Project can be zipped cleanly

---

## Final Submission ZIP Contents

```text
business-research-assistant/
  backend/
  frontend/
  README.md
  AI_PROMPTS_USED.md
  CLAUDE.md
  .gitignore
```

**Do NOT include:**
```text
.env
venv/
node_modules/
__pycache__/
.git/
dist/
```

---

## Final Goal

Generate a complete, locally runnable project using **Groq** for LLM calls and **Tavily** for search. The code must be clean enough to explain in an interview, complete enough to satisfy all assignment requirements, and simple enough to ZIP and submit.
