import os
import json
from groq import Groq

_client: Groq | None = None
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def _get_client() -> Groq:
    """Return a lazily-initialized Groq client."""
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your .env file."
            )
        _client = Groq(api_key=api_key)
    return _client


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Call Groq LLM and return the text response."""
    response = _get_client().chat.completions.create(
        model=os.getenv("GROQ_MODEL", MODEL),
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
        clean = raw.strip()
        # Strip markdown code fences if model wraps output
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
            clean = clean.strip()
        return json.loads(clean)
    except Exception:
        return {}
