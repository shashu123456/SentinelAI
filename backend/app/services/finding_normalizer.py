"""Normalise dependency and SAST findings into the persistence shape.

The three engines speak different dialects:

* the OpenAPI scanner already emits persistence-ready dicts;
* the dependency scanner emits ``DepFinding`` (``package``, ``cve_id``,
  ``fixed_in``, ``confidence`` as a 0-1 float, no ``impact``);
* the SAST engine emits ``SASTFinding`` (``rule_id``, ``line_number``,
  ``confidence`` as a 0-1 float, no ``impact``).

``FindingRepository.from_scan_data`` requires ``vulnerability_name``,
``owasp_category``, ``severity``, ``description``, ``impact`` and
``remediation`` — a missing one raises ``KeyError`` and the scan dies with
HTTP 500 (the A7 regression). Every function here therefore guarantees those
keys are present and non-empty, and maps severity onto the vocabulary the
``ck_findings_severity`` constraint allows:
Critical, High, Medium, Low, Info.

Everything in this module is pure: no I/O, no DB, no network.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

ALLOWED_SEVERITIES = ("Critical", "High", "Medium", "Low", "Info")

# Longest allowed value for Finding.vulnerability_name (String(200)).
MAX_NAME_LENGTH = 200
# Longest allowed value for Finding.owasp_category (String(50)).
MAX_OWASP_LENGTH = 50

_SEVERITY_ALIASES = {
    "critical": "Critical",
    "crit": "Critical",
    "high": "High",
    "important": "High",
    "moderate": "Medium",
    "medium": "Medium",
    "med": "Medium",
    "low": "Low",
    "minor": "Low",
    "info": "Info",
    "informational": "Info",
    "none": "Info",
    "unknown": "Info",
}

# Used when an engine reports a vulnerability without an OWASP API category.
_DEFAULT_OWASP_DEPS = "A06:2021 Vulnerable and Outdated Components"
_DEFAULT_OWASP_SAST = "Unmapped (SAST)"


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read ``key`` from a mapping or an object, so both work as input."""
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _text(value: Any, fallback: str) -> str:
    """Coerce to a non-empty string; required fields may never be None."""
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _clip(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def normalize_severity(value: Any) -> str:
    """Map any engine's severity onto Critical/High/Medium/Low/Info.

    An unrecognised value becomes ``Medium``: under-reporting an unknown
    severity as ``Info`` would hide real findings.
    """
    if value is None:
        return "Medium"
    raw = str(getattr(value, "value", value)).strip().lower()
    return _SEVERITY_ALIASES.get(raw, "Medium")


def normalize_confidence(value: Any, default: int = 85) -> int:
    """Return a 0-100 integer.

    The dependency and SAST engines report 0-1 floats; the database column is an
    integer percentage.
    """
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number <= 1.0:
        number *= 100.0
    return max(0, min(100, int(round(number))))


def _cvss(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_dep(
    dep_finding: Any,
    package_name: str | None = None,
    package_version: str | None = None,
) -> dict:
    """Normalise a dependency-scanner finding into the persistence shape.

    Args:
        dep_finding: ``DepFinding`` instance or its ``to_dict()`` output.
        package_name: overrides the package name (defaults to the finding's).
        package_version: overrides the version (defaults to the finding's).
    """
    name = _text(package_name or _get(dep_finding, "package"), "unknown-package")
    version = _text(package_version or _get(dep_finding, "installed_version"), "unknown-version")
    cve = _text(_get(dep_finding, "cve_id"), "")
    fixed_in = _text(_get(dep_finding, "fixed_in"), "")
    ecosystem = _text(_get(dep_finding, "ecosystem"), "")
    file_path = _text(_get(dep_finding, "file_path"), "")

    identifier = cve or "vulnerable-dependency"
    vulnerability_name = _clip(f"{name} {version}: {identifier}", MAX_NAME_LENGTH)

    description = _text(
        _get(dep_finding, "description"),
        f"{name} {version} is affected by {identifier}.",
    )
    impact = _text(
        _get(dep_finding, "impact"),
        f"An application deploying {name} {version} inherits the weakness "
        f"described by {identifier}"
        + (f" in the {ecosystem} ecosystem" if ecosystem else "")
        + ".",
    )
    remediation = _text(
        _get(dep_finding, "remediation"),
        (
            f"Upgrade {name} to {fixed_in} or later."
            if fixed_in
            else f"Upgrade {name} to a release that is not affected by {identifier}."
        ),
    )

    # The API schema exposes references as a list, so build a list of strings.
    references: list[str] = [f"package:{name}@{version}"]
    url = _text(_get(dep_finding, "url"), "")
    if url:
        references.append(url)
    if cve:
        references.append(cve)
    if fixed_in:
        references.append(f"fixed_in:{fixed_in}")

    return {
        "source": "deps",
        "vulnerability_name": vulnerability_name,
        "owasp_category": _clip(
            _text(_get(dep_finding, "owasp_category"), _DEFAULT_OWASP_DEPS),
            MAX_OWASP_LENGTH,
        ),
        "cwe_id": _get(dep_finding, "cwe_id") or None,
        "severity": normalize_severity(_get(dep_finding, "severity")),
        "confidence": normalize_confidence(_get(dep_finding, "confidence")),
        "description": description,
        "evidence": _text(_get(dep_finding, "evidence"), file_path)
        or f"{file_path}: {name}=={version}",
        "impact": impact,
        "remediation": remediation,
        "references": references,
        "cvss_score": _cvss(_get(dep_finding, "cvss_score")),
        "affected_endpoint": _clip(f"{name}=={version}", 500),
        "detection_reason": _text(
            _get(dep_finding, "detection_reason"),
            f"Known {identifier} in a pinned dependency",
        ),
        # Dedupe identity, not a column.
        "_dedupe": ("deps", name.lower(), identifier.lower(), 0),
    }


def normalize_sast(sast_finding: Any) -> dict:
    """Normalise a SAST finding into the persistence shape."""
    rule_id = _text(_get(sast_finding, "rule_id"), "sast-rule")
    rule_name = _text(_get(sast_finding, "rule_name"), rule_id)
    file_path = _text(_get(sast_finding, "file_path"), "unknown-file")
    line_number = _get(sast_finding, "line_number")
    try:
        line = int(line_number) if line_number is not None else 0
    except (TypeError, ValueError):
        line = 0
    line_content = _text(_get(sast_finding, "line_content"), "")
    language = _text(_get(sast_finding, "language"), "")

    description = _text(
        _get(sast_finding, "description"),
        f"{rule_name} detected in {file_path}.",
    )
    impact = _text(
        _get(sast_finding, "impact"),
        f"Source reaching this point may be attacker-controlled, so the weakness "
        f"described by {rule_name} can be triggered from the network surface.",
    )
    remediation = _text(
        _get(sast_finding, "remediation"),
        "Review the flagged line and apply the rule's recommended secure pattern.",
    )

    location = f"{file_path}:{line}" if line else file_path
    references: list[str] = [f"rule:{rule_id}"]
    tags = _get(sast_finding, "tags")
    if tags:
        references.extend(str(tag) for tag in tags)

    return {
        "source": "code",
        "vulnerability_name": _clip(rule_name, MAX_NAME_LENGTH),
        "owasp_category": _clip(
            _text(_get(sast_finding, "owasp_category"), _DEFAULT_OWASP_SAST),
            MAX_OWASP_LENGTH,
        ),
        "cwe_id": _get(sast_finding, "cwe_id") or None,
        "severity": normalize_severity(_get(sast_finding, "severity")),
        "confidence": normalize_confidence(_get(sast_finding, "confidence")),
        "description": description,
        "evidence": f"{location}: {line_content}" if line_content else location,
        "impact": impact,
        "remediation": remediation,
        "references": references,
        "affected_endpoint": _clip(location, 500),
        "detection_reason": _text(
            _get(sast_finding, "detection_reason"),
            f"Static rule {rule_id} matched" + (f" ({language})" if language else ""),
        ),
        "_dedupe": ("code", file_path.lower(), rule_id.lower(), line),
    }


def dedupe_key(finding: Mapping[str, Any]) -> tuple:
    """Return the dedupe identity of a normalized finding.

    ``(source, package_or_file, rule_id, line)``: for dependencies the "rule id"
    is the CVE (or ``vulnerable-dependency``) and the line is always 0; for SAST
    it is the rule id and the line number.
    """
    key = finding.get("_dedupe") if isinstance(finding, Mapping) else None
    if key:
        return tuple(key)
    return (
        str(finding.get("source", "spec")),
        str(finding.get("affected_endpoint") or "").lower(),
        str(finding.get("cwe_id") or finding.get("vulnerability_name") or "").lower(),
        0,
    )


def strip_internal(finding: dict) -> dict:
    """Drop the ``_``-prefixed helper keys before the dict reaches storage."""
    return {k: v for k, v in finding.items() if not k.startswith("_")}


def dedupe_findings(findings: list[dict]) -> list[dict]:
    """Drop duplicate findings, keeping first occurrence order."""
    seen: set[tuple] = set()
    unique: list[dict] = []
    for finding in findings:
        key = dedupe_key(finding)
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique
