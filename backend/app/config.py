import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
BACKEND_CORS_ORIGINS: list[str] = os.getenv(
    "BACKEND_CORS_ORIGINS", "http://localhost:5173"
).split(",")
