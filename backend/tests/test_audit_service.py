"""Audit logging service tests."""

from app.models.models import AuditLog
from app.services.audit_service import record_action, record_report_export, record_scan_event


class TestAuditService:
    def test_record_action(self, db_session, user):
        record_action(
            db_session,
            "auth.login",
            user_id=user.id,
            entity_type="user",
            entity_id=user.id,
            detail={"ip": "10.0.0.1"},
            ip_address="10.0.0.1",
        )
        db_session.commit()
        entry = db_session.query(AuditLog).one()
        assert entry.action == "auth.login"
        assert entry.user_id == user.id
        assert entry.entity_type == "user"
        assert entry.entity_id == user.id
        assert entry.detail == {"ip": "10.0.0.1"}
        assert entry.ip_address == "10.0.0.1"

    def test_record_scan_event(self, db_session, user):
        record_scan_event(
            db_session,
            "scan.completed",
            user_id=user.id,
            scan_id=42,
            detail={"total_vulnerabilities": 3},
        )
        db_session.commit()
        entry = db_session.query(AuditLog).one()
        assert entry.action == "scan.completed"
        assert entry.entity_type == "scan"
        assert entry.entity_id == 42
        assert entry.detail == {"total_vulnerabilities": 3}

    def test_record_report_export(self, db_session, user):
        record_report_export(db_session, user_id=user.id, scan_id=7, format="pdf")
        db_session.commit()
        entry = db_session.query(AuditLog).one()
        assert entry.action == "report.exported.pdf"
        assert entry.entity_type == "report"
        assert entry.detail == {"format": "pdf"}

    def test_user_cascade_deletes_audit(self, db_session, user):
        record_action(db_session, "auth.login", user_id=user.id)
        db_session.commit()
        assert db_session.query(AuditLog).count() == 1

        from app.repositories.users import UserRepository

        UserRepository(db_session).delete(user)
        db_session.commit()
        assert db_session.query(AuditLog).count() == 0
