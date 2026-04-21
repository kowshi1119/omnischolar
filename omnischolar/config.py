"""
config.py — .env loader for OmniScholar
All configuration is read from environment variables (loaded from .env).
"""

import os
from pathlib import Path

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent / ".env"
    load_dotenv(_env_path, override=True)
except ImportError:
    pass

# ── Ollama ─────────────────────────────────────────────────────────────────────
OLLAMA_HOST        = os.getenv("OLLAMA_HOST",        "http://localhost:11434")
OLLAMA_MODEL       = os.getenv("OLLAMA_MODEL",       "gemma4:e4b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_TIMEOUT     = int(os.getenv("OLLAMA_TIMEOUT", "120"))
OLLAMA_NUM_CTX     = int(os.getenv("OLLAMA_NUM_CTX", "4096"))
OLLAMA_NUM_PARALLEL = int(os.getenv("OLLAMA_NUM_PARALLEL", "1"))

# ── ChromaDB ───────────────────────────────────────────────────────────────────
CHROMA_DB_PATH          = os.getenv("CHROMA_DB_PATH",          "./study_db")
CHROMA_COLLECTION_NAME  = os.getenv("CHROMA_COLLECTION_NAME",  "omnischolar_materials")

# ── SQLite ─────────────────────────────────────────────────────────────────────
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "./omnischolar.db")

# ── App ────────────────────────────────────────────────────────────────────────
APP_NAME         = os.getenv("APP_NAME",         "OmniScholar")
APP_DEBUG        = os.getenv("APP_DEBUG",        "False").lower() == "true"
APP_PORT         = int(os.getenv("APP_PORT",     "8501"))
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "english")

# ── HuggingFace ────────────────────────────────────────────────────────────────
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "")
HUGGINGFACE_REPO  = os.getenv("HUGGINGFACE_REPO",  "kowshikan/omnischolar-gemma4-edu")

# ── FastAPI ────────────────────────────────────────────────────────────────────
FASTAPI_HOST       = os.getenv("FASTAPI_HOST",       os.getenv("API_HOST", "0.0.0.0"))
FASTAPI_PORT       = int(os.getenv("FASTAPI_PORT",   os.getenv("API_PORT", "8000")))
API_SECRET_KEY     = os.getenv("API_SECRET_KEY",     "")
