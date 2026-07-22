"""SAST (Static Application Security Testing) scanner.

Scans source code files against security rules to detect vulnerabilities.
Supports Python, JavaScript, and Java.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional

from .rules import (
    ALL_RULES,
    EXTENSION_LANGUAGE_MAP,
    Language,
    SecurityRule,
    Severity,
    get_rules_for_file,
)

# Directories and files to skip during scanning
SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", ".venv", "venv", "env",
    "dist", "build", ".next", "target", "vendor", "eggs", "*.egg-info",
    ".tox", ".mypy_cache", ".pytest_cache", "coverage",
}

SKIP_FILES = {
    "package-lock.json", "yarn.lock", "poetry.lock", "Gemfile.lock",
    ".min.js", ".min.css", ".bundle.js",
}

# Maximum file size to scan (500KB)
MAX_FILE_SIZE = 500 * 1024


@dataclass
class SASTFinding:
    """A single SAST finding."""
    rule_id: str
    rule_name: str
    severity: str
    cwe_id: str
    owasp_category: Optional[str]
    language: str
    file_path: str
    line_number: int
    line_content: str
    description: str
    remediation: str
    confidence: float
    tags: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "cwe_id": self.cwe_id,
            "owasp_category": self.owasp_category,
            "language": self.language,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "line_content": self.line_content.strip(),
            "description": self.description,
            "remediation": self.remediation,
            "confidence": self.confidence,
            "tags": self.tags,
        }


@dataclass
class SASTScanResult:
    """Aggregated result of a SAST scan."""
    target_path: str
    total_files_scanned: int
    total_lines_scanned: int
    findings: list[SASTFinding] = field(default_factory=list)
    files_with_findings: int = 0
    languages_detected: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def summary(self) -> dict:
        severity_counts = {}
        for f in self.findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
        return {
            "total_findings": len(self.findings),
            "severity_counts": severity_counts,
            "files_scanned": self.total_files_scanned,
            "lines_scanned": self.total_lines_scanned,
            "files_with_findings": self.files_with_findings,
            "languages_detected": self.languages_detected,
        }

    def to_dict(self) -> dict:
        return {
            "target_path": self.target_path,
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
            "errors": self.errors,
        }


def _is_skip_path(path: str) -> bool:
    """Check if a path should be skipped."""
    parts = path.replace("\\", "/").split("/")
    for part in parts:
        if part in SKIP_DIRS or part.startswith("*"):
            return True
    basename = os.path.basename(path)
    for skip in SKIP_FILES:
        if skip in basename:
            return True
    return False


def _scan_file(filepath: str, rules: list[SecurityRule]) -> list[SASTFinding]:
    """Scan a single file against security rules."""
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return findings

    for line_idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("//"):
            continue

        for rule in rules:
            try:
                if re.search(rule.pattern, stripped):
                    findings.append(SASTFinding(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        severity=rule.severity.value,
                        cwe_id=rule.cwe_id,
                        owasp_category=rule.owasp_category,
                        language=rule.language.value,
                        file_path=filepath,
                        line_number=line_idx,
                        line_content=stripped,
                        description=rule.description,
                        remediation=rule.remediation,
                        confidence=rule.confidence,
                        tags=rule.tags,
                    ))
            except re.error:
                continue

    return findings


def _collect_files(target_path: str) -> list[str]:
    """Collect all scannable source files from a path."""
    files = []
    if os.path.isfile(target_path):
        ext = os.path.splitext(target_path)[1].lower()
        if ext in EXTENSION_LANGUAGE_MAP:
            files.append(target_path)
        return files

    for root, dirs, filenames in os.walk(target_path):
        # Filter out skipped directories in-place
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in EXTENSION_LANGUAGE_MAP:
                continue
            filepath = os.path.join(root, filename)
            if _is_skip_path(filepath):
                continue
            try:
                size = os.path.getsize(filepath)
                if size > MAX_FILE_SIZE:
                    continue
                files.append(filepath)
            except OSError:
                continue

    return files


def run_sast_scan(target_path: str) -> SASTScanResult:
    """Run SAST scan on a file or directory.

    Args:
        target_path: Path to a source file or directory to scan.

    Returns:
        SASTScanResult with all findings, summary, and metadata.
    """
    if not os.path.exists(target_path):
        return SASTScanResult(
            target_path=target_path,
            total_files_scanned=0,
            total_lines_scanned=0,
            errors=[f"Path not found: {target_path}"],
        )

    files = _collect_files(target_path)
    result = SASTScanResult(
        target_path=target_path,
        total_files_scanned=len(files),
        total_lines_scanned=0,
    )

    if not files:
        return result

    # Detect languages present
    languages_seen = set()
    all_findings = []
    files_with_findings = set()
    total_lines = 0

    for filepath in files:
        rules = get_rules_for_file(filepath)
        if not rules:
            continue

        ext = os.path.splitext(filepath)[1].lower()
        lang = EXTENSION_LANGUAGE_MAP.get(ext)
        if lang:
            languages_seen.add(lang.value)

        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                line_count = sum(1 for _ in f)
            total_lines += line_count
        except OSError:
            continue

        findings = _scan_file(filepath, rules)
        if findings:
            files_with_findings.add(filepath)
        all_findings.extend(findings)

    # Sort by severity (Critical first), then file path, then line number
    severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
    all_findings.sort(key=lambda f: (
        severity_order.get(f.severity, 5),
        f.file_path,
        f.line_number,
    ))

    result.findings = all_findings
    result.total_lines_scanned = total_lines
    result.files_with_findings = len(files_with_findings)
    result.languages_detected = sorted(languages_seen)

    return result
