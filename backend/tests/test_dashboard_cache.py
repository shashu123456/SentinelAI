"""Cache keying and invalidation for the dashboard / analytics aggregates.

Two properties, both of which were broken at some point and neither of which the
existing suite covered:

1. Invalidation must match the cache key. The key is ``dashboard:{id}:{username}``
   while uploads delete by the ``dashboard:{id}`` prefix. Prefix deletion still
   matches the longer key, so a scan uploaded a second after the dashboard was
   read must appear on the next read rather than after the 60s TTL.
2. The key must carry a stable per-account identity, not just the numeric id.
   Ids are reused when a database is restored, and under the old ``dashboard:{id}``
   key the next account to hold that id was served the previous account's cached
   dashboard.
"""

import json

SPEC = {
    "openapi": "3.0.3",
    "info": {"title": "Cache Fixture", "version": "1.0.0"},
    "paths": {
        "/widgets": {
            "get": {
                "operationId": "listWidgets",
                "responses": {"200": {"description": "ok"}},
            }
        }
    },
}


def _upload(client, headers, name="api.json"):
    return client.post(
        "/api/scans/upload",
        headers=headers,
        files={"file": (name, json.dumps(SPEC).encode(), "application/json")},
        data={"kind": "spec"},
    )


def _user_id(username: str) -> int:
    from app.database.database import SessionLocal
    from app.models.models import User

    db = SessionLocal()
    try:
        return db.query(User).filter(User.username == username).one().id
    finally:
        db.close()


def test_upload_invalidates_the_dashboard_entry(client, auth_headers):
    """A second upload must be visible immediately, not after the TTL."""
    assert _upload(client, auth_headers).status_code == 200
    first = client.get("/api/scans/dashboard", headers=auth_headers)
    assert first.status_code == 200, first.text
    assert first.json()["total_scans"] == 1

    # This read populated dashboard:{id}:{username}. The next upload must delete
    # that longer key through the dashboard:{id} prefix.
    assert _upload(client, auth_headers, "api2.json").status_code == 200
    second = client.get("/api/scans/dashboard", headers=auth_headers)
    assert second.status_code == 200, second.text
    assert second.json()["total_scans"] == 2


def test_upload_invalidates_the_analytics_entry(client, auth_headers):
    assert _upload(client, auth_headers).status_code == 200
    first = client.get("/api/scans/analytics", headers=auth_headers)
    assert first.status_code == 200, first.text
    assert sum(day["scans"] for day in first.json()["scan_activity"]) == 1

    assert _upload(client, auth_headers, "api2.json").status_code == 200
    second = client.get("/api/scans/analytics", headers=auth_headers)
    assert second.status_code == 200, second.text
    assert sum(day["scans"] for day in second.json()["scan_activity"]) == 2


def test_id_only_cache_entry_is_not_served(client, auth_headers, user_token):
    """An entry under the old id-only key must never reach the response.

    This is the shape of the leak: after a restore reuses id 1, an entry written
    by the previous owner of id 1 is still in the cache.
    """
    username, _ = user_token
    user_id = _user_id(username)

    from app.utils.cache import cache

    cache.set(f"dashboard:{user_id}", {"total_scans": 999}, ttl=60)
    cache.set(f"analytics:{user_id}", {"scan_activity": [{"date": "2026-01-01", "scans": 999}]}, ttl=60)

    dashboard = client.get("/api/scans/dashboard", headers=auth_headers)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["total_scans"] == 0

    analytics = client.get("/api/scans/analytics", headers=auth_headers)
    assert analytics.status_code == 200, analytics.text
    assert sum(day["scans"] for day in analytics.json()["scan_activity"]) == 0


def test_two_accounts_never_share_a_dashboard(client):
    """Two accounts, one upload: the second account's dashboard stays empty."""
    first_headers = _register(client, "cache_user_a")
    second_headers = _register(client, "cache_user_b")

    assert _upload(client, first_headers).status_code == 200
    assert client.get("/api/scans/dashboard", headers=first_headers).json()["total_scans"] == 1

    other = client.get("/api/scans/dashboard", headers=second_headers)
    assert other.status_code == 200, other.text
    assert other.json()["total_scans"] == 0


def _register(client, name: str) -> dict:
    resp = client.post(
        "/api/auth/register",
        json={"username": name, "email": f"{name}@example.com", "password": "testpass123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
