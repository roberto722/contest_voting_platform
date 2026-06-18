"""Compatibility launcher for local FastAPI development.

The production application lives in backend/app/main.py.
"""

from pathlib import Path
import sys

backend_path = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_path))

from app.main import app

__all__ = ["app"]
