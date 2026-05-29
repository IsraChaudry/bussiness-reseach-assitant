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
