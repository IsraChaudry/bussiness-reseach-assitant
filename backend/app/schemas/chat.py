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
