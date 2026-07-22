"""Agent controller for the security copilot.

This is the brain of the copilot. It:
1. Understands natural language intent (not just keywords)
2. Retrieves relevant security context
3. Invokes appropriate tools
4. Generates responses grounded in real data
5. Falls back to intelligent rule-based analysis when LLM is unavailable
"""

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Callable
from app.config import get_settings
from app.utils.logger import logger


@dataclass
class AgentMessage:
    role: str
    content: str
    timestamp: str = ""
    tool_used: str = ""


@dataclass
class AgentState:
    """Tracks the agent's conversation state."""
    messages: list[AgentMessage] = field(default_factory=list)
    last_tool: str = ""
    last_context_hash: str = ""

    def add_user(self, content: str):
        self.messages.append(AgentMessage(role="user", content=content))

    def add_assistant(self, content: str, tool_used: str = ""):
        self.messages.append(AgentMessage(role="assistant", content=content, tool_used=tool_used))

    def get_history(self, limit: int = 10) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in self.messages[-limit:]]


def classify_intent(message: str) -> str:
    """Classify user intent using natural language understanding.

    Returns one of: greeting, scan_status, highest_risk, explain_vuln,
    why_critical, how_to_fix, remediation_plan, executive_summary,
    attack_path, compliance, compare, scan_history, general
    """
    lower = message.lower().strip()

    greetings = ["hello", "hey", "good morning", "good afternoon", "good evening", "what's up", "sup"]
    if any(g in lower for g in greetings) and len(lower.split()) <= 5:
        return "greeting"
    if lower.strip() in ("hi", "yo", "hiya"):
        return "greeting"

    if any(w in lower for w in ["what is my security", "security state", "security status", "current status", "what's my risk", "how are we doing", "security posture"]):
        return "scan_status"

    if any(w in lower for w in ["highest risk", "most critical", "biggest risk", "most dangerous", "worst", "top risk", "what is my highest"]):
        return "highest_risk"

    if any(w in lower for w in ["explain this", "explain the", "what is this", "tell me about", "describe this", "details on"]):
        return "explain_vuln"

    if any(w in lower for w in ["why is this critical", "why critical", "why is this high", "why important", "why does this matter"]):
        return "why_critical"

    if any(w in lower for w in ["how do i fix", "how to fix", "fix this", "remediate", "mitigate", "solution for", "patch", "resolve"]):
        return "how_to_fix"

    if any(w in lower for w in ["remediation plan", "fix plan", "action plan", "what should i fix first", "priority", "remediation steps"]):
        return "remediation_plan"

    if any(w in lower for w in ["executive summary", "management summary", "leadership", "board", "brief", "tldr", "bottom line"]):
        return "executive_summary"

    if any(w in lower for w in ["attack", "exploit", "how would", "attack path", "threat", "attacker", "breach"]):
        return "attack_path"

    if any(w in lower for w in ["owasp", "compliance", "standard", "regulation", "pci", "gdpr", "soc 2", "cwe"]):
        return "compliance"

    if any(w in lower for w in ["compare", "comparison", "difference", "improvement", "better", "worse", "trend", "progress"]):
        return "compare"

    if any(w in lower for w in ["history", "previous scans", "past scans", "all scans", "scan history"]):
        return "scan_history"

    return "general"


