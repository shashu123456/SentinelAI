"""Client for OSV.dev: batch discovery plus per-advisory detail.

OSV's ``querybatch`` endpoint answers with **ids only** — ``{"id", "modified"}``
per match, no severity, no aliases, no affected ranges. Measured 2026-11-15::

    POST /v1/querybatch {"queries":[{"package":{"name":"requests",
                          "ecosystem":"PyPI"},"version":"2.30.0"}]}
    -> {"results":[{"vulns":[{"id":"GHSA-9hjg-9r4m-mvj7","modified":"..."}]}]}

So discovery alone cannot fill a finding: it yields no severity band, no CVE
aliases (which is what lets a GHSA advisory collapse with a curated CVE entry)
and no fixed version. This client therefore runs two steps and caches both:

1. ``POST /v1/querybatch`` — up to 100 packages per request, the cheap part.
2. ``GET /v1/vulns/{id}`` — full record, fetched concurrently, once per advisory
   per call and then cached for an hour.

Rules that do not bend:

* **It never sends garbage.** A Maven version can be ``${spring.version}`` and an
  npm range can be ``^4.17.0``; neither is a version OSV can match. Those queries
  are skipped and counted, never guessed at.
* **It never invents a severity.** No CVSS vector and no
  ``database_specific.severity`` means ``severity is None``; the band comes from
  the CVSS v3.1 base-score formula when a vector is present.
* **It never raises.** Timeouts, a 500 that survives one retry, malformed bodies:
  each becomes a warning and an empty list, so the caller can fall back to its
  curated table.
"""

from __future__ import annotations

import logging
import math
import re
import threading
import time
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

OSV_QUERYBATCH_URL = "https://api.osv.dev/v1/querybatch"
OSV_VULN_URL = "https://api.osv.dev/v1/vulns/{vuln_id}"
MAX_QUERIES_PER_REQUEST = 100
#: Advisories whose full record is fetched per call. Beyond this the extra ids
#: are kept (so they still appear) but stay un-enriched, with a warning.
MAX_DETAIL_FETCHES = 300
DETAIL_WORKERS = 8
CACHE_TTL_SECONDS = 3600.0
DEFAULT_TIMEOUT_SECONDS = 10.0
USER_AGENT = "SentinelAI/1.0 (dependency scanner; +https://github.com/shashu123456/SentinelAI)"

#: Scanner ecosystem -> the name OSV expects in ``package.ecosystem``.
ECOSYSTEM_TO_OSV: dict[str, str] = {
    "python": "PyPI",
    "javascript": "npm",
    "java": "Maven",
}

# A component that is a wildcard makes the whole version a range, not a version.
_WILDCARD_COMPONENTS = {"x", "X", "*"}

# What a pinned version looks like: starts with a digit, no operators, no ranges.
_PINNED_VERSION = re.compile(r"^\d[A-Za-z0-9._+-]*$")

_SEVERITY_BANDS = ((9.0, "Critical"), (7.0, "High"), (4.0, "Medium"), (0.1, "Low"))


@dataclass(frozen=True)
class Query:
    """One dependency to look up. ``ecosystem`` is the scanner's vocabulary."""

    name: str
    version: str
    ecosystem: str


@dataclass(frozen=True)
class SkippedQuery:
    """A dependency the client refused to send, and why."""

    index: int
    name: str
    version: str
    ecosystem: str
    reason: str


