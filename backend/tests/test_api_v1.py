"""Version 1 API tests: envelope shape, filters, sorting, pagination, ownership."""

import uuid
from datetime import timedelta

from app.repositories.findings import FindingRepository
from app.repositories.scans import ScanRepository
from app.utils.security import utcnow


def _register(client, prefix="v1") -> dict:
    username = f"{prefix}_{uuid.uuid4().hex[:8]}"
    resp = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpass123",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {
        "user_id": data["user"]["id"],
        "token": data["access_token"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }


def _seed(db, user_id: int, count: int = 3) -> list[int]:
    """Insert scans with deterministic risk scores / severities and return ids."""
    scan_repo = ScanRepository(db)
    finding_repo = FindingRepository(db)
    now = utcnow()
    ids = []
    for i in range(count):
        scan = scan_repo.create_scan(user_id=user_id, api_name=f"Petstore{i}", source_spec={})
        scan.status = "completed"
        scan.risk_level = "High"
        scan.risk_score = 60 + i
        scan.total_vulnerabilities = i + 1
        scan.created_at = now - timedelta(days=i)
        db.add(scan)
        db.commit()
        ids.append(scan.id)

        finding_repo.bulk_add_from_scan(
            scan.id,
            [
                {
                    "vulnerability_name": "Broken Auth",
                    "owasp_category": "API2",
                    "severity": "Critical",
                    "description": "d",
                    "impact": "i",
                    "remediation": "r",
                    "affected_endpoint": "/admin",
                },
                {
                    "vulnerability_name": "Info Leak",
                    "owasp_category": "API8",
                    "severity": "Low",
                    "description": "d",
                    "impact": "i",
                    "remediation": "r",
                    "affected_endpoint": "/debug",
                },
            ],
        )
        db.commit()
    return ids


class TestListScans:
    def test_returns_envelope_and_page_meta(self, client, db_session):
        user = _register(client)
        _seed(db_session, user["user_id"], count=5)
        resp = client.get("/api/v1/scans", headers=user["headers"])
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["meta"] == {"page": 1, "page_size": 20, "total": 5, "total_pages": 1}
        assert isinstance(body["data"], list)
        assert len(body["data"]) == 5

    def test_pagination(self, client, db_session):
        user = _register(client)
        _seed(db_session, user["user_id"], count=5)
        resp = client.get("/api/v1/scans?page=2&page_size=2", headers=user["headers"])
        body = resp.json()
        assert body["meta"] == {"page": 2, "page_size": 2, "total": 5, "total_pages": 3}
        assert len(body["data"]) == 2

    def test_default_sort_newest_first(self, client, db_session):
        user = _register(client)
        _seed(db_session, user["user_id"], count=3)
        resp = client.get("/api/v1/scans?sort_by=created_at", headers=user["headers"])
        dates = [item["created_at"] for item in resp.json()["data"]]
        assert dates == sorted(dates, reverse=True)

    def test_sort_by_risk_score_desc(self, client, db_session):
        user = _register(client)
        _seed(db_session, user["user_id"], count=3)
        resp = client.get("/api/v1/scans?sort_by=-risk_score", headers=user["headers"])
        scores = [item["risk_score"] for item in resp.json()["data"]]
        assert scores == sorted(scores, reverse=True)

    def test_multi_column_sort(self, client, db_session):
        user = _register(client)
        _seed(db_session, user["user_id"], count=2)
        resp = client.get("/api/v1/scans?sort_by=status,-risk_score", headers=user["headers"])
        assert resp.status_code == 200

    def test_status_and_risk_filters(self, client, db_session):
        user = _register(client)
        _seed(db_session, user["user_id"], count=2)
        scan_repo = ScanRepository(db_session)
        failed = scan_repo.create_scan(user_id=user["user_id"], api_name="Old", source_spec={})
        failed.status = "failed"
        failed.risk_level = "Low"
        db_session.commit()

        resp = client.get("/api/v1/scans?status=failed", headers=user["headers"])
        assert resp.json()["meta"]["total"] == 1
        assert resp.json()["data"][0]["api_name"] == "Old"

        resp = client.get("/api/v1/scans?risk_level=High", headers=user["headers"])
        assert resp.json()["meta"]["total"] == 2

    def test_severity_filter_matches_scans_with_finding(self, client, db_session):
        user = _register(client)
        _seed(db_session, user["user_id"], count=2)
        resp = client.get("/api/v1/scans?severity=Critical", headers=user["headers"])
        assert resp.json()["meta"]["total"] == 2
        resp = client.get("/api/v1/scans?severity=Medium", headers=user["headers"])
        assert resp.json()["meta"]["total"] == 0

    def test_search_and_date_range(self, client, db_session):
        user = _register(client)
        _seed(db_session, user["user_id"], count=2)
        resp = client.get("/api/v1/scans?search=Petstore1", headers=user["headers"])
        assert resp.json()["meta"]["total"] == 1

        resp = client.get(
            f"/api/v1/scans?date_from={(utcnow() - timedelta(days=1)).isoformat()}&date_to={utcnow().isoformat()}",
            headers=user["headers"],
        )
        assert resp.json()["meta"]["total"] == 1

    def test_invalid_filter_rejected_with_envelope(self, client):
        user = _register(client)
        for query in ("status=bogus", "risk_level=Meh", "severity=wat", "sort_by=unknown"):
            resp = client.get(f"/api/v1/scans?{query}", headers=user["headers"])
            assert resp.status_code == 422, query
            body = resp.json()
            assert body["success"] is False
            assert body["error"]["code"] == "validation_error"

    def test_invalid_page_rejected(self, client):
        user = _register(client)
        resp = client.get("/api/v1/scans?page=0", headers=user["headers"])
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "validation_error"

    def test_date_range_inverted_rejected(self, client):
        user = _register(client)
        resp = client.get(
            f"/api/v1/scans?date_from={utcnow().isoformat()}&date_to={(utcnow() - timedelta(days=1)).isoformat()}",
            headers=user["headers"],
        )
        assert resp.status_code == 422

    def test_requires_auth(self, client):
        resp = client.get("/api/v1/scans")
        assert resp.status_code == 401
        assert resp.json()["success"] is False
        assert resp.json()["error"]["code"] == "unauthorized"

    def test_excludes_other_users_scans(self, client, db_session):
        user = _register(client, prefix="owner")
        other = _register(client, prefix="other")
        _seed(db_session, user["user_id"], count=2)
        resp = client.get("/api/v1/scans", headers=other["headers"])
        assert resp.json()["meta"]["total"] == 0


