"""
TalentLens runtime configuration.
Centralises env, paths and operational limits — intentionally structured
differently from the upstream template to avoid diff collisions.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Resolve project root (one level above src/)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)

# --- LLM provider ---
OLLAMA_API_KEY: str = os.getenv("OLLAMA_API_KEY", "").strip()
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "https://ollama.com").rstrip("/")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gpt-oss:120b").strip()

# --- Server ---
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))

# --- Storage ---
MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "10"))
ALLOWED_EXTS = {".pdf"}

def _resolve_upload_dir() -> Path:
    # Vercel / Lambda have read-only project fs → fallback to /tmp
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        p = Path("/tmp/talentlens_uploads")
    else:
        p = PROJECT_ROOT / "uploads"
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        p = Path("/tmp/talentlens_uploads")
        p.mkdir(parents=True, exist_ok=True)
    return p

UPLOADS_DIR: Path = _resolve_upload_dir()

# Convenience for tests / health
APP_TITLE = "TalentLens — Hiring Copilot"
APP_VERSION = "2.0.0-jeff"
