"""Tests for the OSV.dev client and its merge into the dependency scanner.

No network: every test injects a stub HTTP client. The one live test is opt-in
through ``OSV_LIVE=1`` so a normal run stays offline and deterministic.
"""

import os
from pathlib import Path

import pytest

from app.core.dep_scanner.osv_client import (
    CACHE_TTL_SECONDS,
    MAX_QUERIES_PER_REQUEST,
    BatchResult,
    Query,
    clear_cache,
    cvss_v3_base_score,
    query_batch,
    set_clock,
    severity_band,
    skip_reason,
)
from app.core.dep_scanner.scanner import run_dep_scan


class _Response:
    def __init__(self, status_code: int, body: object):
        self.status_code = status_code
        self._body = body

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class _Client:
    """Records discovery POSTs and detail GETs.

    ``handler`` answers querybatch; ``details`` maps an advisory id to the full
    record served by ``GET /v1/vulns/{id}``. Unknown ids get a minimal record,
    which is what OSV itself returns for querybatch.
    """

    def __init__(self, handler, details=None, detail_handler=None):
        self.handler = handler
        self.details = details or {}
        self.detail_handler = detail_handler
        self.calls: list[dict] = []
        self.detail_calls: list[str] = []

    def post(self, url, json=None, timeout=None):
        self.calls.append(json)
        result = self.handler(json, len(self.calls))
        if isinstance(result, Exception):
            raise result
        return result

    def get(self, url, timeout=None):
        vuln_id = url.rsplit("/", 1)[-1]
        self.detail_calls.append(vuln_id)
        if self.detail_handler is not None:
            answer = self.detail_handler(vuln_id, len(self.detail_calls))
            if isinstance(answer, Exception):
                raise answer
            return answer
        return _Response(200, self.details.get(vuln_id, {"id": vuln_id}))


def _vuln(osv_id: str, *, cvss: str | None = None, label: str | None = None, alias=()):
    record = {
        "id": osv_id,
        "summary": f"Summary for {osv_id}",
        "aliases": list(alias),
        "affected": [{"ranges": [{"type": "ECOSYSTEM", "events": [{"fixed": "9.9.9"}]}]}],
    }
    if cvss:
        record["severity"] = [{"type": "CVSS_V3", "score": cvss}]
    if label:
        record["database_specific"] = {"severity": label}
    return record


def _discovery(*ids):
    """querybatch answer naming ``ids`` for the first query and nothing else.

    This is the real shape: ids only, no severity, no aliases, no ranges.
    """

    def handler(payload, _call):
        results = []
        for index, _ in enumerate(payload["queries"]):
            results.append({"vulns": [{"id": osv_id} for osv_id in ids]} if index == 0 else {})
        return _Response(200, {"results": results})

    return handler


def _ok_one_vuln_per_query(payload, _call):
    return _Response(
        200,
        {
            "results": [
                {"vulns": [_vuln(f"OSV-{index}")]} for index, _ in enumerate(payload["queries"])
            ]
        },
    )


@pytest.fixture(autouse=True)
def _clean_cache():
    clear_cache()
    set_clock(None)
    yield
    clear_cache()
    set_clock(None)


class TestBatching:
    def test_150_queries_split_into_two_requests(self):
        queries = [Query(name=f"pkg{i}", version="1.0.0", ecosystem="python") for i in range(150)]
        client = _Client(_ok_one_vuln_per_query)

        result = query_batch(queries, client=client)

        assert len(client.calls) == 2
        assert [len(call["queries"]) for call in client.calls] == [MAX_QUERIES_PER_REQUEST, 50]
        assert result.requests == 2
        assert result.sent == 150
        # One detail GET per distinct advisory, not per package.
        assert len(client.detail_calls) == 150
        assert result.failed is False

    def test_results_stay_aligned_with_the_input(self):
        queries = [Query(name=f"pkg{i}", version="1.0.0", ecosystem="python") for i in range(120)]
        client = _Client(_ok_one_vuln_per_query)

        result = query_batch(queries, client=client)

        # The stub numbers advisories per chunk, so the chunk boundary is visible:
        # the 101st query starts the second request at OSV-0, and the last query is
        # the 20th advisory of that request, not the 120th overall.
        assert [len(vulns) for vulns in result.by_query] == [1] * 120
        assert result.by_query[0][0].id == "OSV-0"
        assert result.by_query[99][0].id == "OSV-99"
        assert result.by_query[100][0].id == "OSV-0"
        assert result.by_query[119][0].id == "OSV-19"

    def test_duplicate_queries_are_sent_once(self):
        queries = [Query(name="django", version="4.2.9", ecosystem="python")] * 5
        client = _Client(_ok_one_vuln_per_query)

        result = query_batch(queries, client=client)

        assert len(client.calls) == 1
        assert len(client.calls[0]["queries"]) == 1
        assert client.detail_calls == ["OSV-0"]
        assert all(len(vulns) == 1 for vulns in result.by_query)