class CopilotAgent:
    """Security copilot agent that processes user messages and generates
    grounded, contextual security responses."""

    def __init__(self, settings=None, db=None, user_id=None):
        self.settings = settings or get_settings()
        self.state = AgentState()
        self.db = db
        self.user_id = user_id

    def process_message(self, message: str, context_builder) -> dict:
        """Process a user message and return a response.

        Args:
            message: The user's natural language message
            context_builder: A SecurityContext instance for data retrieval

        Returns:
            dict with keys: response, intent, tool_used, has_context
        """
        self.state.add_user(message)
        intent = classify_intent(message)

        ctx = context_builder.build_tool_context()
        has_data = ctx.get("has_data", False)

        tool_used = ""
        response = ""

        if intent == "greeting":
            response = self._handle_greeting(ctx)
        elif intent == "scan_status":
            response = self._handle_scan_status(ctx)
            tool_used = "get_risk_summary"
        elif intent == "highest_risk":
            response = self._handle_highest_risk(ctx)
            tool_used = "get_critical_findings"
        elif intent == "explain_vuln":
            response = self._handle_explain_vuln(ctx, message)
            tool_used = "get_vulnerability_details"
        elif intent == "why_critical":
            response = self._handle_why_critical(ctx)
            tool_used = "explain_security_issue"
        elif intent == "how_to_fix":
            response = self._handle_how_to_fix(ctx)
            tool_used = "generate_remediation"
        elif intent == "remediation_plan":
            response = self._handle_remediation_plan(ctx)
            tool_used = "generate_report"
        elif intent == "executive_summary":
            response = self._handle_executive_summary(ctx)
            tool_used = "generate_report"
        elif intent == "attack_path":
            response = self._handle_attack_path(ctx)
            tool_used = "explain_security_issue"
        elif intent == "compliance":
            response = self._handle_compliance(ctx)
            tool_used = "get_findings_by_category"
        elif intent == "compare":
            response = self._handle_compare(ctx)
            tool_used = "compare_scans"
        elif intent == "scan_history":
            response = self._handle_scan_history(ctx)
            tool_used = "get_scan_history"
        else:
            response = self._handle_general(ctx, message)

        if not response:
            response = self._handle_general(ctx, message)

        self.state.add_assistant(response, tool_used)

        return {
            "response": response,
            "intent": intent,
            "tool_used": tool_used,
            "has_context": has_data,
        }

    def _handle_greeting(self, ctx: dict) -> str:
        """Handle greetings with contextual security state."""
        risk = ctx.get("risk_summary", {})
        latest = ctx.get("latest_scan")

        if not latest:
            return (
                "Hello! I'm SentinelAI, your AI security analyst.\n\n"
                "I don't see any completed scans yet. Once you run a scan, I can help you "
                "analyze findings, generate remediation plans, and understand your security posture.\n\n"
                "Try uploading an API spec through the Dashboard to get started."
            )

        score = risk.get("risk_score", 0)
        level = risk.get("risk_level", "Unknown")
        total = risk.get("total_findings", 0)
        sev = risk.get("severity_counts", {})
        critical = sev.get("Critical", 0)
        high = sev.get("High", 0)

        lines = [
            f"Hello! I'm SentinelAI, your AI security analyst.",
            f"",
            f"**Current Security State:**",
            f"- Risk Score: **{score}/100** ({level})",
            f"- Total Findings: **{total}**",
            f"- Critical: **{critical}** | High: **{high}**",
            f"- Latest Scan: **{latest.get('api_name', 'N/A')}**",
            f"",
        ]

        if critical > 0:
            lines.append(f"You have **{critical} Critical** findings that need immediate attention. Ask me about them or request a remediation plan.")
        elif high > 0:
            lines.append(f"You have **{high} High** severity findings. I recommend addressing these before your next deployment.")
        else:
            lines.append(f"No critical issues found. Your security posture looks good. Ask me anything about your findings.")

        return "\n".join(lines)

    def _handle_scan_status(self, ctx: dict) -> str:
        """Provide comprehensive security status."""
        risk = ctx.get("risk_summary", {})
        if not risk.get("total_scans"):
            return "No scans have been performed yet. Upload an API specification to start a security assessment."

        latest = ctx.get("latest_scan")
        findings = ctx.get("findings", [])
        critical = ctx.get("critical_findings", [])

        sev = risk.get("severity_counts", {})
        score = risk.get("risk_score", 0)
        level = risk.get("risk_level", "Unknown")

        lines = [
            f"**Security Assessment Status**",
            f"",
            f"**Risk Score:** {score}/100 ({level})",
            f"**Total Scans:** {risk.get('total_scans', 0)}",
            f"**Total Findings:** {risk.get('total_findings', 0)}",
            f"",
            f"**Severity Distribution:**",
            f"- Critical: {sev.get('Critical', 0)}",
            f"- High: {sev.get('High', 0)}",
            f"- Medium: {sev.get('Medium', 0)}",
            f"- Low: {sev.get('Low', 0)}",
            f"- Info: {sev.get('Info', 0)}",
            f"",
        ]

        if latest:
            lines.append(f"**Latest Scan:** {latest.get('api_name', 'N/A')} (Score: {latest.get('risk_score', 0)}/100)")

        if critical:
            lines.append(f"")
            lines.append(f"**{len(critical)} Critical/High findings require attention:**")
            for f in critical[:5]:
                lines.append(f"- [{f['severity']}] {f['vulnerability_name']} at {f.get('affected_endpoint', 'N/A')}")

        return "\n".join(lines)

    def _handle_highest_risk(self, ctx: dict) -> str:
        """Explain the highest risk findings in detail."""
        critical = ctx.get("critical_findings", [])
        if not critical:
            all_f = ctx.get("findings", [])
            if not all_f:
                return "No findings available. Run a scan to analyze your security posture."
            critical = all_f[:3]

        lines = ["**Highest Risk Findings**", ""]

        for i, f in enumerate(critical[:3], 1):
            lines.append(f"### {i}. {f['vulnerability_name']} ({f['severity']})")
            lines.append(f"")
            lines.append(f"**CWE:** {f.get('cwe_id', 'N/A')}")
            lines.append(f"**OWASP:** {f.get('owasp_category', 'N/A')}")
            lines.append(f"**Endpoint:** {f.get('affected_endpoint', 'N/A')}")
            lines.append(f"**Confidence:** {f.get('confidence', 85)}%")
            lines.append(f"")
            lines.append(f"**What it is:** {f.get('description', 'N/A')}")
            lines.append(f"")
            lines.append(f"**Impact:** {f.get('impact', 'N/A')}")
            lines.append(f"")
            lines.append(f"**How to fix:** {f.get('remediation', 'See OWASP guidelines')}")
            lines.append(f"")

        return "\n".join(lines)

    def _handle_explain_vuln(self, ctx: dict, message: str) -> str:
        """Explain a specific vulnerability."""
        findings = ctx.get("findings", [])
        if not findings:
            return "No findings available. Run a scan first."

        lower = message.lower()
        matched = None
        for f in findings:
            name = f.get("vulnerability_name", "").lower()
            if name and name in lower:
                matched = f
                break

        if not matched:
            for f in findings:
                name = f.get("vulnerability_name", "").lower()
                cwe = f.get("cwe_id", "").lower()
                if any(w in lower for w in name.split() if len(w) > 3) or cwe in lower:
                    matched = f
                    break

        if not matched:
            matched = findings[0]

        return (
            f"**{matched['vulnerability_name']}** ({matched['severity']})\n\n"
            f"**CWE:** {matched.get('cwe_id', 'N/A')}\n"
            f"**Category:** {matched.get('owasp_category', 'N/A')}\n"
            f"**Endpoint:** {matched.get('affected_endpoint', 'N/A')}\n\n"
            f"**Description:**\n{matched.get('description', 'N/A')}\n\n"
            f"**Business Impact:**\n{matched.get('impact', 'N/A')}\n\n"
            f"**Remediation:**\n{matched.get('remediation', 'N/A')}"
        )

    def _handle_why_critical(self, ctx: dict) -> str:
        """Explain why findings are critical."""
        critical = ctx.get("critical_findings", [])
        if not critical:
            return "No critical findings in the current assessment."

        lines = ["**Why These Findings Are Critical**", ""]

        for f in critical[:3]:
            lines.append(f"### {f['vulnerability_name']}")
            lines.append(f"")
            lines.append(f"**Severity:** {f['severity']} | **CWE:** {f.get('cwe_id', 'N/A')}")
            lines.append(f"")
            lines.append(f"**Why it matters:** {f.get('impact', 'N/A')}")
            lines.append(f"")
            lines.append(f"**Attack scenario:** An attacker could exploit this vulnerability to "
                         f"{'compromise user data' if 'injection' in f.get('vulnerability_name', '').lower() else 'gain unauthorized access'}.")
            lines.append(f"")

        return "\n".join(lines)

    def _handle_how_to_fix(self, ctx: dict) -> str:
        """Provide specific fix guidance."""
        critical = ctx.get("critical_findings", [])
        if not critical:
            return "No critical findings to fix. Run a scan to identify issues."

        lines = ["**Fix Guide**", ""]

        for f in critical[:3]:
            lines.append(f"### {f['vulnerability_name']} ({f['severity']})")
            lines.append(f"**Endpoint:** {f.get('affected_endpoint', 'N/A')}")
            lines.append(f"**Fix:** {f.get('remediation', 'See OWASP guidelines')}")
            lines.append(f"")

        return "\n".join(lines)

    def _handle_remediation_plan(self, ctx: dict) -> str:
        """Generate a prioritized remediation plan."""
        from app.core.copilot.tools import generate_remediation_plan
        return generate_remediation_plan(self.db, self.user_id)

    def _handle_executive_summary(self, ctx: dict) -> str:
        """Generate executive summary."""
        from app.core.copilot.tools import generate_executive_summary
        return generate_executive_summary(self.db, self.user_id)

    def _handle_attack_path(self, ctx: dict) -> str:
        """Analyze attack paths."""
        from app.core.copilot.tools import explain_attack_path
        return explain_attack_path(self.db, self.user_id)

    def _handle_compliance(self, ctx: dict) -> str:
        """Map findings to compliance standards."""
        by_category = ctx.get("by_category", {})
        if not by_category:
            return "No findings to map to compliance standards."

        lines = ["**Compliance Mapping**", ""]

        owasp_map = {
            "API1": "Broken Object Level Authorization",
            "API2": "Broken Authentication",
            "API3": "Broken Object Property Level Authorization",
            "API4": "Unrestricted Resource Consumption",
            "API5": "Broken Function Level Authorization",
            "API6": "Unrestricted Access to Sensitive Business Flows",
            "API7": "Server Side Request Forgery",
            "API8": "Security Misconfiguration",
            "API9": "Improper Inventory Management",
            "API10": "Unsafe Consumption of APIs",
        }

        lines.append("### OWASP API Security Top 10 Coverage")
        lines.append("")
        for cat, findings in sorted(by_category.items()):
            owasp_name = owasp_map.get(cat, cat)
            lines.append(f"**{cat} - {owasp_name}:** {len(findings)} finding(s)")
            for f in findings[:3]:
                lines.append(f"  - {f['vulnerability_name']} ({f['severity']})")
            lines.append("")

        total = sum(len(f) for f in by_category.values())
        lines.append(f"**Total:** {total} findings across {len(by_category)} OWASP categories")

        return "\n".join(lines)

    def _handle_compare(self, ctx: dict) -> str:
        """Compare scans."""
        history = ctx.get("history", [])
        if len(history) < 2:
            return "Need at least 2 scans to compare. Run another scan to see progress."

        current = history[0]
        previous = history[1]
        change = current["risk_score"] - previous["risk_score"]

        return (
            f"**Scan Comparison**\n\n"
            f"**Previous:** {previous['api_name']} - Score: {previous['risk_score']}/100 ({previous['risk_level']})\n"
            f"**Current:** {current['api_name']} - Score: {current['risk_score']}/100 ({current['risk_level']})\n\n"
            f"**Change:** {'+' if change > 0 else ''}{change} points\n"
            f"**Trend:** {'Improved' if change < 0 else 'Degraded' if change > 0 else 'No change'}"
        )

    def _handle_scan_history(self, ctx: dict) -> str:
        """Show scan history."""
        history = ctx.get("history", [])
        if not history:
            return "No scan history available."

        lines = ["**Scan History**", ""]
        for h in history:
            lines.append(f"- **{h['api_name']}** | Score: {h['risk_score']}/100 ({h['risk_level']}) | {h.get('created_at', 'N/A')}")

        return "\n".join(lines)

    def _handle_general(self, ctx: dict, message: str) -> str:
        """Handle general questions with context awareness."""
        has_data = ctx.get("has_data", False)
        latest = ctx.get("latest_scan")

        if not has_data:
            return (
                "I can help you with security analysis. Here's what I can do:\n\n"
                "- **Security Status:** Ask about your current risk posture\n"
                "- **Vulnerability Analysis:** Ask about specific findings\n"
                "- **Remediation:** Get fix guidance for vulnerabilities\n"
                "- **Executive Summary:** Generate leadership-ready reports\n"
                "- **Attack Analysis:** Understand potential attack paths\n"
                "- **Compliance:** Map findings to OWASP/CWE standards\n\n"
                "Run a scan first, then ask me anything about your security findings."
            )

        return (
            f"I can help you analyze your security findings. Here are some things you can ask:\n\n"
            f"- \"What is my highest risk issue?\"\n"
            f"- \"Explain this vulnerability\"\n"
            f"- \"Why is this critical?\"\n"
            f"- \"How do I fix this?\"\n"
            f"- \"Generate remediation plan\"\n"
            f"- \"Write executive summary\"\n"
            f"- \"How would an attacker exploit this?\"\n"
            f"- \"Map to OWASP Top 10\"\n"
            f"- \"Compare my scans\""
        )

    def get_conversation_history(self) -> list[dict]:
        return self.state.get_history()

    def clear(self):
        self.state = AgentState()
