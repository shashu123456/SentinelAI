"""Vercel serverless entrypoint for the SentinelAI FastAPI app.

Vercel's Python runtime puts the *function's* directory on sys.path, not the
project root, so `backend/` is added explicitly before importing the package.
Serves the bare `/api` path; `api/[...path].py` handles nested routes.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402,F401  (Vercel looks for `app`)
