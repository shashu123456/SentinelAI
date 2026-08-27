"""Performance sanity checks for dashboard / list queries.

Not a benchmark — guards against accidental N+1 or unbounded query patterns by
verifying aggregate queries complete quickly and return correct counts on a
seeded dataset.
"""

import time

from app.models.models import Scan
from app.repositories.scans import ScanRepository


def _seed_scans(db_session, user, count):
    repo = ScanRepository(db_session)
    for i in range(count):
        s = repo.create_scan(
            user_id=user.id,
            api_name=f"API {i}",
            source_spec={"openapi": "3.0.0", "info": {"title": f"API {i}", "version": "1.0"}},
        )
        s.status = "completed"
        s.risk_score = i % 100
        s.total_vulnerabilities = i % 20
        repo.add(s)
    db_session.commit()


class TestPerformanceSanity:
    def test_dashboard_aggregates_on_seeded_data(self, db_session, user):
        _seed_scans(db_session, user, 200)
        repo = ScanRepository(db_session)

        start = time.perf_counter()
        total = repo.count_for_user(user.id)
        vulns = repo.total_vulnerabilities_for_user(user.id)
        avg = repo.average_risk_for_user(user.id)
        dist = repo.severity_distribution_for_user(user.id)
        recent = repo.recent_for_user(user.id, limit=10)
        elapsed = time.perf_counter() - start

        assert total == 200
        assert vulns == sum(i % 20 for i in range(200))
        assert 0 <= avg <= 100
        assert sum(dist.values()) == 0
        assert len(recent) == 10
        assert elapsed < 5.0, f"aggregate queries too slow: {elapsed:.2f}s"

    def test_paginate_last_page(self, db_session, user):
        _seed_scans(db_session, user, 12)
        repo = ScanRepository(db_session)
        items, total = repo.paginate(
            Scan.user_id == user.id,
            Scan.deleted_at.is_(None),
            page=2,
            page_size=10,
            order_by=Scan.id.asc(),
        )
        assert total == 12
        assert len(items) == 2