class TestScanDetail:
    def test_returns_findings_in_envelope(self, client, db_session):
        user = _register(client)
        ids = _seed(db_session, user["user_id"], count=1)
        resp = client.get(f"/api/v1/scans/{ids[0]}", headers=user["headers"])
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["api_name"] == "Petstore0"
        assert {f["severity"] for f in body["data"]["findings"]} == {"Critical", "Low"}

    def test_missing_scan_is_404(self, client):
        user = _register(client)
        resp = client.get("/api/v1/scans/999999", headers=user["headers"])
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "not_found"

    def test_other_users_scan_is_404(self, client, db_session):
        user = _register(client)
        other = _register(client, prefix="other")
        ids = _seed(db_session, user["user_id"], count=1)
        resp = client.get(f"/api/v1/scans/{ids[0]}", headers=other["headers"])
        assert resp.status_code == 404


class TestFindings:
    def test_paginated_and_severity_order(self, client, db_session):
        user = _register(client)
        ids = _seed(db_session, user["user_id"], count=1)
        resp = client.get(
            f"/api/v1/scans/{ids[0]}/findings?page=1&page_size=1",
            headers=user["headers"],
        )
        body = resp.json()
        assert body["meta"] == {"page": 1, "page_size": 1, "total": 2, "total_pages": 2}
        assert len(body["data"]) == 1

    def test_severity_and_search_filters(self, client, db_session):
        user = _register(client)
        ids = _seed(db_session, user["user_id"], count=1)
        resp = client.get(
            f"/api/v1/scans/{ids[0]}/findings?severity=Critical",
            headers=user["headers"],
        )
        assert resp.json()["meta"]["total"] == 1
        assert resp.json()["data"][0]["vulnerability_name"] == "Broken Auth"

        resp = client.get(
            f"/api/v1/scans/{ids[0]}/findings?search=Info",
            headers=user["headers"],
        )
        assert resp.json()["meta"]["total"] == 1
        assert resp.json()["data"][0]["vulnerability_name"] == "Info Leak"

    def test_scan_ownership_enforced(self, client, db_session):
        user = _register(client)
        other = _register(client, prefix="other")
        ids = _seed(db_session, user["user_id"], count=1)
        resp = client.get(f"/api/v1/scans/{ids[0]}/findings", headers=other["headers"])
        assert resp.status_code == 404


class TestDashboard:
    def test_overview(self, client, db_session):
        user = _register(client)
        _seed(db_session, user["user_id"], count=2)
        resp = client.get("/api/v1/dashboard/overview", headers=user["headers"])
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        assert body["success"] is True
        assert data["total_scans"] == 2
        assert data["completed_scans"] == 2
        assert data["total_vulnerabilities"] == 3
        assert data["average_risk_score"] == 60.5
        assert data["severity_distribution"]["Critical"] == 2
        assert len(data["recent_scans"]) == 2

    def test_overview_empty_state(self, client):
        user = _register(client)
        resp = client.get("/api/v1/dashboard/overview", headers=user["headers"])
        data = resp.json()["data"]
        assert data["total_scans"] == 0
        assert data["average_risk_score"] == 0.0
        assert data["recent_scans"] == []
