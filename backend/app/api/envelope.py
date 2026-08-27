"""Standard API response envelope.

Versioned (``/api/v1/*``) endpoints return a uniform envelope:

* success: ``{"success": true, "data": <payload>, "meta": {...} | null}``
* error:   ``{"success": false, "error": {"code", "message", "details"}}``

Legacy (``/api/*``) responses keep their original shape so existing
clients and tests are unaffected.
"""

import math
from typing import Any


def api_response(data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a success envelope around a payload."""
    return {"success": True, "data": data, "meta": meta}


def error_response(code: str, message: str, details: Any = None) -> dict[str, Any]:
    """Build an error envelope with a stable machine-readable code."""
    return {
        "success": False,
        "error": {"code": code, "message": message, "details": details},
    }


def page_meta(page: int, page_size: int, total: int) -> dict[str, Any]:
    """Build pagination metadata for list responses."""
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }
