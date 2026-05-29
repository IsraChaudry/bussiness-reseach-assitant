from typing import Dict, Any, Optional

SESSION_STORE: Dict[str, Dict[str, Any]] = {}


def get_session(session_id: str) -> Dict[str, Any]:
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = {
            "messages": [],
            "company_name": None,
            "last_query": None,
            "pending_clarification": False,
            "pending_query": None,
            "active_agent": None,
        }
    return SESSION_STORE[session_id]


def update_session(session_id: str, data: Dict[str, Any]) -> None:
    session = get_session(session_id)
    session.update(data)


def append_message(session_id: str, role: str, content: str) -> None:
    session = get_session(session_id)
    session["messages"].append({"role": role, "content": content})


def set_active_agent(session_id: str, agent_name: Optional[str]) -> None:
    session = get_session(session_id)
    session["active_agent"] = agent_name


def get_active_agent(session_id: str) -> Dict[str, Any]:
    session = get_session(session_id)
    agent = session.get("active_agent")
    return {
        "active_agent": agent,
        "status": "running" if agent else "idle",
    }