@dataclass(frozen=True)
class OsvVuln:
    """A vulnerability record as OSV published it, with nothing guessed."""

    id: str
    aliases: tuple[str, ...] = ()
    summary: str = ""
    details: str = ""
    cvss_vector: str | None = None
    cvss_score: float | None = None
    #: One of Critical/High/Medium/Low, or None when OSV published no rating.
    severity: str | None = None
    cwe_ids: tuple[str, ...] = ()
    fixed_versions: tuple[str, ...] = ()

    @property
    def cve_ids(self) -> tuple[str, ...]:
        """CVE identifiers this record answers to, its own id included."""
        found = [self.id] if self.id.upper().startswith("CVE-") else []
        found.extend(alias for alias in self.aliases if alias.upper().startswith("CVE-"))
        return tuple(dict.fromkeys(found))

    @property
    def identity(self) -> str:
        """Stable identity for de-duplication.

        A GHSA advisory that aliases a CVE must collapse with the curated entry
        for that CVE, so a CVE alias always wins over the OSV id. Two OSV records
        for the same CVE (GHSA and PYSEC twins) collapse with each other the same
        way.
        """
        cves = self.cve_ids
        return cves[0] if cves else self.id

    @property
    def reference_url(self) -> str:
        return f"https://osv.dev/vulnerability/{self.id}"