class TestFailures:
    def test_500_is_retried_once_then_falls_back(self):
        client = _Client(lambda payload, call: _Response(500, {}))

        result = query_batch([Query("django", "4.2.9", "python")], client=client)

        assert result.requests == 2
        assert result.failed is True
        assert result.by_query == [[]]
        assert any("HTTP 500" in warning for warning in result.warnings)

    def test_400_is_not_retried(self):
        client = _Client(lambda payload, call: _Response(400, {"message": "bad"}))

        result = query_batch([Query("django", "4.2.9", "python")], client=client)

        assert len(client.calls) == 1
        assert result.requests == 1
        assert result.failed is True
        assert any("HTTP 400" in warning for warning in result.warnings)

    def test_transport_error_is_retried_once_and_never_raises(self):
        client = _Client(lambda payload, call: ConnectionError("boom"))

        result = query_batch([Query("django", "4.2.9", "python")], client=client)

        assert result.requests == 2
        assert result.failed is True
        assert any("ConnectionError" in warning for warning in result.warnings)

    def test_failure_does_not_poison_the_cache(self):
        failing = _Client(lambda payload, call: _Response(503, {}))
        query_batch([Query("django", "4.2.9", "python")], client=failing)

        working = _Client(_ok_one_vuln_per_query)
        second = query_batch([Query("django", "4.2.9", "python")], client=working)

        assert second.cache_hits == 0
        assert len(working.calls) == 1
        assert second.by_query[0][0].id == "OSV-0"

    def test_malformed_body_is_a_warning_not_an_exception(self):
        client = _Client(lambda payload, call: _Response(200, {"unexpected": True}))

        result = query_batch([Query("django", "4.2.9", "python")], client=client)

        assert result.failed is True
        assert result.by_query == [[]]


class TestCache:
    def test_second_call_is_served_from_cache(self):
        client = _Client(_ok_one_vuln_per_query)
        query = Query("django", "4.2.9", "python")

        first = query_batch([query], client=client)
        second = query_batch([query], client=client)

        assert len(client.calls) == 1
        assert client.detail_calls == ["OSV-0"]
        assert first.cache_hits == 0
        assert second.cache_hits == 1
        assert second.by_query[0][0].id == "OSV-0"

    def test_cache_expires_on_the_injected_clock(self):
        client = _Client(_ok_one_vuln_per_query)
        query = Query("django", "4.2.9", "python")
        now = [1000.0]
        set_clock(lambda: now[0])

        query_batch([query], client=client)
        now[0] += CACHE_TTL_SECONDS + 1
        second = query_batch([query], client=client)

        assert len(client.calls) == 2
        assert second.cache_hits == 0

    def test_use_cache_false_always_requests(self):
        client = _Client(_ok_one_vuln_per_query)
        query = Query("django", "4.2.9", "python")

        query_batch([query], client=client)
        query_batch([query], client=client, use_cache=False)

        assert len(client.calls) == 2


