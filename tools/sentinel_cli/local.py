"""In-process scanning: no server, no database, no network.

``sentinel scan samples/vulnerable_api.yaml`` uses the same engines the API
uses (parser → OWASP checks → risk scoring), so output matches a real scan.
The backend package is imported lazily and only when local mode is used.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"


def _ensure_backend_importable() -> None:
    backend = str(BACKEND_DIR)
    if backend not in sys.path:
        sys.path.insert(0, backend)


def load_spec(path: Path) -> dict:
    """Load a JSON or YAML OpenAPI document."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover - PyYAML is a backend dependency
            raise RuntimeError("PyYAML is required to scan YAML specs: pip install pyyaml") from exc
        spec = yaml.safe_load(text)
    else:
        spec = json.loads(text)

    if not isinstance(spec, dict):
        raise ValueError(f"{path}: not a JSON/YAML object")
    return spec


def scan_spec(spec: dict) -> dict:
    """Run the real OWASP scan pipeline over an already-parsed spec."""
    _ensure_backend_importable()

    from app.core.risk_engine.scorer import calculate_risk_score
    from app.core.security_engine.parser import parse_openapi_spec
    from app.core.security_engine.scanner import run_owasp_scan

    parsed = parse_openapi_spec(spec)
    findings = run_owasp_scan(parsed)
    risk = calculate_risk_score(findings)

    return {
        "api_title": parsed.get("title"),
        "api_version": parsed.get("version"),
        "total_endpoints": parsed.get("total_endpoints", 0),
        "findings": findings,
        "risk": risk,
    }


def scan_file(path: Path) -> dict:
    result = scan_spec(load_spec(path))
    result["source"] = str(path)
    return result


def to_sarif(results: list[dict], version: str = "1.0.0") -> dict:
    """Serialize findings as SARIF 2.1.0 for GitHub code scanning."""
    rules: dict[str, dict] = {}
    sarif_results: list[dict] = []

    for result in results:
        for finding in result["findings"]:
            rule_id = finding.get("vulnerability_name", "unknown").replace(" ", "-").lower()
            if rule_id not in rules:
                rules[rule_id] = {
                    "id": rule_id,
                    "name": finding.get("vulnerability_name", "Finding"),
                    "shortDescription": {"text": finding.get("vulnerability_name", "Finding")},
                    "fullDescription": {"text": finding.get("description", "")},
                    "help": {
                        "text": finding.get("remediation", ""),
                        "markdown": finding.get("remediation", ""),
                    },
                    "properties": {
                        "tags": [
                            finding.get("owasp_category", ""),
                            finding.get("cwe_id", ""),
                        ]
                    },
                    "defaultConfiguration": {
                        "level": _sarif_level(finding.get("severity", "Info")),
                    },
                }
            sarif_results.append(
                {
                    "ruleId": rule_id,
                    "level": _sarif_level(finding.get("severity", "Info")),
                    "message": {"text": finding.get("evidence") or finding.get("description", "")},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": result.get("source", "spec")},
                                "region": {"startLine": 1},
                            }
                        }
                    ],
                    "properties": {
                        "severity": finding.get("severity"),
                        "confidence": finding.get("confidence"),
                        "cvss_score": finding.get("cvss_score"),
                        "cvss_vector": finding.get("cvss_vector"),
                        "endpoint": finding.get("affected_endpoint"),
                        "method": finding.get("affected_method"),
                    },
                }
            )

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "SentinelAI",
                        "informationUri": "https://github.com/your-org/sentinelai",
                        "version": version,
                        "rules": list(rules.values()),
                    }
                },
                "results": sarif_results,
            }
        ],
    }


def _sarif_level(severity: str) -> str:
    return {
        "critical": "error",
        "high": "error",
        "medium": "warning",
        "low": "note",
        "info": "note",
    }.get(str(severity).lower(), "warning")


def to_markdown(results: list[dict]) -> str:
    """Human-readable Markdown report for PR comments or CI artifacts."""
    lines: list[str] = ["# SentinelAI scan report", ""]
    for result in results:
        risk = result["risk"]
        lines += [
            f"## {result.get('api_title') or result.get('source', 'API')}",
            "",
            f"- **Source:** `{result.get('source', 'n/a')}`",
            f"- **Version:** {result.get('api_version') or 'unversioned'}",
            f"- **Endpoints:** {result.get('total_endpoints', 0)}",
            f"- **Risk score:** {risk['score']}/100 ({risk['level']})",
            f"- **Findings:** {risk['total_vulnerabilities']} "
            f"(critical {risk['critical_count']}, high {risk['high_count']}, "
            f"medium {risk['medium_count']}, low {risk['low_count']})",
            "",
        ]
        if not result["findings"]:
            lines += ["No findings. 🎉", ""]
            continue

        lines += [
            "| Severity | Finding | OWASP | Endpoint | CVSS |",
            "|----------|---------|-------|----------|------|",
        ]
        ordered = sorted(
            result["findings"],
            key=lambda f: _severity_rank(f.get("severity", "Info")),
        )
        for finding in ordered:
            endpoint = finding.get("affected_endpoint") or "—"
            method = finding.get("affected_method")
            if method:
                endpoint = f"`{method} {endpoint}`"
            lines.append(
                f"| {finding.get('severity', 'Info')} "
                f"| {finding.get('vulnerability_name', 'Finding')} "
                f"| {finding.get('owasp_category', '—')} "
                f"| {endpoint} "
                f"| {finding.get('cvss_score', '—')} |"
            )
        lines.append("")
    return "\n".join(lines)


def _severity_rank(value: str) -> int:
    return {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}.get(value, 5)
