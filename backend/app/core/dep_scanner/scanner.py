"""Dependency security scanner.

Parses requirements.txt (Python), package.json (JavaScript), and pom.xml (Java)
to detect known vulnerabilities, outdated packages, and security risks.
"""

import json
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

from .osv_client import (
    DEFAULT_TIMEOUT_SECONDS,
    OsvVuln,
    Query,
    query_batch,
)
from .vulnerability_db import (
    JAVA_VULNERABILITIES,
    JAVASCRIPT_VULNERABILITIES,
    PYTHON_VULNERABILITIES,
)


def _parse_version(version_str: str) -> tuple:
    """Parse a version string into a comparable tuple."""
    cleaned = re.sub(r"[^0-9.]", "", version_str.strip())
    parts = []
    for p in cleaned.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts) if parts else (0,)


def _is_version_affected(installed: str, vulnerable_range: str) -> bool:
    """Check if installed version falls within vulnerable range.

    Supports: >=X, <=X, ==X, ~=X, ==X.Y.Z, and exact matches.
    This is a simplified check covering common cases.
    """
    installed_clean = re.sub(r"[^0-9.]", "", installed.strip())
    installed_ver = _parse_version(installed_clean)

    if not vulnerable_range or vulnerable_range.strip() == "*":
        return True

    vulnerable_ver = _parse_version(vulnerable_range)
    return installed_ver < vulnerable_ver


@dataclass
class DependencyInfo:
    """Information about a single dependency."""

    name: str
    version: str
    ecosystem: str
    file_path: str
    is_dev: bool = False


@dataclass
class DepFinding:
    """A dependency security finding."""

    package: str
    installed_version: str
    severity: str
    cvss_score: float
    cve_id: str
    cwe_id: str
    description: str
    fixed_in: str
    ecosystem: str
    file_path: str
    url: str = ""
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "package": self.package,
            "installed_version": self.installed_version,
            "severity": self.severity,
            "cvss_score": self.cvss_score,
            "cve_id": self.cve_id,
            "cwe_id": self.cwe_id,
            "description": self.description,
            "fixed_in": self.fixed_in,
            "ecosystem": self.ecosystem,
            "file_path": self.file_path,
            "url": self.url,
            "confidence": self.confidence,
        }


@dataclass
class DepScanResult:
    """Aggregated result of a dependency scan."""

    target_path: str
    total_dependencies: int = 0
    total_files_scanned: int = 0
    findings: list[DepFinding] = field(default_factory=list)
    dependencies: list[DependencyInfo] = field(default_factory=list)
    ecosystems_detected: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    #: Non-fatal problems from the live OSV lookup, safe to show the user.
    osv_warnings: list[str] = field(default_factory=list)
    #: curated_only / osv_only / overlap / skipped_queries for this scan.
    merge_counts: dict[str, int] = field(default_factory=dict)

    @property
    def summary(self) -> dict:
        severity_counts: dict[str, int] = {}
        for f in self.findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
        return {
            "total_dependencies": self.total_dependencies,
            "total_vulnerabilities": len(self.findings),
            "severity_counts": severity_counts,
            "files_scanned": self.total_files_scanned,
            "ecosystems_detected": self.ecosystems_detected,
            "merge_counts": self.merge_counts,
        }

    def to_dict(self) -> dict:
        return {
            "target_path": self.target_path,
            "summary": self.summary,
            "osv_warnings": self.osv_warnings,
            "merge_counts": self.merge_counts,
            "findings": [f.to_dict() for f in self.findings],
            "dependencies": [
                {
                    "name": d.name,
                    "version": d.version,
                    "ecosystem": d.ecosystem,
                    "file": d.file_path,
                    "is_dev": d.is_dev,
                }
                for d in self.dependencies
            ],
            "errors": self.errors,
        }


def _parse_requirements_txt(filepath: str) -> list[DependencyInfo]:
    """Parse a Python requirements.txt file."""
    deps = []
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue

                # Handle ==, >=, ~=, etc.
                match = re.match(
                    r"^([a-zA-Z0-9_][a-zA-Z0-9._-]*)\s*([=~><!]+)\s*([0-9][a-zA-Z0-9.*-]*)", line
                )
                if match:
                    name = match.group(1).strip().lower()
                    version = match.group(3).strip()
                    deps.append(
                        DependencyInfo(
                            name=name,
                            version=version,
                            ecosystem="python",
                            file_path=filepath,
                        )
                    )
                    continue

                # Simple name without version
                match = re.match(r"^([a-zA-Z0-9_][a-zA-Z0-9._-]*)", line)
                if match:
                    name = match.group(1).strip().lower()
                    deps.append(
                        DependencyInfo(
                            name=name,
                            version="unknown",
                            ecosystem="python",
                            file_path=filepath,
                        )
                    )
    except (OSError, UnicodeDecodeError):
        pass
    return deps


