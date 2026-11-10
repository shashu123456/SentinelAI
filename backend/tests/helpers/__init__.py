"""Reusable test helpers.

Prefer these over copy-pasted setup so a change to the auth flow or the upload
contract only needs one edit::

    from tests.helpers import register, auth_headers, make_spec, upload_spec

    def test_scan_upload(client):
        headers = auth_headers(client)
        response = upload_spec(client, headers, make_spec(["/v1/orders"]))
        assert response.status_code == 200
"""

from __future__ import annotations

import uuid
from typing import Any

DEFAULT_PASSWORD = "testpass123"


def unique(prefix: str = "user") -> str:
    """A collision-free username fragment for parallel-safe tests."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def register(
    client,
    *,
    prefix: str = "user",
    password: str = DEFAULT_PASSWORD,
    username: str | None = None,
    email: str | None = None,
) -> dict[str, Any]:
    """Create a user through the public API and return its session details."""
    username = username or unique(prefix)
    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": email or f"{username}@example.com",
            "password": password,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    token = data["access_token"]
    return {
        "username": username,
        "password": password,
        "user_id": data["user"]["id"],
        "user": data["user"],
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


def auth_headers(client, *, prefix: str = "user", **kwargs) -> dict[str, str]:
    """Register a fresh user and return only the Authorization header."""
    return register(client, prefix=prefix, **kwargs)["headers"]


def login(client, username: str, password: str = DEFAULT_PASSWORD) -> dict[str, str]:
    """Log in an existing user and return the Authorization header."""
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def make_spec(
    paths: list[str] | None = None,
    *,
    title: str = "Test API",
    version: str = "1.0.0",
) -> dict[str, Any]:
    """Build a minimal but valid OpenAPI 3 document.

    The default spec is deliberately *clean* (secured with a bearer scheme) so
    tests can opt into the specific weakness they care about.
    """
    paths = paths or ["/v1/orders"]
    document: dict[str, Any] = {
        "openapi": "3.0.0",
        "info": {"title": title, "version": version},
        "servers": [{"url": "https://api.example.com"}],
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
            }
        },
        "security": [{"bearerAuth": []}],
        "paths": {},
    }
    for path in paths:
        document["paths"][path] = {
            "get": {
                "summary": f"Read {path}",
                "responses": {"200": {"description": "OK"}},
            }
        }
    return document


def vulnerable_spec() -> dict[str, Any]:
    """A spec with known, high-signal weaknesses.

    Used by tests that assert findings are produced — keep it intentionally bad.
    """
    spec = make_spec(["/v1/admin/users", "/v1/orders/{orderId}"])
    del spec["security"]
    spec["servers"] = [{"url": "http://api.example.com"}]
    spec["paths"]["/v1/admin/users"]["delete"] = {
        "summary": "Delete user",
        "responses": {"200": {"description": "OK"}},
    }
    spec["paths"]["/v1/orders/{orderId}"]["get"]["parameters"] = [
        {"name": "orderId", "in": "path", "required": True, "schema": {"type": "string"}}
    ]
    return spec


def upload_spec(
    client,
    headers: dict[str, str],
    spec: dict[str, Any],
    *,
    api_name: str = "Test API",
    filename: str = "spec.json",
    extra: dict[str, Any] | None = None,
):
    """POST a spec to ``/api/scans/upload`` and return the raw response."""
    import json

    data = {"api_name": api_name, **(extra or {})}
    return client.post(
        "/api/scans/upload",
        files={"file": (filename, json.dumps(spec).encode(), "application/json")},
        data=data,
        headers=headers,
    )


def seed_scan(db, user_id: int, *, api_name: str = "Seeded API", risk_score: int = 50):
    """Insert a completed scan row directly (fast, no engine execution)."""
    from app.repositories.scans import ScanRepository
    from app.utils.security import utcnow

    repo = ScanRepository(db)
    scan = repo.create_scan(user_id=user_id, api_name=api_name, source_spec={})
    scan.status = "completed"
    scan.risk_score = risk_score
    scan.risk_level = "High" if risk_score >= 60 else "Medium"
    scan.total_endpoints = 3
    scan.total_vulnerabilities = 1
    scan.completed_at = utcnow()
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


__all__ = [
    "DEFAULT_PASSWORD",
    "auth_headers",
    "login",
    "make_spec",
    "register",
    "seed_scan",
    "unique",
    "upload_spec",
    "vulnerable_spec",
]
