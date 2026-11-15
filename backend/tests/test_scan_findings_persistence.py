"""Regression tests for the trimmed-findings defect.

A previous change passed ``_trim_findings_for_ai`` output straight into
``FindingRepository.bulk_add_from_scan``. The trimmed dicts carry only
vulnerability_name/severity/owasp_category/cwe_id, but
``from_scan_data`` requires ``description``, ``impact`` and ``remediation``, so
every scan died with ``KeyError: 'description'`` and returned
HTTP 500 "Scan execution failed".

Invariant under test:
  * persistence and risk scoring get the COMPLETE finding dicts
  * only the AI prompt payload is trimmed

No network is used: these tests touch the repository and the pure trim helper.
"""

import pytest

from app.repositories.findings import FindingRepository
from app.services.scan_service import _trim_findings_for_ai


def _finding(**overrides):
    base = {
        "vulnerability_name": "Broken Object Level Authorization",
        "severity": "High",
        "owasp_category": "API1:2023",
        "cwe_id": "CWE-639",
        "confidence": 90,
        "description": "Object ownership is not verified.",
        "impact": "An attacker can read another tenant's data.",
        "remediation": "Check object ownership before returning it.",
    }
    base.update(overrides)
    return base


def test_storage_keeps_description_impact_and_remediation(db_session, scan):
    """Persisting a scanned finding must keep the fields the repository requires."""
    repo = FindingRepository(db_session)
    created = repo.bulk_add_from_scan(scan.id, [_finding()])
    db_session.commit()

    assert len(created) == 1
    from app.models.models import Finding

    row = db_session.query(Finding).filter(Finding.scan_id == scan.id).one()
    assert row.description == "Object ownership is not verified."
    assert row.impact == "An attacker can read another tenant's data."
    assert row.remediation == "Check object ownership before returning it."
    assert row.confidence == 90


def test_ai_payload_contains_only_the_four_prompt_fields():
    """The AI payload is the trimmed copy, with exactly four keys."""
    payload = _trim_findings_for_ai([_finding()])

    assert len(payload) == 1
    assert set(payload[0]) == {
        "vulnerability_name",
        "severity",
        "owasp_category",
        "cwe_id",
    }


def test_trimmed_payload_is_unusable_for_persistence(db_session, scan):
    """Guard the original bug: persisting the trimmed payload fails loudly.

    If someone ever routes the trimmed dicts back into storage, this test turns
    that into an obvious failure instead of a runtime 500 in production.
    """
    repo = FindingRepository(db_session)

    with pytest.raises(KeyError):
        repo.bulk_add_from_scan(scan.id, _trim_findings_for_ai([_finding()]))