def _parse_package_json(filepath: str) -> list[DependencyInfo]:
    """Parse a JavaScript package.json file."""
    deps = []
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            data = json.load(f)

        dep_sections = [
            ("dependencies", False),
            ("devDependencies", True),
            ("peerDependencies", False),
            ("optionalDependencies", False),
        ]

        for section, is_dev in dep_sections:
            packages = data.get(section, {})
            for name, version_spec in packages.items():
                # Strip ^, ~, >=, etc. to get base version
                version = re.sub(r"[^0-9.]", "", str(version_spec))
                if not version:
                    version = version_spec
                deps.append(
                    DependencyInfo(
                        name=name.lower(),
                        version=version,
                        ecosystem="javascript",
                        file_path=filepath,
                        is_dev=is_dev,
                    )
                )
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        pass
    return deps


def _parse_pom_xml(filepath: str) -> list[DependencyInfo]:
    """Parse a Java pom.xml file."""
    deps = []
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()

        # Handle Maven namespace
        ns = ""
        ns_match = re.match(r"\{(.*)\}", root.tag)
        if ns_match:
            ns = ns_match.group(1)

        nsmap = {"m": ns} if ns else {}

        def find(element, path):
            if ns:
                path = path.replace("/", "/m:")
                return element.find(path, nsmap)
            return element.find(path)

        def findall(element, path):
            if ns:
                path = path.replace("/", "/m:")
                return element.findall(path, nsmap)
            return element.findall(path)

        dependencies = find(root, "dependencies")
        if dependencies is not None:
            for dep in findall(dependencies, "dependency"):
                group_id = find(dep, "groupId")
                artifact_id = find(dep, "artifactId")
                version = find(dep, "version")

                name = ""
                if artifact_id is not None and artifact_id.text:
                    name = artifact_id.text.strip()

                if group_id is not None and group_id.text:
                    name = f"{group_id.text.strip()}:{name}" if name else group_id.text.strip()

                ver = ""
                if version is not None and version.text:
                    ver = version.text.strip()

                if name:
                    deps.append(
                        DependencyInfo(
                            name=name.lower(),
                            version=ver,
                            ecosystem="java",
                            file_path=filepath,
                        )
                    )

        # Also check parent POM for managed versions
        parent_deps = find(root, "parent/dependencies")
        if parent_deps is not None:
            for dep in findall(parent_deps, "dependency"):
                artifact_id = find(dep, "artifactId")
                version = find(dep, "version")
                if artifact_id is not None and artifact_id.text:
                    name = artifact_id.text.strip().lower()
                    ver = version.text.strip() if version is not None and version.text else ""
                    deps.append(
                        DependencyInfo(
                            name=name,
                            version=ver,
                            ecosystem="java",
                            file_path=filepath,
                        )
                    )

    except (OSError, ET.ParseError):
        pass
    return deps


def _get_vuln_db_for_ecosystem(ecosystem: str) -> dict:
    """Return the vulnerability database for the given ecosystem."""
    mapping = {
        "python": PYTHON_VULNERABILITIES,
        "javascript": JAVASCRIPT_VULNERABILITIES,
        "java": JAVA_VULNERABILITIES,
    }
    return mapping.get(ecosystem, {})


def _check_vulnerabilities(dep: DependencyInfo, vuln_db: dict) -> list[DepFinding]:
    """Check a dependency against the vulnerability database."""
    findings = []

    # Normalize package name for lookup
    pkg_name = dep.name.lower().replace("-", "_").replace(".", "_")

    # Try direct match, then fuzzy match
    matched_vulns = vuln_db.get(pkg_name, [])
    if not matched_vulns:
        # Try with original name (for npm packages that use hyphens)
        original_name = dep.name.lower()
        matched_vulns = vuln_db.get(original_name, [])

    if not matched_vulns and "/" in dep.name:
        # Try removing scope prefix (@org/name -> name)
        short_name = dep.name.split("/")[-1]
        matched_vulns = vuln_db.get(short_name.lower(), [])

    for vuln in matched_vulns:
        is_affected = _is_version_affected(dep.version, vuln.fixed_in)
        if is_affected:
            findings.append(
                DepFinding(
                    package=dep.name,
                    installed_version=dep.version,
                    severity=vuln.severity,
                    cvss_score=vuln.cvss_score,
                    cve_id=vuln.cve_id,
                    cwe_id=vuln.cwe_id,
                    description=vuln.description,
                    fixed_in=vuln.fixed_in,
                    ecosystem=dep.ecosystem,
                    file_path=dep.file_path,
                    url=vuln.url,
                    confidence=0.95,
                )
            )

    return findings


