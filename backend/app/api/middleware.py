"""Middleware that wraps versioned (``/api/v1/*``) JSON responses in the
standard success envelope.

Error responses are produced by the centralized exception handlers and are
already enveloped, so they pass through untouched. Downloads and streaming
responses are excluded so file payloads are never corrupted.

Note: ``BaseHTTPMiddleware.call_next`` always returns a ``_StreamingResponse``
whose body is exposed through an *async* ``body_iterator``, so the body is read
asynchronously. Because reading consumes the stream, any response we forward is
rebuilt from the read bytes.
"""

import json
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi.responses import JSONResponse, Response

from app.api.envelope import error_response
from app.api.errors import code_for_status

_VERSIONED_PREFIX = "/api/v1"

EnvelopeCallNext = Callable[[Any], Awaitable[Response]]


async def _read_body(response: Response) -> bytes | None:
    """Read the response body, handling async, sync, and buffered responses."""
    body_iter = getattr(response, "body_iterator", None)
    if body_iter is not None:
        try:
            chunks: list[bytes] = []
            async for chunk in body_iter:
                chunks.append(chunk)
            return b"".join(chunks)
        except Exception:
            return None
    body = getattr(response, "body", None)
    if isinstance(body, bytes):
        return body
    return None


def _is_json(response: Response) -> bool:
    return "application/json" in response.headers.get("content-type", "")


# Entity headers describe the body that was read, not the re-encoded one. Copying
# them (content-length in particular) makes the server advertise a length that
# does not match the new body, which aborts the response mid-flight.
_ENTITY_HEADERS = {
    "content-length",
    "content-type",
    "content-encoding",
    "transfer-encoding",
    "connection",
}


def _rebuild(response: Response, content: dict[str, Any], status_code: int) -> Response:
    """Forward a response as a fresh JSONResponse preserving end-to-end headers."""
    rebuilt = JSONResponse(content=content, status_code=status_code)
    for key, value in response.headers.items():
        if key.lower() in _ENTITY_HEADERS:
            continue
        rebuilt.headers[key] = value
    return rebuilt


async def _wrap_success(response: Response) -> Response:
    if not _is_json(response):
        return response
    if response.headers.get("content-disposition", "").startswith("attachment"):
        return response
    body = await _read_body(response)
    if not body:
        return response
    try:
        data = json.loads(body)
    except (ValueError, TypeError):
        return response
    if isinstance(data, dict) and "success" in data:
        return _rebuild(response, data, response.status_code)
    return _rebuild(response, {"success": True, "data": data, "meta": None}, response.status_code)


async def _wrap_error(response: Response) -> Response:
    if not _is_json(response):
        return response
    body = await _read_body(response)
    if not body:
        return _rebuild(
            response,
            error_response(code_for_status(response.status_code), "Request failed"),
            response.status_code,
        )
    try:
        data = json.loads(body)
    except (ValueError, TypeError):
        return response
    if isinstance(data, dict) and "success" in data:
        return _rebuild(response, data, response.status_code)
    if isinstance(data, dict) and "detail" in data:
        return _rebuild(
            response,
            error_response(
                code_for_status(response.status_code), str(data["detail"]), data["detail"]
            ),
            response.status_code,
        )
    return _rebuild(
        response,
        error_response(code_for_status(response.status_code), str(data), data),
        response.status_code,
    )


async def envelope_middleware(request: Any, call_next: EnvelopeCallNext) -> Response:
    """Starlette pure-function middleware; register it innermost."""
    path = request.url.path
    if not path.startswith(_VERSIONED_PREFIX):
        return await call_next(request)
    response = await call_next(request)
    if response.status_code < 400:
        return await _wrap_success(response)
    return await _wrap_error(response)
