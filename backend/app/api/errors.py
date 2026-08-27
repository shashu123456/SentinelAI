"""Centralized exception handling with path-aware response shapes.

* ``/api/*`` (legacy) keeps FastAPI's ``{"detail": ...}`` shape so existing
  clients and tests are unaffected.
* ``/api/v1/*`` returns the standardized envelope
  ``{"success": false, "error": {"code", "message", "details"}}``.
"""

import logging
from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from slowapi.errors import RateLimitExceeded

from app.api.envelope import error_response

logger = logging.getLogger(__name__)

_VERSIONED_PREFIX = "/api/v1"

_STATUS_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
}


class APIError(HTTPException):
    """HTTP exception carrying a stable machine-readable error code."""

    def __init__(self, status_code: int, code: str, message: str, details: Any = None) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.details = details


def code_for_status(status_code: int) -> str:
    """Map an HTTP status to a stable error code."""
    return _STATUS_CODES.get(status_code, f"http_{status_code}")


def _is_versioned(request: Request) -> bool:
    return request.url.path.startswith(_VERSIONED_PREFIX)


async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if _is_versioned(request):
        code = exc.code if isinstance(exc, APIError) else code_for_status(exc.status_code)
        details = exc.details if isinstance(exc, APIError) else None
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(code, str(exc.detail), details),
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def _simplify_validation_errors(errors: Sequence[Any]) -> list[dict]:
    """Reduce pydantic error structures to a compact stable shape."""
    simplified: list[dict] = []
    for err in errors:
        loc = ".".join(str(part) for part in err.get("loc", ()))
        err_type = str(err.get("type", "value_error"))
        msg = str(err.get("msg", ""))
        ctx = err.get("ctx")
        if ctx and "error" in ctx:
            ctx = {"error": str(ctx["error"])}
        simplified.append({"loc": loc, "type": err_type, "msg": msg, "ctx": ctx})
    return simplified


async def _validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    if _is_versioned(request):
        return JSONResponse(
            status_code=422,
            content=error_response(
                "validation_error", "Request validation failed", _simplify_validation_errors(errors)
            ),
        )
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})


async def _pydantic_validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle raw pydantic errors raised by `Depends()`-style model bindings.

    FastAPI wraps ordinary request validation in ``RequestValidationError`` but
    a Pydantic model bound via ``Depends()`` raises ``ValidationError`` directly
    during dependency solving; normalize it to the same 422 shape.
    """
    errors = exc.errors()
    if _is_versioned(request):
        return JSONResponse(
            status_code=422,
            content=error_response(
                "validation_error", "Request validation failed", _simplify_validation_errors(errors)
            ),
        )
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    message = f"Rate limit exceeded: {exc.detail}"
    if _is_versioned(request):
        return JSONResponse(
            status_code=429,
            content=error_response("rate_limited", "Rate limit exceeded", message),
        )
    return JSONResponse(status_code=429, content={"error": message})


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True
    )
    if _is_versioned(request):
        return JSONResponse(
            status_code=500,
            content=error_response("internal_error", "Internal server error"),
        )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def register_exception_handlers(app: FastAPI) -> None:
    """Install centralized exception handlers on the application.

    Handlers are path-aware: versioned routes receive the envelope shape while
    legacy ``/api/*`` routes keep their original ``{"detail": ...}`` responses.
    """
    app.add_exception_handler(APIError, _http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, _http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(
        RequestValidationError,
        _validation_exception_handler,  # type: ignore[arg-type]
    )
    app.add_exception_handler(ValidationError, _pydantic_validation_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_exception_handler)
