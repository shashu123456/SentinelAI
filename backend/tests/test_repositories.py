"""Repository layer tests: CRUD, ownership, soft delete, pagination, aggregates."""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.models.models import AuditLog, Finding, Scan, User
from app.repositories.audit import AuditLogRepository
from app.repositories.findings import FindingRepository
from app.repositories.refresh_tokens import RefreshTokenRepository
from app.repositories.reports import ReportRepository
from app.repositories.scans import ScanRepository
from app.repositories.users import UserRepository
from app.schemas.schemas import FindingListParams, ScanListParams
from app.utils.security import hash_password, utcnow


class TestUserRepository:
    def test_create_and_fetch(self, db_session, user):
        assert user.id is not None
        repo = UserRepository(db_session)
        assert repo.get_by_username("repo_user") is user
        assert repo.get_by_email("repo_user@example.com") is user

    def test_get_by_username_or_email_any_field(self, db_session, user):
        repo = UserRepository(db_session)
        assert repo.get_by_username_or_email("nope", "repo_user@example.com") is user
        assert repo.get_by_username_or_email("repo_user", "nope@example.com") is user
        assert repo.get_by_username_or_email("nope", "nope@example.com") is None

    def test_failed_attempts_and_lock(self, db_session, user):
        repo = UserRepository(db_session)
        lock_until = utcnow() + timedelta(minutes=15)
        repo.register_failed_attempt(user, None)
        db_session.commit()
        assert user.failed_login_attempts == 1
        repo.register_failed_attempt(user, lock_until)
        db_session.commit()
        assert user.failed_login_attempts == 2
        assert user.locked_until == lock_until
        repo.reset_failed_attempts(user)
        db_session.commit()
        assert user.failed_login_attempts == 0
        assert user.locked_until is None

    def test_lock_unlock(self, db_session, user):
        repo = UserRepository(db_session)
        repo.lock(user, utcnow() + timedelta(minutes=5))
        db_session.commit()
        assert user.locked_until is not None
        repo.unlock(user)
        db_session.commit()
        assert user.locked_until is None
        assert user.failed_login_attempts == 0

    def test_delete_user(self, db_session, user):
        UserRepository(db_session).delete(user)
        db_session.commit()
        assert db_session.get(User, user.id) is None


