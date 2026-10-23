"""Point every test at throwaway SQLite/Chroma paths and an unreachable Ollama.

These env vars must be set before any app module is imported, because
config.py reads them at import time.
"""

import os
import sys
import tempfile

_TMP = tempfile.mkdtemp(prefix="omnischolar-tests-")
os.environ["SQLITE_DB_PATH"] = os.path.join(_TMP, "test.db")
os.environ["CHROMA_DB_PATH"] = os.path.join(_TMP, "chroma")
os.environ["OLLAMA_HOST"] = "http://127.0.0.1:9"  # nothing listens here

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_DIR)
