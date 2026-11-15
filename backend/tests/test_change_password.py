"""Tests for the POST /api/auth/change-password endpoint.

Scope note on the "short new password" case
-------------------------------------------
``ChangePasswordRequest.new_password`` is declared with ``min_length=8`` and a
``validate_password_strength`` validator, and ``settings.PASSWORD_MIN_LENGTH``
is 8. A password shorter than 8 characters is therefore rejected by Pydantic
with **422** before the route body executes, so the route's own
``len(data.new_password) < settings.PASSWORD_MIN_LENGTH`` -> **400** branch is
unreachable while both values are 8. The test below asserts the behaviour a
client actually observes (422) and does not pretend the 400 branch is covered.
"""

import uuid

CURRENT_PASSWORD = "CorrectPass1!"
NEW_PASSWORD = "NewStrongPass2!"


def _register_and_login(client, password=CURRENT_PASSWORD):
    """Register a unique user and return (username, access_token)."""
    username = f"cp_{uuid.uuid4().hex[:8]}"
    resp = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
        },
    )
    assert resp.status_code == 201, resp.text
    return username, resp.json()["access_token"]


def _change(client, token, current, new):
    return client.post(
        "/api/auth/change-password",
        json={"current_password": current, "new_password": new},
        headers={"Authorization": f"Bearer {token}"},
    )


def test_change_password_wrong_current_password_400(client):
    """A wrong current password is rejected by the route with 400."""
    _, token = _register_and_login(client)

    resp = _change(client, token, "WrongPass9!", NEW_PASSWORD)

    assert resp.status_code == 400, resp.text
    assert "current password" in resp.json()["detail"].lower()


def test_change_password_short_new_password_422(client):
    """A sub-8-character new password is rejected by schema validation (422).

    See the module docstring: the route's 400 branch is unreachable at
    PASSWORD_MIN_LENGTH == 8, so 422 is the real contract.
    """
    _, token = _register_and_login(client)

    resp = _change(client, token, CURRENT_PASSWORD, "short")

    assert resp.status_code == 422, resp.text

    # The body must carry a message a user can act on, not just a loc array.
    import json

    body = json.dumps(resp.json()).lower()
    assert "at least 8" in body or "characters" in body, resp.text


def test_change_password_weak_new_password_422(client):
    """A new password meeting length but failing strength rules is 422."""
    _, token = _register_and_login(client)

    # 8+ chars, but no digit/uppercase variety per validate_password_strength.
    resp = _change(client, token, CURRENT_PASSWORD, "aaaaaaaa")

    assert resp.status_code == 422, resp.text


def test_change_password_success_200_and_audit_row(client):
    """A valid change returns 200 and writes exactly one audit row."""
    username, token = _register_and_login(client)

    resp = _change(client, token, CURRENT_PASSWORD, NEW_PASSWORD)

    assert resp.status_code == 200, resp.text
    assert resp.json()["detail"] == "Password changed successfully"

    # The new password must actually work for a fresh login.
    login = client.post(
        "/api/auth/login",
        json={"username": username, "password": NEW_PASSWORD},
    )
    assert login.status_code == 200, login.text

    # And the audit event must have been persisted for this user.
    from app.database.database import SessionLocal
    from app.models.models import AuditLog

    db = SessionLocal()
    try:
        rows = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "auth.password_changed",
                AuditLog.username == username,
            )
            .all()
        )
        assert len(rows) == 1, f"expected 1 audit row, got {len(rows)}"
    finally:
        db.close()


def test_change_password_without_auth_401(client):
    """The endpoint requires authentication."""
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": CURRENT_PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert resp.status_code == 401, resp.text