@dataclass
class BatchResult:
    """Vulns per input query, plus everything the client had to leave out."""

    by_query: list[list[OsvVuln]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped: list[SkippedQuery] = field(default_factory=list)
    #: Advisory ids whose full record could not be loaded this call.
    detail_failures: list[str] = field(default_factory=list)
    requests: int = 0
    sent: int = 0
    cache_hits: int = 0
    detail_requests: int = 0
    failed: bool = False

    @property
    def skipped_queries(self) -> int:
        return len(self.skipped)

    @property
    def vuln_count(self) -> int:
        return sum(len(vulns) for vulns in self.by_query)

    def skip_reasons(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for skipped in self.skipped:
            counts[skipped.reason] = counts.get(skipped.reason, 0) + 1
        return counts


# --------------------------------------------------------------------------- #
# Severity
# --------------------------------------------------------------------------- #


def cvss_v3_base_score(vector: str | None) -> float | None:
    """Return the CVSS v3.0/3.1 base score for ``vector``, or None.

    Implements the base-score section of the specification (FIRST, "CVSS v3.1:
    Specification Document", section 7.1). Scope-changed metrics use the
    alternate PR/Impact constants. An unparsable or incomplete vector returns
    None rather than a default: a made-up score is worse than no score.
    """
    if not vector:
        return None
    metrics = _parse_cvss_vector(vector)
    if metrics is None:
        return None

    scope_changed = metrics["S"] == "C"
    try:
        av = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}[metrics["AV"]]
        ac = {"L": 0.77, "H": 0.44}[metrics["AC"]]
        ui = {"N": 0.85, "R": 0.62}[metrics["UI"]]
        if scope_changed:
            pr = {"N": 0.85, "L": 0.68, "H": 0.5}[metrics["PR"]]
        else:
            pr = {"N": 0.85, "L": 0.62, "H": 0.27}[metrics["PR"]]
        cia = {"H": 0.56, "L": 0.22, "N": 0.0}
        c, i, a = cia[metrics["C"]], cia[metrics["I"]], cia[metrics["A"]]
    except KeyError:
        return None

    isc_base = 1 - (1 - c) * (1 - i) * (1 - a)
    if scope_changed:
        impact = 7.52 * (isc_base - 0.029) - 3.25 * (isc_base - 0.02) ** 15
    else:
        impact = 6.42 * isc_base
    if impact <= 0:
        return 0.0

    exploitability = 8.22 * av * ac * pr * ui
    raw = min((1.08 if scope_changed else 1.0) * (impact + exploitability), 10.0)
    return math.ceil(raw * 10) / 10


def _parse_cvss_vector(vector: str) -> dict[str, str] | None:
    parts = vector.strip().split("/")
    if parts and parts[0].upper().startswith("CVSS:3"):
        parts = parts[1:]
    metrics: dict[str, str] = {}
    for part in parts:
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        metrics[key.strip().upper()] = value.strip().upper()
    required = ("AV", "AC", "PR", "UI", "S", "C", "I", "A")
    if not all(key in metrics for key in required):
        return None
    return metrics


def severity_band(score: float | None) -> str | None:
    """Map a CVSS base score onto a band, or None when there is no score."""
    if score is None:
        return None
    for threshold, band in _SEVERITY_BANDS:
        if score >= threshold:
            return band
    return None


def severity_from_label(label: Any) -> str | None:
    """Map an OSV/GHSA severity label onto a band.

    GitHub advisories publish ``database_specific.severity`` ("MODERATE",
    "HIGH", ...); records with neither that nor a vector have no label at all, and
    this returns None rather than assuming a middle band.
    """
    if not label:
        return None
    text = str(label).strip().lower()
    return {
        "critical": "Critical",
        "high": "High",
        "moderate": "Medium",
        "medium": "Medium",
        "low": "Low",
    }.get(text)


# --------------------------------------------------------------------------- #
# Cache (in-process, TTL, injectable clock)
# --------------------------------------------------------------------------- #

_CACHE: dict[tuple[str, str, str], tuple[float, list[OsvVuln]]] = {}
_CACHE_LOCK = threading.Lock()


def _monotonic() -> float:
    return time.monotonic()


#: Indirection so tests can move time without sleeping.
_clock: Callable[[], float] = _monotonic


def set_clock(now: Callable[[], float] | None = None) -> None:
    """Replace the cache clock. ``None`` restores the monotonic default."""
    global _clock
    _clock = now or _monotonic


def clear_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()


def cache_size() -> int:
    with _CACHE_LOCK:
        return len(_CACHE)


def _cache_get(key: tuple[str, str, str], now: float) -> list[OsvVuln] | None:
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry is None:
            return None
        stored_at, vulns = entry
        if now - stored_at >= CACHE_TTL_SECONDS:
            del _CACHE[key]
            return None
        return vulns


def _cache_put(key: tuple[str, str, str], vulns: list[OsvVuln], now: float) -> None:
    with _CACHE_LOCK:
        _CACHE[key] = (now, vulns)


# --------------------------------------------------------------------------- #
# Query validation
# --------------------------------------------------------------------------- #


def skip_reason(query: Query) -> str | None:
    """Why this query cannot be sent as-is, or None when it can.

    The scanner's parsers do not resolve Maven properties or npm ranges, so a
    version like ``${spring.version}`` or ``^4.17.0`` is a fact about the
    manifest, not a version tuple. Sending it would make OSV answer confidently
    about a package nobody is running.
    """
    version = (query.version or "").strip()
    if not version:
        return "no version"
    if version.lower() in {"unknown", "unspecified", "latest", "*"}:
        return "unresolved version"
    if "${" in version or "#{" in version:
        return "unresolved version placeholder"
    if version.startswith(("^", "~", ">", "<", "=", "!", "[")):
        return "version range"
    if "||" in version or " - " in version or "," in version:
        return "version range"
    components = re.split(r"[.]", version)
    if any(component in _WILDCARD_COMPONENTS for component in components):
        return "version wildcard"
    if not _PINNED_VERSION.match(version):
        return "unresolved version"
    return None


def ecosystem_for(query: Query) -> str | None:
    """Return the OSV ecosystem name, or None when this ecosystem is unmapped."""
    return ECOSYSTEM_TO_OSV.get((query.ecosystem or "").strip().lower())


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #

_session_lock = threading.Lock()
_session: Any = None


def _default_client() -> Any:
    """One shared ``requests.Session``: connection pooling matters for details."""
    global _session
    with _session_lock:
        if _session is None:
            import requests

            session = requests.Session()
            session.headers.update({"User-Agent": USER_AGENT})
            _session = session
        return _session


def _call(
    method: str, url: str, http: Any, timeout: float, **kwargs: Any
) -> tuple[int | None, Any, str | None]:
    """One HTTP call. Returns ``(status, body, error)`` and never raises."""
    try:
        response = getattr(http, method)(url, timeout=timeout, **kwargs)
    except Exception as exc:  # connection error, timeout, TLS, anything
        return None, None, f"{type(exc).__name__}: {exc}"

    status = getattr(response, "status_code", None)
    try:
        body = response.json()
    except Exception:
        body = None
    return status, body, None


def _request_with_retry(
    method: str,
    url: str,
    http: Any,
    timeout: float,
    result: BatchResult,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """One request, retried exactly once and only for 5xx or transport failures."""
    attempts = 0
    while attempts < 2:
        attempts += 1
        result.requests += 1
        status, body, error = _call(method, url, http, timeout, **kwargs)

        if error is not None:
            logger.debug("OSV %s %s failed: %s", method.upper(), url, error)
            if attempts < 2:
                continue
            result.warnings.append(f"OSV request failed twice ({error}); using curated data")
            return None

        assert status is not None  # no error means we have a status
        if 200 <= status < 300:
            return body if isinstance(body, dict) else None
        if 400 <= status < 500:
            result.warnings.append(f"OSV rejected the request with HTTP {status}; not retrying")
            return None
        if attempts >= 2:
            result.warnings.append(f"OSV returned HTTP {status} twice; using curated data")
            return None

    return None


def _chunks(items: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #


def query_batch(
    queries: Sequence[Query],
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    client: Any = None,
    use_cache: bool = True,
    fetch_details: bool = True,
) -> BatchResult:
    """Look up ``queries`` on OSV, at most 100 packages per request.

    ``client`` is anything with ``post``/``get``; tests pass a stub. The returned
    ``by_query`` list is aligned with ``queries`` by index and holds an empty list
    for every skipped or failed query.
    """
    result = BatchResult(by_query=[[] for _ in queries])
    http = client if client is not None else _default_client()
    pending: list[tuple[Query, tuple[str, str, str], str]] = []
    pending_indexes: dict[tuple[str, str, str], list[int]] = {}
    now = _clock()

    for index, query in enumerate(queries):
        reason = skip_reason(query)
        if reason:
            result.skipped.append(
                SkippedQuery(
                    index=index,
                    name=query.name,
                    version=query.version,
                    ecosystem=query.ecosystem,
                    reason=reason,
                )
            )
            continue

        osv_ecosystem = ecosystem_for(query)
        if osv_ecosystem is None:
            result.skipped.append(
                SkippedQuery(
                    index=index,
                    name=query.name,
                    version=query.version,
                    ecosystem=query.ecosystem,
                    reason=f"ecosystem '{query.ecosystem}' has no OSV mapping",
                )
            )
            continue

        cache_key = (osv_ecosystem, query.name.lower(), query.version)
        if use_cache:
            cached = _cache_get(cache_key, now)
            if cached is not None:
                result.by_query[index] = list(cached)
                result.cache_hits += 1
                continue

        if cache_key not in pending_indexes:
            pending_indexes[cache_key] = []
            pending.append((query, cache_key, osv_ecosystem))
        pending_indexes[cache_key].append(index)

    for chunk in _chunks(pending, MAX_QUERIES_PER_REQUEST):
        payload = {
            "queries": [
                {
                    "package": {"name": query.name, "ecosystem": osv_ecosystem},
                    "version": query.version,
                }
                for query, _cache_key, osv_ecosystem in chunk
            ]
        }
        body = _request_with_retry("post", OSV_QUERYBATCH_URL, http, timeout, result, json=payload)
        if body is None:
            result.failed = True
            continue

        entries = body.get("results")
        if not isinstance(entries, list) or len(entries) != len(chunk):
            result.warnings.append(
                f"OSV returned an unexpected response shape; {len(chunk)} queries were not used"
            )
            result.failed = True
            continue

        result.sent += len(chunk)
        details = _fetch_details(_ids_in(entries), http, timeout, result) if fetch_details else {}

        for (_query, cache_key, _ecosystem), entry in zip(chunk, entries, strict=True):
            vulns = _vulns_for_entry(entry, details)
            for index in pending_indexes[cache_key]:
                result.by_query[index] = list(vulns)
            if use_cache and not any(vuln.id in result.detail_failures for vuln in vulns):
                _cache_put(cache_key, vulns, now)

    return result


def _ids_in(entries: Sequence[Any]) -> list[str]:
    """Advisory ids in a querybatch response, in order, de-duplicated."""
    ids: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for raw in entry.get("vulns") or []:
            if isinstance(raw, dict) and raw.get("id"):
                ids.append(str(raw["id"]))
    return list(dict.fromkeys(ids))


def _fetch_details(
    ids: Sequence[str], http: Any, timeout: float, result: BatchResult
) -> dict[str, OsvVuln]:
    """Load full records for ``ids`` concurrently; failures are warnings."""
    if not ids:
        return {}

    to_fetch = list(ids)
    if len(to_fetch) > MAX_DETAIL_FETCHES:
        result.warnings.append(
            f"{len(to_fetch)} advisories matched but only {MAX_DETAIL_FETCHES} were "
            "loaded in full; the rest are listed with unknown severity"
        )
        to_fetch = to_fetch[:MAX_DETAIL_FETCHES]

    details: dict[str, OsvVuln] = {}

    def load(vuln_id: str) -> None:
        result.detail_requests += 1
        body = _request_with_retry(
            "get",
            OSV_VULN_URL.format(vuln_id=vuln_id),
            http,
            timeout,
            # Each detail failure is reported once, by the caller below.
            BatchResult(by_query=[]),
        )
        if body is None:
            result.detail_failures.append(vuln_id)
            return
        details[vuln_id] = parse_vuln(body)

    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as pool:
        list(pool.map(load, to_fetch))

    if result.detail_failures:
        result.warnings.append(
            f"{len(result.detail_failures)} OSV advisories could not be loaded in full; "
            "their severity is unknown"
        )
    return details


def _vulns_for_entry(entry: Any, details: dict[str, OsvVuln]) -> list[OsvVuln]:
    if not isinstance(entry, dict):
        return []
    raw_vulns = entry.get("vulns") or []
    if not isinstance(raw_vulns, list):
        return []
    vulns: list[OsvVuln] = []
    for raw in raw_vulns:
        if not isinstance(raw, dict):
            continue
        vuln_id = str(raw.get("id") or "")
        if vuln_id in details:
            vulns.append(details[vuln_id])
        elif vuln_id:
            # Discovery succeeded but the detail call did not: keep the finding,
            # with unknown severity, rather than hide it.
            vulns.append(OsvVuln(id=vuln_id))
    return vulns


def parse_vuln(raw: dict[str, Any]) -> OsvVuln:
    """Convert one full OSV JSON record into :class:`OsvVuln`."""
    database_specific = raw.get("database_specific") or {}
    if not isinstance(database_specific, dict):
        database_specific = {}

    vector = None
    for entry in raw.get("severity") or []:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("type", "")).upper().startswith("CVSS_V3"):
            vector = (str(entry.get("score") or "").strip()) or None
            if vector:
                break

    score = cvss_v3_base_score(vector)
    if score is not None:
        severity = severity_band(score)
    else:
        # GitHub advisories carry their band here; there is nothing else to use.
        severity = severity_from_label(database_specific.get("severity"))

    cwe_ids = database_specific.get("cwe_ids") or []
    if not isinstance(cwe_ids, list):
        cwe_ids = []

    fixed: list[str] = []
    for affected in raw.get("affected") or []:
        if not isinstance(affected, dict):
            continue
        for rng in affected.get("ranges") or []:
            if not isinstance(rng, dict):
                continue
            for event in rng.get("events") or []:
                if isinstance(event, dict) and event.get("fixed"):
                    fixed.append(str(event["fixed"]))

    aliases = tuple(str(alias) for alias in raw.get("aliases") or [] if isinstance(alias, str))
    return OsvVuln(
        id=str(raw.get("id") or ""),
        aliases=aliases,
        summary=str(raw.get("summary") or ""),
        details=str(raw.get("details") or ""),
        cvss_vector=vector,
        cvss_score=score,
        severity=severity,
        cwe_ids=tuple(str(cwe) for cwe in cwe_ids),
        fixed_versions=tuple(dict.fromkeys(fixed)),
    )
