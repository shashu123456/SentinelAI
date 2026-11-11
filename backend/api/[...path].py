"""Catch-all Vercel function: routes every nested /api/* path into FastAPI.

`api/index.py` only answers the bare `/api` path, so `/api/v1/version`,
`/api/auth/login` and friends need this file to reach the ASGI app.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402,F401  (Vercel looks for `app`)
