"""Minimal HTTP client for the SentinelAI API.

Uses only the standard library so the CLI keeps working even when the backend
virtualenv is not the active interpreter (``sentinel login`` against a remote
deployment never needs FastAPI installed).
"""

from __future__ import annotations

import json
import mimetypes
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from . import config


class APIError(RuntimeError):
    """A non-2xx response from the API, with the server's message preserved."""

    def __init__(self, status: int, message: str, payload=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.payload = payload


def _request(
    method: str,
    path: str,
    *,
    body: bytes | None = None,
    headers: dict | None = None,
    base_url: str | None = None,
    auth: bool = True,
    timeout: float = 60.0,
) -> tuple[int, bytes, dict]:
    base = (base_url or config.api_url()).rstrip("/")
    url = f"{base}{path}"
    all_headers = {"Accept": "application/json", **(headers or {})}

    token = config.token()
    if auth and token:
        all_headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, data=body, headers=all_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
            return response.status, payload, dict(response.headers)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        raise APIError(exc.code, _error_message(raw, exc.reason), _safe_json(raw)) from None
    except urllib.error.URLError as exc:
        raise APIError(
            0,
            f"Cannot reach the API at {base} ({exc.reason}). "
            "Start it with `make dev-backend` or pass --url.",
        ) from None


def _safe_json(raw: bytes):
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _error_message(raw: bytes, fallback: str) -> str:
    payload = _safe_json(raw)
    if isinstance(payload, dict):
        if "detail" in payload:
            detail = payload["detail"]
            return detail if isinstance(detail, str) else json.dumps(detail)
        error = payload.get("error")
        if isinstance(error, dict) and error.get("message"):
            return error["message"]
    return fallback or "Request failed"


def get_json(path: str, **kwargs):
    status, raw, _ = _request("GET", path, **kwargs)
    return json.loads(raw or b"null")


def post_json(path: str, payload: dict, **kwargs):
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", **kwargs.pop("headers", {})}
    status, raw, _ = _request("POST", path, body=body, headers=headers, **kwargs)
    return json.loads(raw or b"null")


def delete(path: str, **kwargs) -> None:
    _request("DELETE", path, **kwargs)


def download(path: str, destination: Path) -> Path:
    """Stream a binary endpoint (PDF/JSON report) to ``destination``."""
    status, raw, headers = _request("GET", path, timeout=120.0)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    return destination


def upload_spec(path: Path, *, api_name: str = "", organization_id: int | None = None):
    """POST a spec file to ``/api/scans/upload`` as multipart/form-data."""
    boundary = f"----sentinelai{uuid.uuid4().hex}"
    file_bytes = path.read_bytes()
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    parts: list[bytes] = []
    for name, value in (("api_name", api_name), ("organization_id", organization_id)):
        if value in (None, ""):
            continue
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            f'filename="{path.name}"\r\nContent-Type: {content_type}\r\n\r\n'
        ).encode()
        + file_bytes
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())

    status, raw, _ = _request(
        "POST",
        "/api/scans/upload",
        body=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        timeout=300.0,
    )
    return json.loads(raw or b"null")


def login(username: str, password: str, base_url: str | None = None) -> dict:
    return post_json(
        "/api/auth/login", {"username": username, "password": password}, base_url=base_url
    )


def health(base_url: str | None = None) -> dict:
    """Full health payload (unwraps the ``/api/v1`` success envelope)."""
    payload = get_json("/api/v1/health", base_url=base_url, auth=False)
    if isinstance(payload, dict) and "data" in payload and "success" in payload:
        return payload["data"]
    return payload


def unwrap(payload):
    """Unwrap ``{success, data}`` envelopes returned by ``/api/v1`` routes."""
    if isinstance(payload, dict) and payload.get("success") is True and "data" in payload:
        return payload["data"]
    return payload
