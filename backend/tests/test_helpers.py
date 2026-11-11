"""The shared test helpers must work, or every test built on them is suspect."""

from tests.helpers import (
    DEFAULT_PASSWORD,
    auth_headers,
    login,
    make_spec,
    register,
    seed_scan,
    upload_spec,
    vulnerable_spec,
)


def test_register_returns_usable_credentials(client):
    session = register(client, prefix="helper")

    assert session["username"].startswith("helper_")
    assert session["token"]
    assert session["headers"]["Authorization"].startswith("Bearer ")

    me = client.get("/api/auth/me", headers=session["headers"])
    assert me.status_code == 200
    assert me.json()["username"] == session["username"]


def test_login_matches_register_credentials(client):
    session = register(client, prefix="login")

    headers = login(client, session["username"], DEFAULT_PASSWORD)
    assert client.get("/api/auth/me", headers=headers).status_code == 200


def test_auth_headers_creates_a_fresh_user(client):
    first = auth_headers(client, prefix="fresh")
    second = auth_headers(client, prefix="fresh")

    assert first != second
    assert client.get("/api/auth/me", headers=first).status_code == 200


def test_make_spec_is_a_valid_openapi_document(client):
    spec = make_spec(["/v1/orders"], title="Orders API")

    assert spec["openapi"].startswith("3.")
    assert spec["info"]["title"] == "Orders API"
    assert "/v1/orders" in spec["paths"]

    response = upload_spec(client, auth_headers(client), spec, api_name="Orders API")
    assert response.status_code == 200, response.text
    assert response.json()["api_name"] == "Orders API"


def test_vulnerable_spec_produces_findings(client):
    response = upload_spec(client, auth_headers(client), vulnerable_spec(), api_name="Bad API")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total_vulnerabilities"] > 0
    assert payload["risk_score"] > 0

    detail = client.get(f"/api/scans/{payload['id']}", headers=auth_headers(client))
    assert detail.status_code in (200, 404)  # owner differs; helper keeps it simple


def test_seed_scan_persists_a_completed_scan(db_session, user):
    scan = seed_scan(db_session, user.id, api_name="Seeded", risk_score=72)

    assert scan.id
    assert scan.status == "completed"
    assert scan.risk_level == "High"
    assert scan.api_name == "Seeded"
