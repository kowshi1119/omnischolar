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
    load_dotenv(_env_path)  # real environment variables win over .env
except ImportError:
    pass

# ── Ollama ─────────────────────────────────────────────────────────────────────
# "localhost" tries IPv6 (::1) first on Windows while Ollama listens on IPv4,
# adding ~2s to every request; 127.0.0.1 avoids the fallback.
OLLAMA_HOST        = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").replace("//localhost", "//127.0.0.1")
OLLAMA_MODEL       = os.getenv("OLLAMA_MODEL",       "gemma4:e2b")
# Multilingual (Sinhala/Tamil); existing nomic indexes are re-embedded automatically
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "embeddinggemma")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "gemma4:e4b")
OLLAMA_TIMEOUT     = int(os.getenv("OLLAMA_TIMEOUT", "120"))
# How long Ollama keeps the model loaded after a request (avoids cold starts)
_keep_alive = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
# Bare numbers ("-1" = forever, "300" = seconds) must be sent as numbers, not duration strings
OLLAMA_KEEP_ALIVE  = int(_keep_alive) if _keep_alive.lstrip("-").isdigit() else _keep_alive
OLLAMA_NUM_CTX          = int(os.getenv("OLLAMA_NUM_CTX",          "4096"))
OLLAMA_NUM_PREDICT      = int(os.getenv("OLLAMA_NUM_PREDICT",      "512"))
OLLAMA_NUM_BATCH        = int(os.getenv("OLLAMA_NUM_BATCH",        "512"))
OLLAMA_NUM_PARALLEL     = int(os.getenv("OLLAMA_NUM_PARALLEL",     "1"))
OLLAMA_MAX_LOADED_MODELS = int(os.getenv("OLLAMA_MAX_LOADED_MODELS", "1"))

# ── ChromaDB ───────────────────────────────────────────────────────────────────
_APP_DIR = Path(__file__).parent


def _app_path(value: str) -> str:
    """Resolve relative paths against the app folder so the cwd doesn't matter."""
    path = Path(value)
    return str(path if path.is_absolute() else (_APP_DIR / path).resolve())


CHROMA_DB_PATH          = _app_path(os.getenv("CHROMA_DB_PATH", "./study_db"))
CHROMA_COLLECTION_NAME  = os.getenv("CHROMA_COLLECTION_NAME",  "omnischolar_materials")

# ── SQLite ─────────────────────────────────────────────────────────────────────
SQLITE_DB_PATH = _app_path(os.getenv("SQLITE_DB_PATH", "./omnischolar.db"))

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
