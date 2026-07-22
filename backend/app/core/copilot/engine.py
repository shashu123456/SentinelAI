"""AI Security Copilot - Agent-based security reasoning system.

Architecture:
    User Message
        → CopilotAgent (intent classification + tool routing)
        → SecurityContext (database retrieval)
        → Tools (get_latest_scan, get_critical_findings, etc.)
        → LLM / Rule-based Response
        → Grounded Response

Unlike a chatbot, this agent:
- Maintains conversation context across turns
- Pulls real data from the database
- Generates responses grounded in actual findings
- Falls back to intelligent rule-based analysis when LLM is unavailable
"""

from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy.orm import Session
from app.core.copilot.agent import CopilotAgent, classify_intent
from app.core.copilot.context_retrieval import SecurityContext
from app.core.copilot import tools as security_tools


class SecurityCopilot:
    """Agent-based security copilot that maintains context and provides
    grounded, contextual security guidance."""

    def __init__(self, settings=None, db: Session = None, user_id: int = None):
        self.db = db
        self.user_id = user_id
        self.agent = CopilotAgent(settings=settings, db=db, user_id=user_id)
        self._context = None

    def _get_context(self, scan_id: int = None) -> SecurityContext:
        """Get or build security context."""
        if self.db and self.user_id:
            return SecurityContext(self.db, self.user_id, scan_id)
        return None

    def chat(self, message: str, scan_id: int = None) -> dict:
        """Process a user message and return a grounded response.

        Returns:
            dict with keys: response, intent, tool_used, has_context
        """
        ctx = self._get_context(scan_id)
        if ctx is None:
            return {
                "response": self._handle_no_database(message),
                "intent": classify_intent(message),
                "tool_used": "",
                "has_context": False,
            }

        result = self.agent.process_message(message, ctx)
        return result

    def get_sidebar(self, scan_id: int = None) -> dict:
        """Get data for the frontend sidebar panel."""
        ctx = self._get_context(scan_id)
        if ctx is None:
            return {"risk_score": 0, "risk_level": "Unknown", "total_scans": 0,
                    "total_findings": 0, "severity_counts": {}, "latest_scan": None,
                    "critical_count": 0, "recent_findings": [], "scan_history": []}
        return ctx.get_sidebar_data()

    def get_context_summary(self) -> dict:
        """Return a summary of the current context state."""
        ctx = self._get_context()
        if ctx is None:
            return {"has_data": False, "total_findings": 0}
        tool_ctx = ctx.build_tool_context()
        return {
            "has_data": tool_ctx["has_data"],
            "total_findings": len(tool_ctx.get("findings", [])),
            "critical_count": len(tool_ctx.get("critical_findings", [])),
            "risk_score": tool_ctx.get("risk_summary", {}).get("risk_score", 0),
            "risk_level": tool_ctx.get("risk_summary", {}).get("risk_level", "Unknown"),
            "conversation_length": len(self.agent.get_conversation_history()),
        }

    def clear(self):
        """Clear conversation history."""
        self.agent.clear()

    def _handle_no_database(self, message: str) -> str:
        """Handle messages when no database connection is available."""
        lower = message.lower()
        if any(w in lower for w in ["hello", "hi", "hey"]):
            return (
                "Hello! I'm SentinelAI, your AI security analyst.\n\n"
                "I can help you analyze security findings, generate remediation plans, "
                "and understand your security posture.\n\n"
                "Run a scan first, then ask me anything about your findings."
            )
        return (
            "I need a database connection to access your security data. "
            "Please ensure the application is properly configured."
        )

    def load_scan_context(self, scan_data: dict, findings: list[dict] = None,
                          ai_analysis: dict = None):
        """Legacy method: Load scan results into context (for backward compatibility)."""
        pass

    def load_sast_context(self, sast_findings: list[dict]):
        """Legacy method: Load SAST results (for backward compatibility)."""
        pass

    def load_dep_context(self, dep_findings: list[dict]):
        """Legacy method: Load dependency results (for backward compatibility)."""
        pass
