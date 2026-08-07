"""Integration tests for the authentication API."""


class TestRegistration:
    def test_register_success(self, client):
        resp = client.post(
            "/api/auth/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": "securepass123",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["access_token"]
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "alice"
        assert data["user"]["email"] == "alice@example.com"

    def test_register_duplicate_username(self, client):
        payload = {
            "username": "bob",
            "email": "bob@example.com",
            "password": "securepass123",
        }
        assert client.post("/api/auth/register", json=payload).status_code == 201
        resp = client.post(
            "/api/auth/register",
            json={
                "username": "bob",
                "email": "bob2@example.com",
                "password": "securepass123",
            },
        )
        assert resp.status_code == 400
        assert "Username already registered" in resp.json()["detail"]

    def test_register_duplicate_email(self, client):
        payload = {
            "username": "carol",
            "email": "carol@example.com",
            "password": "securepass123",
        }
        assert client.post("/api/auth/register", json=payload).status_code == 201
        resp = client.post(
            "/api/auth/register",
            json={
                "username": "carol2",
                "email": "carol@example.com",
                "password": "securepass123",
            },
        )
        assert resp.status_code == 400
        assert "Email already registered" in resp.json()["detail"]

    def test_register_short_password_rejected(self, client):
        resp = client.post(
            "/api/auth/register",
            json={
                "username": "dave",
                "email": "dave@example.com",
                "password": "short",
            },
        )
        assert resp.status_code == 422

    def test_register_invalid_email_rejected(self, client):
        resp = client.post(
            "/api/auth/register",
            json={
                "username": "erin",
                "email": "not-an-email",
                "password": "securepass123",
            },
        )
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client):
        client.post(
            "/api/auth/register",
            json={
                "username": "frank",
                "email": "frank@example.com",
                "password": "securepass123",
            },
        )
        resp = client.post(
            "/api/auth/login",
            json={"username": "frank", "password": "securepass123"},
        )
        assert resp.status_code == 200
        assert resp.json()["access_token"]

    def test_login_wrong_password(self, client):
        client.post(
            "/api/auth/register",
            json={
                "username": "grace",
                "email": "grace@example.com",
                "password": "securepass123",
            },
        )
        resp = client.post(
            "/api/auth/login",
            json={"username": "grace", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"username": "nobody", "password": "whatever"},
        )
        assert resp.status_code == 401


class TestMe:
    def test_me_with_valid_token(self, client, user_token):
        username, token = user_token
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["username"] == username

    def test_me_without_token(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
        assert resp.status_code == 401

    def test_me_with_garbage_auth_header(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "garbage"})
        assert resp.status_code == 401