class TestScanRepository:
    def test_create_stores_source_spec(self, db_session, user):
        repo = ScanRepository(db_session)
        s = repo.create_scan(
            user_id=user.id,
            api_name="A",
            source_spec={"openapi": "3.0.0", "info": {"title": "A"}},
        )
        repo.add(s)
        db_session.commit()
        assert s.source_spec == {"openapi": "3.0.0", "info": {"title": "A"}}

    def test_get_owned_respects_ownership(self, db_session, user, scan):
        other = UserRepository(db_session).create(
            username="other",
            email="other@example.com",
            hashed_password=hash_password("testpass123"),
        )
        db_session.commit()
        repo = ScanRepository(db_session)
        assert repo.get_owned(scan.id, user.id) is scan
        assert repo.get_owned(scan.id, other.id) is None

    def test_soft_delete_excludes_from_queries(self, db_session, user, scan):
        repo = ScanRepository(db_session)
        repo.soft_delete(scan)
        db_session.commit()
        assert repo.get_owned(scan.id, user.id) is None
        assert scan.id not in [s.id for s in repo.list_by_user(user.id)]
        assert repo.count_for_user(user.id) == 0

    def test_paginate(self, db_session, user):
        repo = ScanRepository(db_session)
        for i in range(25):
            s = repo.create_scan(user_id=user.id, api_name=f"S{i}", source_spec={})
            repo.add(s)
        db_session.commit()

        page1, total = repo.paginate(
            Scan.user_id == user.id,
            Scan.deleted_at.is_(None),
            page=1,
            page_size=10,
            order_by=Scan.id.asc(),
        )
        page3, _ = repo.paginate(
            Scan.user_id == user.id,
            Scan.deleted_at.is_(None),
            page=3,
            page_size=10,
            order_by=Scan.id.asc(),
        )
        assert total == 25
        assert len(page1) == 10
        assert len(page3) == 5
        assert page1[0].id < page1[-1].id

    def test_aggregates_exclude_deleted(self, db_session, user, scan):
        repo = ScanRepository(db_session)
        s2 = repo.create_scan(user_id=user.id, api_name="B", source_spec={})
        repo.add(s2)
        s2.status = "completed"
        s2.risk_score = 50
        s2.total_vulnerabilities = 4
        db_session.commit()

        assert repo.count_for_user(user.id) == 2
        assert repo.total_vulnerabilities_for_user(user.id) == 4
        assert repo.average_risk_for_user(user.id) == 50.0

        repo.soft_delete(s2)
        db_session.commit()
        assert repo.count_for_user(user.id) == 1
        assert repo.total_vulnerabilities_for_user(user.id) == 0

    def test_list_for_user_filtered_status_search_pagination(self, db_session, user):
        repo = ScanRepository(db_session)
        for i in range(5):
            s = repo.create_scan(user_id=user.id, api_name=f"Petstore{i}", source_spec={})
            s.status = "completed"
            s.risk_level = "High"
            s.risk_score = 70 + i
            s.total_vulnerabilities = 3
            repo.add(s)
        db_session.commit()

        items, total = repo.list_for_user_filtered(
            user.id,
            ScanListParams(
                page=1,
                page_size=2,
                status="completed",
                risk_level="High",
                search="Petstore3",
                sort_by="-risk_score",
            ),
        )
        assert total == 1
        assert [s.api_name for s in items] == ["Petstore3"]

        items, total = repo.list_for_user_filtered(
            user.id, ScanListParams(page=1, page_size=10, sort_by="-risk_score")
        )
        assert total == 5
        assert [s.risk_score for s in items] == [74, 73, 72, 71, 70]

    def test_list_for_user_filtered_severity_and_date_range(self, db_session, user, scan):
        repo = ScanRepository(db_session)
        finding_repo = FindingRepository(db_session)
        s2 = repo.create_scan(user_id=user.id, api_name="AuthSvc", source_spec={})
        repo.add(s2)
        db_session.commit()
        finding_repo.bulk_add_from_scan(
            s2.id,
            [
                {
                    "vulnerability_name": "Broken Auth",
                    "owasp_category": "API2",
                    "severity": "Critical",
                    "description": "d",
                    "impact": "i",
                    "remediation": "r",
                }
            ],
        )
        db_session.commit()

        items, total = repo.list_for_user_filtered(user.id, ScanListParams(severity="Critical"))
        assert total == 1
        assert items[0].id == s2.id

        items, total = repo.list_for_user_filtered(user.id, ScanListParams(severity="Low"))
        assert total == 0

        scan.created_at = utcnow() - timedelta(days=10)
        db_session.commit()
        items, total = repo.list_for_user_filtered(
            user.id,
            ScanListParams(date_from=utcnow() - timedelta(days=5)),
        )
        assert total == 1
        assert items[0].id == s2.id

    def test_list_for_user_filtered_excludes_other_users_and_deleted(self, db_session, user, scan):
        repo = ScanRepository(db_session)
        other = UserRepository(db_session).create(
            username="other2",
            email="other2@example.com",
            hashed_password=hash_password("testpass123"),
        )
        db_session.commit()
        repo.add(repo.create_scan(user_id=other.id, api_name="OtherSvc", source_spec={}))
        repo.soft_delete(scan)
        db_session.commit()

        items, total = repo.list_for_user_filtered(user.id, ScanListParams())
        assert total == 0
        assert items == []