class TestQueryValidation:
    @pytest.mark.parametrize(
        "version,reason",
        [
            ("", "no version"),
            ("unknown", "unresolved version"),
            ("${spring.version}", "unresolved version placeholder"),
            ("^4.17.0", "version range"),
            ("~=2.0", "version range"),
            (">=1.0.0", "version range"),
            ("[1,2)", "version range"),
            ("1.x", "version wildcard"),
            ("1.*", "version wildcard"),
            ("latest", "unresolved version"),
        ],
    )
    def test_unusable_versions_are_skipped(self, version, reason):
        assert skip_reason(Query("pkg", version, "python")) == reason

    def test_pinned_versions_are_sent(self):
        assert skip_reason(Query("pkg", "4.2.9", "python")) is None
        assert skip_reason(Query("bcrypt", "1.0.0-beta1", "python")) is None

    def test_skipped_queries_are_never_sent(self):
        client = _Client(_ok_one_vuln_per_query)
        queries = [
            Query("django", "${spring.version}", "java"),
            Query("django", "4.2.9", "python"),
        ]

        result = query_batch(queries, client=client)

        assert len(client.calls[0]["queries"]) == 1
        assert result.skipped_queries == 1
        assert result.skipped[0].reason == "unresolved version placeholder"
        assert result.skipped[0].index == 0
        assert result.by_query[0] == []
        assert len(result.by_query[1]) == 1

    def test_unmapped_ecosystem_is_skipped_with_a_reason(self):
        client = _Client(_ok_one_vuln_per_query)

        result = query_batch([Query("rails", "7.0.0", "ruby")], client=client)

        assert client.calls == []
        assert result.skipped_queries == 1
        assert "no OSV mapping" in result.skipped[0].reason
        assert "ruby" in result.skipped[0].reason


class TestSeverity:
    def test_cvss_vector_is_scored_and_banded(self):
        # The classic Log4Shell vector: exactly 10.0.
        vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H"
        assert cvss_v3_base_score(vector) == 10.0
        assert severity_band(10.0) == "Critical"

    def test_medium_cvss_vector(self):
        assert cvss_v3_base_score("CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:H") == 6.5
        assert severity_band(6.5) == "Medium"

    def test_unparsable_vector_returns_none_rather_than_a_guess(self):
        assert cvss_v3_base_score("nonsense") is None
        assert cvss_v3_base_score("") is None
        assert cvss_v3_base_score(None) is None

    def test_database_specific_label_is_used_when_no_vector(self):
        client = _Client(
            _discovery("GHSA-1"), details={"GHSA-1": _vuln("GHSA-1", label="MODERATE")}
        )

        result = query_batch([Query("flask", "2.3.1", "python")], client=client)

        assert result.by_query[0][0].severity == "Medium"
        assert result.by_query[0][0].cvss_score is None

    def test_cvss_vector_on_the_detail_record_wins_over_the_label(self):
        record = _vuln("GHSA-2", cvss="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", label="LOW")
        client = _Client(_discovery("GHSA-2"), details={"GHSA-2": record})

        result = query_batch([Query("flask", "2.3.1", "python")], client=client)

        assert result.by_query[0][0].cvss_score == 9.8
        assert result.by_query[0][0].severity == "Critical"

    def test_no_vector_and_no_label_stays_unknown(self):
        client = _Client(_discovery("GHSA-3"), details={"GHSA-3": _vuln("GHSA-3")})

        result = query_batch([Query("flask", "2.3.1", "python")], client=client)

        assert result.by_query[0][0].severity is None
        assert result.by_query[0][0].cvss_score is None

    def test_range_only_versions_are_not_used_as_the_installed_version(self):
        record = {
            "id": "GHSA-4",
            "affected": [{"ranges": [{"events": [{"introduced": "0"}, {"fixed": "2.0.1"}]}]}],
        }
        client = _Client(_discovery("GHSA-4"), details={"GHSA-4": record})

        result = query_batch([Query("flask", "2.3.1", "python")], client=client)

        assert result.by_query[0][0].fixed_versions == ("2.0.1",)

    def test_detail_failure_keeps_the_finding_with_unknown_severity(self):
        client = _Client(
            _discovery("GHSA-5"),
            detail_handler=lambda vuln_id, call: _Response(500, {}),
        )

        result = query_batch([Query("flask", "2.3.1", "python")], client=client)

        assert [vuln.id for vuln in result.by_query[0]] == ["GHSA-5"]
        assert result.by_query[0][0].severity is None
        assert result.detail_failures == ["GHSA-5"]
        assert any("could not be loaded in full" in warning for warning in result.warnings)

    def test_detail_failure_is_not_cached(self):
        broken = _Client(_discovery("GHSA-6"), detail_handler=lambda vid, call: _Response(502, {}))
        query_batch([Query("flask", "2.3.1", "python")], client=broken)

        healthy = _Client(_discovery("GHSA-6"), details={"GHSA-6": _vuln("GHSA-6", label="HIGH")})
        second = query_batch([Query("flask", "2.3.1", "python")], client=healthy)

        assert second.cache_hits == 0
        assert second.by_query[0][0].severity == "High"


