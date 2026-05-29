# Business Research Assistant

A production-grade multi-agent AI application that helps users research businesses by collecting company data, recent news, financial information, competitors, leadership details, and more.

---

## Architecture Overview

The system uses **LangGraph** to orchestrate 4 specialized agents in a conditional workflow, backed by **Groq** (LLM) and **Tavily** (web search).

```
User Message
     |
     v
[FastAPI /chat endpoint]
     |
     v
[Session Store] ─── resolve pending clarification, inject conversation history
     |
     v
[LangGraph Workflow]
     |
     v
┌─────────────────────────────────────────────────────┐
│                                                     │
│  START                                              │
│    │                                                │
│  Clarity Agent                                      │
│    ├── needs_clarification ──► INTERRUPT            │
│    │                        (return question)       │
│    └── clear                                        │
│         │                                           │
│  Research Agent (Tavily search)                     │
│    ├── confidence < 6 ──► Validator Agent           │
│    │                          │                     │
│    │              insufficient & attempts < 3       │
│    │                          └──► Research Agent   │
│    │              sufficient OR attempts >= 3       │
│    │                          └──► Synthesis Agent  │
│    └── confidence >= 6 ──► Synthesis Agent          │
│                                  │                  │
│                                 END                 │
└─────────────────────────────────────────────────────┘
     |
     v
[ChatResponse JSON] ──► React Frontend
```

---

## Agent Descriptions

### 1. Clarity Agent
Determines whether the user's query is specific enough to research. Resolves pronouns ("their", "the CEO") using session memory. Returns a clarification question if the company cannot be identified.

### 2. Research Agent
Performs real web searches via the Tavily API using the resolved query. Collects company overview, news, financials, leadership, and competitors. Scores its own confidence (0–10) to decide if validation is needed.

### 3. Validator Agent
Reviews research quality against the original query. Assesses relevance, completeness, and source credibility. Can loop back to the Research Agent (up to 3 total attempts) if findings are insufficient.

### 4. Synthesis Agent
Writes the final, structured, user-facing response using research findings and conversation history. Uses sections and bullet points for clarity. Includes clickable source links.

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- Node.js 18+
- A [Groq API key](https://console.groq.com/)
- A [Tavily API key](https://app.tavily.com/)

### Backend

```bash
cd business-research-assistant/backend

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and fill in environment variables
cp .env.example .env
# Edit .env with your GROQ_API_KEY and TAVILY_API_KEY

# Start backend
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd business-research-assistant/frontend

npm install
npm run dev
```

Frontend runs at: http://localhost:5173
Backend runs at: http://localhost:8000

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Groq API key for LLM calls |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Groq model name |
| `TAVILY_API_KEY` | Yes | — | Tavily API key for web search |
| `BACKEND_CORS_ORIGINS` | No | `http://localhost:5173` | Comma-separated allowed CORS origins |

---

## Demo Scenarios

### Scenario 1 — Direct Research
```
User: Research Tesla
```
Clarity Agent marks it clear → Research Agent (Tavily) → Synthesis Agent → structured summary with sources.

### Scenario 2 — Follow-up with Context
```
User: Research Tesla
...
User: What about their competitors?
```
Session memory resolves "their" → Tesla → researches Tesla competitors.

### Scenario 3 — Follow-up on Leadership
```
User: Tell me more about the CEO
```
System resolves company from session → researches Tesla CEO.

### Scenario 4 — Ambiguous Query + Clarification
```
User: Tell me about them
→ "Which company are you asking about?"

User: Tesla
→ Resolves to "Tell me about Tesla" → continues workflow
```

### Scenario 5 — Multi-Company Comparison
```
User: Compare Apple and Microsoft recent AI developments
```
Clear query → research both → structured comparison.

---

## API Reference

### POST /chat

**Request:**
```json
{
  "session_id": "string",
  "message": "string"
}
```

**Response (normal):**
```json
{
  "answer": "string",
  "needs_clarification": false,
  "clarification_question": null,
  "sources": [{ "title": "...", "url": "...", "content": "..." }],
  "debug": { "steps": [...], "confidence_score": 8, "attempts": 1 }
}
```

**Response (clarification needed):**
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

## Known Limitations & Trade-offs

- **In-memory session store**: Sessions are lost on server restart. A Redis or database store would fix this for production.
- **No authentication**: The API is open. For production, add API key auth or OAuth.
- **Tavily rate limits**: Heavy use may hit API limits; no retry/backoff is implemented.
- **LLM JSON parsing**: The Clarity and Research agents rely on the LLM returning valid JSON. A fallback is included but edge cases may occur with very unusual queries.
- **Single-server deployment**: No load balancing; designed for local development and demo purposes.