def _package_key(name: str) -> str:
    """Normalise a package name so PyPI, npm and Maven spellings compare equal."""
    return name.strip().lower().replace("-", "_").replace(".", "_")


def _finding_key(finding: DepFinding) -> tuple[str, str]:
    """Identity of a finding: (package, advisory id).

    The advisory id is the CVE when one exists, so an OSV GHSA advisory that
    aliases CVE-2024-24680 collapses with the curated CVE-2024-24680 entry
    instead of appearing twice for the same package.
    """
    return (_package_key(finding.package), (finding.cve_id or "").strip().upper())


def _osv_finding(dep: DependencyInfo, vuln: OsvVuln) -> DepFinding:
    """Convert one OSV record into the shape the report and normaliser consume."""
    identifier = vuln.identity
    description = vuln.summary or vuln.details or f"{identifier} affects {dep.name} {dep.version}."
    if vuln.details and vuln.summary and vuln.details != vuln.summary:
        description = f"{description}\n\n{vuln.details}"
    if vuln.severity is None:
        # Say so instead of picking a band. The scanner's own severity stays
        # "unknown" through finder, normaliser and report.
        description = (
            f"{description} OSV publishes no severity rating (no CVSS vector, no "
            f"database_specific severity) for {identifier}."
        )

    return DepFinding(
        package=dep.name,
        installed_version=dep.version,
        severity=vuln.severity or "unknown",
        cvss_score=vuln.cvss_score if vuln.cvss_score is not None else 0.0,
        cve_id=identifier,
        cwe_id=vuln.cwe_ids[0] if vuln.cwe_ids else "",
        description=description.strip(),
        fixed_in=vuln.fixed_versions[0] if vuln.fixed_versions else "",
        ecosystem=dep.ecosystem,
        file_path=dep.file_path,
        url=vuln.reference_url,
        confidence=0.9,
    )


def _osv_enabled() -> bool:
    """Global default for live lookups; tests disable it through the env."""
    try:
        from app.config import get_settings
    except ImportError:  # scanner used standalone
        return True
    return bool(get_settings().OSV_ENABLED)


def _lookup_osv(
    dependencies: list[DependencyInfo], client: Any, timeout: float
) -> tuple[list[DepFinding], list[str], dict[str, int]]:
    """Query OSV for every dependency and convert what comes back."""
    queries = [
        Query(name=dep.name, version=dep.version, ecosystem=dep.ecosystem) for dep in dependencies
    ]
    batch = query_batch(queries, timeout=timeout, client=client)

    findings: list[DepFinding] = []
    for dep, vulns in zip(dependencies, batch.by_query, strict=True):
        for vuln in vulns:
            findings.append(_osv_finding(dep, vuln))

    counts = {"skipped_queries": batch.skipped_queries}
    reasons = batch.skip_reasons()
    if reasons:
        counts.update({f"skipped_{reason.replace(' ', '_')}": n for reason, n in reasons.items()})
    return findings, list(batch.warnings), counts


def _merge_findings(
    curated: list[DepFinding], live: list[DepFinding]
) -> tuple[list[DepFinding], dict[str, int]]:
    """Merge curated and live findings, curated winning on conflict.

    Also collapses duplicates inside each side (the same manifest scanned twice,
    or two manifests pinning the same package) so one advisory is one finding.
    """
    curated_by_key: dict[tuple[str, str], DepFinding] = {}
    for finding in curated:
        curated_by_key.setdefault(_finding_key(finding), finding)

    live_by_key: dict[tuple[str, str], DepFinding] = {}
    for finding in live:
        live_by_key.setdefault(_finding_key(finding), finding)

    overlap = curated_by_key.keys() & live_by_key.keys()
    live_only = [key for key in live_by_key if key not in curated_by_key]
    curated_only = [key for key in curated_by_key if key not in live_by_key]

    merged = list(curated_by_key.values()) + [live_by_key[key] for key in live_only]
    counts = {
        "curated_only": len(curated_only),
        "osv_only": len(live_only),
        "overlap": len(overlap),
    }
    return merged, counts


