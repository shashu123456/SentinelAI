"""The authorized-use gate must block the first scan until acceptance."""

import json

import pytest

SPEC = {
    "openapi": "3.0.3",
    "info": {"title": "Gate Fixture", "version": "1.0.0"},
    "paths": {
        "/ping": {
            "get": {
                "operationId": "ping",
                "responses": {"200": {"description": "ok"}},
            }
        }
    },
}


def _upload(client, headers):
    return client.post(
        "/api/scans/upload",
        headers=headers,
        files={"file": ("api.json", json.dumps(SPEC).encode(), "application/json")},
        data={"kind": "spec"},
    )


@pytest.fixture
def enforce(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "ENFORCE_AUTHORIZED_USE", True)
    yield


def test_upload_is_403_before_acceptance(client, auth_headers, enforce):
    resp = _upload(client, auth_headers)
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == "authorization_required"


def test_acceptance_unblocks_upload(client, auth_headers, enforce):
    state = client.get("/api/account/authorized-use", headers=auth_headers)
    assert state.status_code == 200
    assert state.json()["accepted"] is False

    accepted = client.post("/api/account/authorized-use", headers=auth_headers)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["accepted"] is True
    assert accepted.json()["accepted_at"]

    resp = _upload(client, auth_headers)
    assert resp.status_code == 200, resp.text


def test_delete_data_removes_scans_but_keeps_account(client, auth_headers):
    # Enforcement is off in the suite, so a direct upload works here.
    assert _upload(client, auth_headers).status_code == 200
    before = client.get("/api/scans/", headers=auth_headers)
    assert len(before.json()) >= 1

    deleted = client.post("/api/account/delete-data", headers=auth_headers)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["deleted_scans"] >= 1

    after = client.get("/api/scans/", headers=auth_headers)
    assert after.json() == []
    # Account still usable.
    assert client.get("/api/auth/me", headers=auth_headers).status_code == 200