class TestFindingRepository:
    def test_bulk_add_maps_new_columns(self, db_session, scan):
        repo = FindingRepository(db_session)
        repo.bulk_add_from_scan(
            scan.id,
            [
                {
                    "vulnerability_name": "Broken Auth",
                    "owasp_category": "API2",
                    "cwe_id": "CWE-287",
                    "severity": "High",
                    "confidence": 90,
                    "description": "d",
                    "impact": "i",
                    "remediation": "r",
                    "technical_impact": "t",
                    "business_impact": "b",
                    "request_example": "req",
                    "response_example": "resp",
                    "fix_recommendation": "fix",
                    "references": ["https://example.com"],
                    "cvss_score": 8.1,
                    "cvss_vector": "CVSS:3.1/AV:N",
                    "affected_endpoint": "/users",
                    "affected_method": "GET",
                    "detection_reason": "reason",
                    "false_positive_note": "note",
                }
            ],
        )
        db_session.commit()
        f = db_session.scalars(select(Finding)).first()
        assert f is not None
        assert f.technical_impact == "t"
        assert f.business_impact == "b"
        assert f.request_example == "req"
        assert f.response_example == "resp"
        assert f.fix_recommendation == "fix"
        assert f.references == ["https://example.com"]
        assert f.cvss_score == 8.1
        assert f.cvss_vector == "CVSS:3.1/AV:N"

    def test_severity_counts(self, db_session, scan, user):
        repo = FindingRepository(db_session)
        repo.bulk_add_from_scan(
            scan.id,
            [
                {
                    "vulnerability_name": "A",
                    "owasp_category": "API1",
                    "severity": "Critical",
                    "description": "d",
                    "impact": "i",
                    "remediation": "r",
                },
                {
                    "vulnerability_name": "B",
                    "owasp_category": "API1",
                    "severity": "Low",
                    "description": "d",
                    "impact": "i",
                    "remediation": "r",
                },
            ],
        )
        db_session.commit()
        dist = repo.severity_counts_for_user(user.id)
        assert dist["Critical"] == 1
        assert dist["Low"] == 1
        assert dist["High"] == 0
        assert dist["Medium"] == 0
        assert dist["Info"] == 0

    def test_paginate_for_scan_filters_and_sorts(self, db_session, scan):
        repo = FindingRepository(db_session)
        repo.bulk_add_from_scan(
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
                    "vulnerability_name": "Mass Assignment",
                    "owasp_category": "API6",
                    "severity": "High",
                    "description": "d",
                    "impact": "i",
                    "remediation": "r",
                    "affected_endpoint": "/users",
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
        db_session.commit()

        items, total = repo.paginate_for_scan(scan.id, FindingListParams())
        assert total == 3
        assert [f.severity for f in items] == ["Critical", "High", "Low"]

        items, total = repo.paginate_for_scan(
            scan.id, FindingListParams(severity="High", sort_by="-affected_endpoint")
        )
        assert total == 1
        assert items[0].vulnerability_name == "Mass Assignment"

        items, total = repo.paginate_for_scan(scan.id, FindingListParams(search="admin"))
        assert total == 1
        assert items[0].vulnerability_name == "Broken Auth"


class TestListParamsValidation:
    def test_rejects_non_whitelisted_values(self):
        with pytest.raises(ValidationError):
            ScanListParams(status="bogus")
        with pytest.raises(ValidationError):
            ScanListParams(risk_level="Nope")
        with pytest.raises(ValidationError):
            ScanListParams(severity="Whatever")
        with pytest.raises(ValidationError):
            ScanListParams(sort_by="created_at,unknown_field")
        with pytest.raises(ValidationError):
            ScanListParams(page=0)
        with pytest.raises(ValidationError):
            ScanListParams(
                date_from=datetime(2026, 1, 10), date_to=datetime(2026, 1, 1)
            )

    def test_multi_sort_direction_resolution(self):
        p = ScanListParams(sort_by="created_at,-risk_score,api_name", order="asc")
        assert p.sort_columns() == [
            ("created_at", False),
            ("risk_score", True),
            ("api_name", False),
        ]
        p2 = ScanListParams(sort_by="created_at,-risk_score", order="desc")
        assert p2.sort_columns() == [
            ("created_at", True),
            ("risk_score", True),
        ]


class TestRefreshTokenRepository:
    def test_create_fetch_revoke(self, db_session, user):
        repo = RefreshTokenRepository(db_session)
        r = repo.create(user.id, "abc123hash", utcnow() + timedelta(days=7), ip_address="127.0.0.1")
        db_session.commit()
        assert repo.get_by_hash("abc123hash") is r
        repo.revoke(r, replaced_by="newhash")
        db_session.commit()
        assert r.revoked_at is not None
        assert r.replaced_by == "newhash"

    def test_revoke_all_for_user(self, db_session, user):
        repo = RefreshTokenRepository(db_session)
        repo.create(user.id, "h1", utcnow() + timedelta(days=1))
        repo.create(user.id, "h2", utcnow() + timedelta(days=1))
        db_session.commit()
        repo.revoke_all_for_user(user.id)
        db_session.commit()
        assert all(r.revoked_at is not None for r in repo.list_for_user(user.id))


class TestAuditLogRepository:
    def test_create_and_paginate(self, db_session, user):
        repo = AuditLogRepository(db_session)
        for i in range(15):
            repo.create(
                "scan.started", user_id=user.id, entity_type="scan", entity_id=i, detail={"n": i}
            )
        db_session.commit()
        items, total = repo.paginate(page=1, page_size=10)
        assert total == 15
        assert len(items) == 10
        assert items[0].created_at >= items[-1].created_at
        assert all(isinstance(i, AuditLog) for i in items)


class TestReportRepository:
    def test_create_and_get_for_scan(self, db_session, scan):
        repo = ReportRepository(db_session)
        repo.create(scan, "pdf", b"%PDF-1.4")
        db_session.commit()
        found = repo.get_for_scan(scan.id, "pdf")
        assert found is not None
        assert found.content == b"%PDF-1.4"
        assert repo.get_for_scan(scan.id, "json") is None
