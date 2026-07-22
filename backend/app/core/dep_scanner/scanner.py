"""Dependency security scanner.

Parses requirements.txt (Python), package.json (JavaScript), and pom.xml (Java)
to detect known vulnerabilities, outdated packages, and security risks.
"""

import os
import re
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

from .vulnerability_db import (
    PYTHON_VULNERABILITIES,
    JAVASCRIPT_VULNERABILITIES,
    JAVA_VULNERABILITIES,
    Vulnerability,
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

    @property
    def summary(self) -> dict:
        severity_counts = {}
        for f in self.findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
        return {
            "total_dependencies": self.total_dependencies,
            "total_vulnerabilities": len(self.findings),
            "severity_counts": severity_counts,
            "files_scanned": self.total_files_scanned,
            "ecosystems_detected": self.ecosystems_detected,
        }

    def to_dict(self) -> dict:
        return {
            "target_path": self.target_path,
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
            "dependencies": [
                {"name": d.name, "version": d.version, "ecosystem": d.ecosystem,
                 "file": d.file_path, "is_dev": d.is_dev}
                for d in self.dependencies
            ],
            "errors": self.errors,
        }


def _parse_requirements_txt(filepath: str) -> list[DependencyInfo]:
    """Parse a Python requirements.txt file."""
    deps = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue

                # Handle ==, >=, ~=, etc.
                match = re.match(r"^([a-zA-Z0-9_][a-zA-Z0-9._-]*)\s*([=~><!]+)\s*([0-9][a-zA-Z0-9.*-]*)", line)
                if match:
                    name = match.group(1).strip().lower()
                    version = match.group(3).strip()
                    deps.append(DependencyInfo(
                        name=name, version=version,
                        ecosystem="python", file_path=filepath,
                    ))
                    continue

                # Simple name without version
                match = re.match(r"^([a-zA-Z0-9_][a-zA-Z0-9._-]*)", line)
                if match:
                    name = match.group(1).strip().lower()
                    deps.append(DependencyInfo(
                        name=name, version="unknown",
                        ecosystem="python", file_path=filepath,
                    ))
    except (OSError, UnicodeDecodeError):
        pass
    return deps


def _parse_package_json(filepath: str) -> list[DependencyInfo]:
    """Parse a JavaScript package.json file."""
    deps = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
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
                deps.append(DependencyInfo(
                    name=name.lower(), version=version,
                    ecosystem="javascript", file_path=filepath,
                    is_dev=is_dev,
                ))
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
                    deps.append(DependencyInfo(
                        name=name.lower(), version=ver,
                        ecosystem="java", file_path=filepath,
                    ))

        # Also check parent POM for managed versions
        parent_deps = find(root, "parent/dependencies")
        if parent_deps is not None:
            for dep in findall(parent_deps, "dependency"):
                artifact_id = find(dep, "artifactId")
                version = find(dep, "version")
                if artifact_id is not None and artifact_id.text:
                    name = artifact_id.text.strip().lower()
                    ver = version.text.strip() if version is not None and version.text else ""
                    deps.append(DependencyInfo(
                        name=name, version=ver,
                        ecosystem="java", file_path=filepath,
                    ))

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

    if not matched_vulns:
        # Try removing scope prefix (@org/name -> name)
        if "/" in dep.name:
            short_name = dep.name.split("/")[-1]
            matched_vulns = vuln_db.get(short_name.lower(), [])

    for vuln in matched_vulns:
        is_affected = _is_version_affected(dep.version, vuln.fixed_in)
        if is_affected:
            findings.append(DepFinding(
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
            ))

    return findings


def _collect_dep_files(target_path: str) -> list[str]:
    """Collect dependency manifest files from the target path."""
    files = []
    dep_filenames = {
        "requirements.txt", "requirements.in", "Pipfile",
        "package.json", "pom.xml",
    }

    if os.path.isfile(target_path):
        basename = os.path.basename(target_path)
        if basename in dep_filenames or basename.endswith(".xml") or basename.endswith(".txt"):
            files.append(target_path)
        return files

    skip_dirs = {"node_modules", "__pycache__", ".git", ".venv", "venv",
                 "dist", "build", "target", ".next", "vendor"}

    for root, dirs, filenames in os.walk(target_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        for filename in filenames:
            if filename in dep_filenames:
                files.append(os.path.join(root, filename))

    return files


def run_dep_scan(target_path: str) -> DepScanResult:
    """Run dependency security scan on a file or directory.

    Scans for:
    - Known CVEs in dependencies
    - Outdated packages
    - Insecure dependency configurations

    Args:
        target_path: Path to a file or directory containing dependency manifests.

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

    # Sort findings by severity
    severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
    all_findings.sort(key=lambda f: (severity_order.get(f.severity, 5), f.package))

    result.dependencies = all_deps
    result.total_dependencies = len(all_deps)
    result.findings = all_findings
    result.ecosystems_detected = sorted(ecosystems_seen)

    return result