class TestMerge:
    def _requirements(self, tmp_path: Path, content: str) -> Path:
        path = tmp_path / "requirements.txt"
        path.write_text(content, encoding="utf-8")
        return path

    def test_curated_entry_wins_over_the_osv_record_for_the_same_cve(self, tmp_path):
        path = self._requirements(tmp_path, "django==4.2.9\n")
        client = _Client(
            _discovery("GHSA-django-dos"),
            details={
                "GHSA-django-dos": _vuln("GHSA-django-dos", alias=["CVE-2024-24680"], label="LOW")
            },
        )

        result = run_dep_scan(path, osv_client=client, use_osv=True)

        matches = [f for f in result.findings if f.cve_id == "CVE-2024-24680"]
        assert len(matches) == 1, "an aliased GHSA entry must not duplicate the curated CVE"
        assert "urlquote" in matches[0].description
        assert result.merge_counts["overlap"] == 1
        assert result.merge_counts["osv_only"] == 0

    def test_osv_only_package_is_added(self, tmp_path):
        path = self._requirements(tmp_path, "some-package==1.0.0\n")
        client = _Client(
            _discovery("GHSA-new"), details={"GHSA-new": _vuln("GHSA-new", label="HIGH")}
        )

        result = run_dep_scan(path, osv_client=client, use_osv=True)

        assert [f.cve_id for f in result.findings] == ["GHSA-new"]
        assert result.findings[0].severity == "High"
        assert result.merge_counts["osv_only"] == 1
        assert result.merge_counts["overlap"] == 0

    def test_unknown_severity_is_reported_as_unknown_not_high(self, tmp_path):
        path = self._requirements(tmp_path, "some-package==1.0.0\n")
        client = _Client(
            _discovery("GHSA-unrated"), details={"GHSA-unrated": _vuln("GHSA-unrated")}
        )

        result = run_dep_scan(path, osv_client=client, use_osv=True)

        finding = result.findings[0]
        assert finding.severity == "unknown"
        assert finding.cvss_score == 0.0
        assert "no severity rating" in finding.description

    def test_osv_failure_falls_back_to_curated_with_a_warning(self, tmp_path):
        path = self._requirements(tmp_path, "django==4.2.9\n")
        client = _Client(lambda payload, call: _Response(500, {}))

        result = run_dep_scan(path, osv_client=client, use_osv=True)

        assert result.findings, "curated findings must survive an OSV outage"
        assert all(f.severity != "unknown" for f in result.findings)
        assert any("OSV" in error for error in result.errors)
        assert result.osv_warnings

    def test_two_manifests_with_the_same_package_produce_one_finding(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("django==4.2.9\n", encoding="utf-8")
        nested = tmp_path / "sub"
        nested.mkdir()
        (nested / "requirements.txt").write_text("django==4.2.9\n", encoding="utf-8")

        result = run_dep_scan(tmp_path, use_osv=False)

        identities = [(f.package, f.cve_id) for f in result.findings]
        assert len(identities) == len(set(identities))
        assert result.total_dependencies == 2

    def test_osv_disabled_keeps_the_scan_offline(self, tmp_path):
        path = self._requirements(tmp_path, "django==4.2.9\n")
        client = _Client(_ok_one_vuln_per_query)

        result = run_dep_scan(path, osv_client=client, use_osv=False)

        assert client.calls == []
        assert result.merge_counts.get("osv_disabled") == 1
        assert result.findings


@pytest.mark.skipif(
    os.environ.get("OSV_LIVE") != "1",
    reason="set OSV_LIVE=1 to query the real api.osv.dev",
)
class TestLiveOsv:
    def test_real_query_returns_without_raising(self):
        result: BatchResult = query_batch(
            [
                Query("requests", "2.30.0", "python"),
                Query("django", "4.2.9", "python"),
            ],
            use_cache=False,
        )

        assert result.failed is False
        assert result.requests == 1
        assert result.vuln_count >= 1
        # The detail step is what supplies severity and aliases; without it every
        # finding would be unrated, so prove at least one record got a band.
        assert all(vuln.id for vulns in result.by_query for vuln in vulns)
        assert any(vuln.severity is not None for vulns in result.by_query for vuln in vulns)
