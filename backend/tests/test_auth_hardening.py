"""Auth hardening tests: session refresh/rotation, roles, lockout, rate limits,
password reset, and security headers."""

import secrets
import uuid

from app.config import get_settings

settings = get_settings()

REFRESH_COOKIE = settings.REFRESH_TOKEN_COOKIE_NAME
STRONG_PASSWORD = "Testpass123"


def _register(client, username=None, password=STRONG_PASSWORD, email=None):
    username = username or f"u_{uuid.uuid4().hex[:8]}"
    email = email or f"{username}@example.com"
    resp = client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    return resp, username, email, password


def _make_admin(client):
    """Register a user and promote them to admin directly in the DB."""
    from app.database.database import SessionLocal
    from app.models.models import User

    resp, username, _, password = _register(client)
    token = resp.json()["access_token"]
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        user.role = "admin"
        db.commit()
    finally:
        db.close()
    return token, username, password


def _set_user_flag(client, username, **fields):
    from app.database.database import SessionLocal
    from app.models.models import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        for key, value in fields.items():
            setattr(user, key, value)
        db.commit()
    finally:
        db.close()


class TestRegistrationPolicy:
    def test_register_defaults_role_and_active(self, client):
        resp, _, _, _ = _register(client)
        assert resp.status_code == 201
        user = resp.json()["user"]
        assert user["role"] == "user"
        assert user["is_active"] is True

    def test_register_sets_refresh_cookie(self, client):
        resp, _, _, _ = _register(client)
        assert resp.status_code == 201
        assert REFRESH_COOKIE in client.cookies
        assert resp.headers["set-cookie"].lower().find("httponly") != -1

    def test_register_too_short_password_rejected(self, client):
        resp, _, _, _ = _register(client, password="Short1")
        assert resp.status_code == 422

    def test_register_no_digit_password_rejected(self, client):
        resp, _, _, _ = _register(client, password="Allletters")
        assert resp.status_code == 422

    def test_register_no_upper_allowed_when_not_required(self, client):
        resp, _, _, _ = _register(client, password="lowercase123")
        assert resp.status_code == 201


class TestRefreshRotation:
    def _get_csrf_headers(self, client):
        """Extract CSRF token from cookies and return as header."""
        csrf_cookie = client.cookies.get("sentinelai_csrf", "")
        if csrf_cookie and "." in csrf_cookie:
            token = csrf_cookie.split(".", 1)[0]
            return {"x-csrf-token": token}
        return {}

    def test_refresh_issues_new_access_token(self, client):
        resp, _, _, _ = _register(client)
        headers = self._get_csrf_headers(client)
        r = client.post("/api/auth/refresh", headers=headers)
        assert r.status_code == 200
        assert r.json()["access_token"]

    def test_refresh_rotates_token(self, client):
        resp, _, _, _ = _register(client)
        old = client.cookies.get(REFRESH_COOKIE)
        headers = self._get_csrf_headers(client)
        r = client.post("/api/auth/refresh", headers=headers)
        new = client.cookies.get(REFRESH_COOKIE)
        assert r.status_code == 200
        assert old and new and old != new

    def test_refresh_without_cookie_rejected(self, client):
        resp, _, _, _ = _register(client)
        client.cookies.clear()
        assert client.post("/api/auth/refresh").status_code == 401

    def test_refresh_without_csrf_header_rejected(self, client):
        """Refresh must include CSRF header when CSRF cookie is present."""
        resp, _, _, _ = _register(client)
        # Send refresh without CSRF header (but cookie is present)
        r = client.post("/api/auth/refresh")
        assert r.status_code == 403

    def test_reuse_detection_revokes_family(self, client):
        from fastapi.testclient import TestClient

        from app.main import app

        resp, _, _, _ = _register(client)
        old = client.cookies.get(REFRESH_COOKIE)
        headers = self._get_csrf_headers(client)
        assert client.post("/api/auth/refresh", headers=headers).status_code == 200
        assert client.cookies.get(REFRESH_COOKIE) != old

        # A second "device" presents the already-consumed token: treated as theft.
        attacker = TestClient(app)
        attacker.cookies.set(REFRESH_COOKIE, old, path="/api/auth")
        assert attacker.post("/api/auth/refresh").status_code == 401

        # The whole family is now revoked, including the latest one.
        headers2 = self._get_csrf_headers(client)
        assert client.post("/api/auth/refresh", headers=headers2).status_code == 401

    def test_garbage_refresh_token_rejected(self, client):
        from fastapi.testclient import TestClient

        from app.main import app

        attacker = TestClient(app)
        attacker.cookies.set(REFRESH_COOKIE, "not-a-real-token", path="/api/auth")
        assert attacker.post("/api/auth/refresh").status_code == 401