def _sort_findings(findings: list[DepFinding]) -> list[DepFinding]:
    """Stable order so two runs over the same input produce the same report."""
    severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
    return sorted(
        findings,
        key=lambda f: (
            severity_order.get(f.severity, 5),
            _package_key(f.package),
            f.installed_version,
            (f.cve_id or "").upper(),
            f.file_path,
        ),
    )


def _collect_dep_files(target_path: str) -> list[str]:
    """Collect dependency manifest files from the target path."""
    files = []
    dep_filenames = {
        "requirements.txt",
        "requirements.in",
        "Pipfile",
        "package.json",
        "pom.xml",
    }

    if os.path.isfile(target_path):
        basename = os.path.basename(target_path)
        if basename in dep_filenames or basename.endswith(".xml") or basename.endswith(".txt"):
            files.append(target_path)
        return files

    skip_dirs = {
        "node_modules",
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "dist",
        "build",
        "target",
        ".next",
        "vendor",
    }

    for root, dirs, filenames in os.walk(target_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        for filename in filenames:
            if filename in dep_filenames:
                files.append(os.path.join(root, filename))

    return files


def run_dep_scan(
    target_path: str,
    *,
    osv_client: Any = None,
    use_osv: bool | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> DepScanResult:
    """Run dependency security scan on a file or directory.

    Two sources feed the findings: the curated table in ``vulnerability_db``
    (always, offline) and OSV.dev (when enabled). Curated entries win on conflict;
    OSV contributes advisories the table does not know about. If OSV is
    unreachable the scan still returns the curated results plus a warning, so an
    upload never fails because a third party is down.

    Args:
        target_path: Path to a file or directory containing dependency manifests.
        osv_client: Injectable HTTP client (anything with ``post``). Tests pass a
            stub; production passes None and the client uses ``requests``.
        use_osv: Force live lookup on or off. Defaults to ``settings.OSV_ENABLED``.
        timeout: Per-request timeout for the OSV calls.

    Returns:
        DepScanResult with findings, dependency list, and metadata.
    """
    if not os.path.exists(target_path):
        return DepScanResult(
            target_path=target_path,
            errors=[f"Path not found: {target_path}"],
        )

    files = _collect_dep_files(target_path)
    result = DepScanResult(
        target_path=target_path,
        total_files_scanned=len(files),
    )

    if not files:
        return result

    ecosystems_seen = set()
    all_deps = []
    all_findings = []

    for filepath in files:
        basename = os.path.basename(filepath).lower()
        deps = []

        if basename in ("requirements.txt", "requirements.in"):
            deps = _parse_requirements_txt(filepath)
        elif basename == "package.json":
            deps = _parse_package_json(filepath)
        elif basename == "pom.xml":
            deps = _parse_pom_xml(filepath)
        else:
            # Single file with unknown name: try all parsers by extension
            if filepath.lower().endswith(".txt"):
                deps = _parse_requirements_txt(filepath)
            elif filepath.lower().endswith(".json"):
                deps = _parse_package_json(filepath)
            elif filepath.lower().endswith(".xml"):
                deps = _parse_pom_xml(filepath)

        if deps:
            all_deps.extend(deps)
            ecosystem = deps[0].ecosystem
            ecosystems_seen.add(ecosystem)

            # Check each dependency against vulnerability database
            vuln_db = _get_vuln_db_for_ecosystem(ecosystem)
            for dep in deps:
                findings = _check_vulnerabilities(dep, vuln_db)
                all_findings.extend(findings)

    live_enabled = _osv_enabled() if use_osv is None else use_osv
    if live_enabled and all_deps:
        live_findings, warnings, lookup_counts = _lookup_osv(all_deps, osv_client, timeout)
        all_findings, merge_counts = _merge_findings(all_findings, live_findings)
        merge_counts.update(lookup_counts)
        result.osv_warnings = warnings
        result.merge_counts = merge_counts
        result.errors.extend(f"OSV: {warning}" for warning in warnings)
    else:
        all_findings, merge_counts = _merge_findings(all_findings, [])
        result.merge_counts = merge_counts
        if not live_enabled:
            result.merge_counts["osv_disabled"] = 1

    result.dependencies = all_deps
    result.total_dependencies = len(all_deps)
    result.findings = _sort_findings(all_findings)
    result.ecosystems_detected = sorted(ecosystems_seen)

    return result
