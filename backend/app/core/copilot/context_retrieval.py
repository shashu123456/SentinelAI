"""Context retrieval layer for the security copilot agent.

Builds rich security context from the database that the agent uses
to ground all responses in actual scan data.
"""

from sqlalchemy.orm import Session
from app.core.copilot.tools import (
    get_latest_scan, get_scan_history, get_critical_findings,
    get_all_findings, get_findings_by_category, get_findings_by_cwe,
    get_ai_analysis, get_risk_summary, compare_scans,
)


class SecurityContext:
    """Represents the full security state for a user at a point in time."""

    def __init__(self, db: Session, user_id: int, scan_id: int = None):
        self.db = db
        self.user_id = user_id
        self.scan_id = scan_id
        self._risk_summary = None
        self._latest_scan = None
        self._findings = None
        self._critical_findings = None
        self._by_category = None
        self._by_cwe = None
        self._ai_analysis = None
        self._history = None

    @property
    def risk_summary(self) -> dict:
        if self._risk_summary is None:
            self._risk_summary = get_risk_summary(self.db, self.user_id)
        return self._risk_summary

    @property
    def latest_scan(self) -> dict | None:
        if self._latest_scan is None:
            self._latest_scan = get_latest_scan(self.db, self.user_id)
        return self._latest_scan

    @property
    def findings(self) -> list[dict]:
        if self._findings is None:
            self._findings = get_all_findings(self.db, self.user_id, self.scan_id)
        return self._findings

    @property
    def critical_findings(self) -> list[dict]:
        if self._critical_findings is None:
            self._critical_findings = get_critical_findings(self.db, self.user_id, self.scan_id)
        return self._critical_findings

    @property
    def by_category(self) -> dict:
        if self._by_category is None:
            self._by_category = get_findings_by_category(self.db, self.user_id)
        return self._by_category

    @property
    def by_cwe(self) -> dict:
        if self._by_cwe is None:
            self._by_cwe = get_findings_by_cwe(self.db, self.user_id)
        return self._by_cwe

    @property
    def ai_analysis(self) -> dict | None:
        if self._ai_analysis is None and self.latest_scan:
            self._ai_analysis = get_ai_analysis(self.db, self.latest_scan["id"])
        return self._ai_analysis

    @property
    def history(self) -> list[dict]:
        if self._history is None:
            self._history = get_scan_history(self.db, self.user_id)
        return self._history

    @property
    def has_data(self) -> bool:
        return self.latest_scan is not None

    def build_system_context(self) -> str:
        """Build a comprehensive context string for the LLM system prompt."""
        parts = []

        parts.append("=== SECURITY ASSESSMENT CONTEXT ===\n")

        risk = self.risk_summary
        if risk["total_scans"] > 0:
            parts.append(f"Overall Risk Score: {risk['risk_score']}/100 ({risk['risk_level']})")
            parts.append(f"Total Scans Performed: {risk['total_scans']}")
            parts.append(f"Total Findings: {risk['total_findings']}")
            sev = risk.get("severity_counts", {})
            parts.append(f"Severity: {sev.get('Critical', 0)} Critical, {sev.get('High', 0)} High, {sev.get('Medium', 0)} Medium, {sev.get('Low', 0)} Low, {sev.get('Info', 0)} Info")
        else:
            parts.append("No scans have been performed yet.")

        if self.latest_scan:
            scan = self.latest_scan
            parts.append(f"\nLatest Scan: {scan['api_name']} (v{scan.get('api_version', 'N/A')})")
            parts.append(f"  Endpoints: {scan['total_endpoints']}")
            parts.append(f"  Score: {scan['risk_score']}/100 ({scan['risk_level']})")
            parts.append(f"  Date: {scan.get('created_at', 'N/A')}")

        if self.critical_findings:
            parts.append(f"\n=== CRITICAL/HIGH FINDINGS ({len(self.critical_findings)}) ===")
            for f in self.critical_findings:
                parts.append(f"  [{f['severity']}] {f['vulnerability_name']}")
                parts.append(f"    CWE: {f.get('cwe_id', 'N/A')} | OWASP: {f.get('owasp_category', 'N/A')}")
                parts.append(f"    Endpoint: {f.get('affected_endpoint', 'N/A')}")
                parts.append(f"    {f.get('description', '')[:150]}")
                parts.append("")

        medium_findings = [f for f in self.findings if f.get("severity") == "Medium"]
        if medium_findings:
            parts.append(f"\n=== MEDIUM FINDINGS ({len(medium_findings)}) ===")
            for f in medium_findings[:5]:
                parts.append(f"  [{f['severity']}] {f['vulnerability_name']} - {f.get('affected_endpoint', 'N/A')}")

        if self.by_cwe:
            top_cwes = sorted(self.by_cwe.items(), key=lambda x: len(x[1]), reverse=True)[:5]
            parts.append(f"\nTop CWE Weaknesses:")
            for cwe, findings in top_cwes:
                parts.append(f"  {cwe}: {len(findings)} finding(s)")

        if self.ai_analysis:
            parts.append(f"\n=== AI ANALYSIS ===")
            if self.ai_analysis.get("executive_summary"):
                parts.append(f"Executive: {self.ai_analysis['executive_summary'][:200]}")
            if self.ai_analysis.get("recommended_mitigation"):
                parts.append(f"Mitigation: {self.ai_analysis['recommended_mitigation'][:200]}")

        if self.history and len(self.history) > 1:
            parts.append(f"\n=== SCAN HISTORY ({len(self.history)} scans) ===")
            for h in self.history[:5]:
                parts.append(f"  [{h['risk_level']}] {h['api_name']} - Score: {h['risk_score']}/100 - {h.get('created_at', 'N/A')}")

        return "\n".join(parts)

    def build_tool_context(self) -> dict:
        """Build a dict of all available context for tool-based responses."""
        return {
            "risk_summary": self.risk_summary,
            "latest_scan": self.latest_scan,
            "findings": self.findings,
            "critical_findings": self.critical_findings,
            "by_category": self.by_category,
            "by_cwe": self.by_cwe,
            "ai_analysis": self.ai_analysis,
            "history": self.history,
            "has_data": self.has_data,
        }

    def get_sidebar_data(self) -> dict:
        """Get data for the frontend sidebar panel."""
        risk = self.risk_summary
        latest = self.latest_scan
        critical = self.critical_findings
        recent_findings = self.findings[:10]

        return {
            "risk_score": risk.get("risk_score", 0),
            "risk_level": risk.get("risk_level", "Unknown"),
            "total_scans": risk.get("total_scans", 0),
            "total_findings": risk.get("total_findings", 0),
            "severity_counts": risk.get("severity_counts", {}),
            "latest_scan": latest,
            "critical_count": len(critical),
            "recent_findings": recent_findings,
            "scan_history": self.history[:5],
        }