class TestLogout:
    def test_logout_revokes_and_clears_cookie(self, client):
        resp, _, _, _ = _register(client)
        assert client.post("/api/auth/logout").status_code == 204
        assert REFRESH_COOKIE not in client.cookies
        assert client.post("/api/auth/refresh").status_code == 401

    def test_logout_all_revokes_every_token(self, client):
        resp, _, _, _ = _register(client)
        token = resp.json()["access_token"]
        r = client.post(
            "/api/auth/logout-all",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 204
        assert client.post("/api/auth/refresh").status_code == 401

    def test_logout_revokes_access_token_via_jti(self, client):
        """Logout should revoke the current access token via JTI blacklist."""
        resp, _, _, _ = _register(client)
        token = resp.json()["access_token"]
        # Token should work before logout
        assert (
            client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code
            == 200
        )
        # Logout
        client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        # Token should be revoked after logout
        assert (
            client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code
            == 401
        )


class TestLoginLockout:
    def test_account_locks_after_max_failures(self, client):
        resp, username, _, password = _register(client)
        for _ in range(settings.LOGIN_MAX_ATTEMPTS):
            r = client.post(
                "/api/auth/login",
                json={"username": username, "password": "Wrongpass1"},
            )
            assert r.status_code == 401

        # Correct password is rejected while locked.
        r = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        assert r.status_code == 423

    def test_admin_unlock_allows_login_again(self, client):
        resp, username, _, password = _register(client)
        user_id = resp.json()["user"]["id"]
        for _ in range(settings.LOGIN_MAX_ATTEMPTS):
            client.post("/api/auth/login", json={"username": username, "password": "Wrongpass1"})

        admin_token, _, _ = _make_admin(client)
        unlock = client.post(
            f"/api/auth/users/{user_id}/unlock",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert unlock.status_code == 200

        r = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        assert r.status_code == 200


class TestInactiveUser:
    def test_inactive_user_cannot_access_me(self, client):
        resp, username, _, _ = _register(client)
        token = resp.json()["access_token"]
        _set_user_flag(client, username, is_active=False)

        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403

    def test_inactive_user_cannot_login(self, client):
        resp, username, _, password = _register(client)
        _set_user_flag(client, username, is_active=False)

        r = client.post("/api/auth/login", json={"username": username, "password": password})
        assert r.status_code == 403


RESET_TOKEN = "pinned-reset-token-for-tests"


def _request_reset(client, monkeypatch, email, token=RESET_TOKEN):
    """Request a password reset and return the raw reset token.

    The API deliberately never echoes reset tokens (see
    ``test_security_hardening.TestPasswordResetSecurity``), so the generated
    token is pinned for the duration of the request instead.
    """
    with monkeypatch.context() as patch:
        patch.setattr(secrets, "token_urlsafe", lambda _n: token)
        resp = client.post("/api/auth/forgot-password", json={"email": email})

    assert resp.status_code == 200
    assert resp.json()["reset_token"] is None
    return token


class TestRolesAndAdmin:
    def test_non_admin_cannot_list_users(self, client):
        resp, _, _, _ = _register(client)
        token = resp.json()["access_token"]
        r = client.get("/api/auth/users", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403

    def test_admin_can_manage_users(self, client):
        admin_token, _, _ = _make_admin(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        target = _register(client)
        target_id = target[0].json()["user"]["id"]

        lst = client.get("/api/auth/users", headers=admin_headers)
        assert lst.status_code == 200
        assert len(lst.json()) == 2

        role = client.patch(
            f"/api/auth/users/{target_id}/role",
            json={"role": "analyst"},
            headers=admin_headers,
        )
        assert role.status_code == 200
        assert role.json()["role"] == "analyst"

        assert (
            client.post(f"/api/auth/users/{target_id}/lock", headers=admin_headers).status_code
            == 200
        )
        sessions = client.get(f"/api/auth/users/{target_id}/sessions", headers=admin_headers)
        assert sessions.status_code == 200
        assert isinstance(sessions.json(), list)
        assert (
            client.post(f"/api/auth/users/{target_id}/unlock", headers=admin_headers).status_code
            == 200
        )

    def test_admin_cannot_change_own_role(self, client):
        admin_token, _, _ = _make_admin(client)
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"}).json()
        r = client.patch(
            f"/api/auth/users/{me['id']}/role",
            json={"role": "viewer"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 400

    def test_invalid_role_rejected(self, client):
        admin_token, _, _ = _make_admin(client)
        target_id = _register(client)[0].json()["user"]["id"]
        r = client.patch(
            f"/api/auth/users/{target_id}/role",
            json={"role": "superuser"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 422


class TestPasswordReset:
    def test_full_reset_flow(self, client, monkeypatch):
        resp, username, email, password = _register(client)

        reset_token = _request_reset(client, monkeypatch, email)
        assert reset_token

        reset = client.post(
            "/api/auth/reset-password",
            json={"token": reset_token, "new_password": "Newpass123"},
        )
        assert reset.status_code == 200

        assert (
            client.post(
                "/api/auth/login", json={"username": username, "password": password}
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/auth/login", json={"username": username, "password": "Newpass123"}
            ).status_code
            == 200
        )

    def test_reset_token_is_single_use(self, client, monkeypatch):
        resp, _, email, _ = _register(client)
        reset_token = _request_reset(client, monkeypatch, email)

        assert (
            client.post(
                "/api/auth/reset-password",
                json={"token": reset_token, "new_password": "Newpass123"},
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/auth/reset-password",
                json={"token": reset_token, "new_password": "Newpass456"},
            ).status_code
            == 400
        )

    def test_forgot_password_unknown_email_is_generic(self, client):
        r = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
        assert r.status_code == 200
        assert r.json()["reset_token"] is None

    def test_weak_new_password_rejected(self, client, monkeypatch):
        resp, _, email, _ = _register(client)
        reset_token = _request_reset(client, monkeypatch, email)
        r = client.post(
            "/api/auth/reset-password",
            json={"token": reset_token, "new_password": "weak"},
        )
        assert r.status_code == 422


class TestSecurityHeaders:
    def test_security_headers_present(self, client):
        r = client.get("/api/health")
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["x-frame-options"] == "DENY"
        assert r.headers["referrer-policy"]
        assert r.headers["content-security-policy"]


class TestTokenRobustness:
    def test_tampered_access_token_rejected(self, client):
        resp, _, _, _ = _register(client)
        token = resp.json()["access_token"]
        bad = token[:-2] + ("xy" if token[-2:] != "xy" else "zz")
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad}"})
        assert r.status_code == 401


class TestRateLimiting:
    def test_login_rate_limit_exceeded(self, client):
        codes = []
        for i in range(settings.LOGIN_RATE_LIMIT_PER_MINUTE + 1):
            r = client.post(
                "/api/auth/login",
                json={"username": f"ghost_{i}", "password": "Wrongpass1"},
            )
            codes.append(r.status_code)
        assert all(c == 401 for c in codes[:-1])
        assert codes[-1] == 429
