"""Tests for the Security Copilot Agent."""

import pytest
from unittest.mock import MagicMock, patch
from app.core.copilot.agent import CopilotAgent, classify_intent, AgentState
from app.core.copilot.context_retrieval import SecurityContext
from app.core.copilot.engine import SecurityCopilot
from app.core.copilot import tools as security_tools


# =============================================================================
# Intent Classification
# =============================================================================

class TestIntentClassification:

    def test_greeting(self):
        assert classify_intent("hello") == "greeting"
        assert classify_intent("hi") == "greeting"
        assert classify_intent("hey") == "greeting"
        assert classify_intent("good morning") == "greeting"

    def test_scan_status(self):
        assert classify_intent("what is my security status") == "scan_status"
        assert classify_intent("how are we doing") == "scan_status"
        assert classify_intent("what's my risk") == "scan_status"
        assert classify_intent("security posture") == "scan_status"

    def test_highest_risk(self):
        assert classify_intent("what is my highest risk issue") == "highest_risk"
        assert classify_intent("most critical vulnerability") == "highest_risk"
        assert classify_intent("biggest risk") == "highest_risk"
        assert classify_intent("worst finding") == "highest_risk"

    def test_explain_vuln(self):
        assert classify_intent("explain this vulnerability") == "explain_vuln"
        assert classify_intent("tell me about SQL injection") == "explain_vuln"
        assert classify_intent("describe this finding") == "explain_vuln"

    def test_why_critical(self):
        assert classify_intent("why is this critical") == "why_critical"
        assert classify_intent("why critical") == "why_critical"
        assert classify_intent("why does this matter") == "why_critical"

    def test_how_to_fix(self):
        assert classify_intent("how do I fix this") == "how_to_fix"
        assert classify_intent("how to fix SQL injection") == "how_to_fix"
        assert classify_intent("remediate this") == "how_to_fix"
        assert classify_intent("mitigate the risk") == "how_to_fix"

    def test_remediation_plan(self):
        assert classify_intent("generate remediation plan") == "remediation_plan"
        assert classify_intent("what should I fix first") == "remediation_plan"
        assert classify_intent("action plan") == "remediation_plan"

    def test_executive_summary(self):
        assert classify_intent("write executive summary") == "executive_summary"
        assert classify_intent("management summary") == "executive_summary"
        assert classify_intent("what's the bottom line") == "executive_summary"

    def test_attack_path(self):
        assert classify_intent("how would an attacker exploit this") == "attack_path"
        assert classify_intent("attack path analysis") == "attack_path"
        assert classify_intent("threat analysis") == "attack_path"

    def test_compliance(self):
        assert classify_intent("map to OWASP top 10") == "compliance"
        assert classify_intent("compliance check") == "compliance"
        assert classify_intent("CWE analysis") == "compliance"

    def test_compare(self):
        assert classify_intent("compare my scans") == "compare"
        assert classify_intent("scan comparison") == "compare"
        assert classify_intent("what's the trend") == "compare"

    def test_scan_history(self):
        assert classify_intent("scan history") == "scan_history"
        assert classify_intent("previous scans") == "scan_history"
        assert classify_intent("all scans") == "scan_history"

    def test_general(self):
        assert classify_intent("what is SQL injection") == "general"
        assert classify_intent("tell me a joke") == "general"
        assert classify_intent("random question") == "general"


# =============================================================================
# Agent State
# =============================================================================

class TestAgentState:

    def test_add_messages(self):
        state = AgentState()
        state.add_user("hello")
        state.add_assistant("hi there")
        assert len(state.messages) == 2
        assert state.messages[0].role == "user"
        assert state.messages[1].role == "assistant"

    def test_get_history(self):
        state = AgentState()
        state.add_user("hello")
        state.add_assistant("hi")
        history = state.get_history()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_clear(self):
        state = AgentState()
        state.add_user("hello")
        state = AgentState()
        assert len(state.messages) == 0


# =============================================================================
# Tools
# =============================================================================

class TestTools:

    def test_get_latest_scan_no_data(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        result = security_tools.get_latest_scan(db, 1)
        assert result is None

    def test_get_critical_findings_empty(self):
        db = MagicMock()
        query = db.query.return_value.join.return_value.filter.return_value
        query.filter.return_value = query
        query.order_by.return_value = query
        query.all.return_value = []
        result = security_tools.get_critical_findings(db, 1)
        assert result == []

    def test_get_risk_summary_no_scans(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        result = security_tools.get_risk_summary(db, 1)
        assert result["total_scans"] == 0
        assert result["risk_score"] == 0

    def test_generate_executive_summary_no_scans(self):
        result = security_tools.generate_executive_summary(MagicMock(), 1)
        assert "No scans" in result

    def test_generate_remediation_plan_no_findings(self):
        result = security_tools.generate_remediation_plan(MagicMock(), 1)
        assert "No findings" in result

    def test_explain_attack_path_no_critical(self):
        db = MagicMock()
        query = db.query.return_value.join.return_value.filter.return_value
        query.filter.return_value = query
        query.order_by.return_value = query
        query.all.return_value = []
        result = security_tools.explain_attack_path(db, 1)
        assert "No critical" in result

    def test_compare_scans_insufficient(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        result = security_tools.compare_scans(db, 1)
        assert result is None

    def test_get_findings_by_category_empty(self):
        db = MagicMock()
        query = db.query.return_value.join.return_value.filter.return_value
        query.filter.return_value = query
        query.order_by.return_value = query
        query.all.return_value = []
        result = security_tools.get_findings_by_category(db, 1)
        assert result == {}

    def test_get_scan_history_empty(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        result = security_tools.get_scan_history(db, 1)
        assert result == []


# =============================================================================
# CopilotAgent
# =============================================================================

class TestCopilotAgent:

    def test_greeting_without_data(self):
        agent = CopilotAgent()
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        ctx = SecurityContext(db, 1)
        result = agent.process_message("hello", ctx)
        assert result["intent"] == "greeting"
        assert "SentinelAI" in result["response"]
        assert result["has_context"] is False

    def test_greeting_with_data(self):
        agent = CopilotAgent()
        db = MagicMock()
        scan = MagicMock()
        scan.api_name = "Test API"
        scan.risk_score = 75
        scan.risk_level = "High"
        scan.total_endpoints = 10
        scan.total_vulnerabilities = 5
        scan.status = "completed"
        scan.created_at = MagicMock()
        scan.created_at.isoformat.return_value = "2024-01-01"
        scan.completed_at = MagicMock()
        scan.completed_at.isoformat.return_value = "2024-01-01"
        scan.findings = []

        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = scan
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [scan]

        ctx = SecurityContext(db, 1)
        result = agent.process_message("hello", ctx)
        assert result["intent"] == "greeting"
        assert "Test API" in result["response"]

    def test_scan_status_no_data(self):
        agent = CopilotAgent()
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        ctx = SecurityContext(db, 1)
        result = agent.process_message("what is my security status", ctx)
        assert result["intent"] == "scan_status"
        assert "No scans" in result["response"]

    def test_highest_risk_no_data(self):
        agent = CopilotAgent()
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        ctx = SecurityContext(db, 1)
        result = agent.process_message("what is my highest risk issue", ctx)
        assert result["intent"] == "highest_risk"
        assert "No findings" in result["response"]

    def test_general_no_data(self):
        agent = CopilotAgent()
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        ctx = SecurityContext(db, 1)
        result = agent.process_message("what is SQL injection", ctx)
        assert result["intent"] == "general"
        assert "security" in result["response"].lower()

    def test_tool_used_tracked(self):
        agent = CopilotAgent()
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        ctx = SecurityContext(db, 1)
        result = agent.process_message("what is my security status", ctx)
        assert result["tool_used"] != ""

    def test_conversation_history(self):
        agent = CopilotAgent()
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        ctx = SecurityContext(db, 1)
        agent.process_message("hello", ctx)
        agent.process_message("what is my security status", ctx)
        history = agent.get_conversation_history()
        assert len(history) == 4  # 2 user + 2 assistant

    def test_clear(self):
        agent = CopilotAgent()
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        ctx = SecurityContext(db, 1)
        agent.process_message("hello", ctx)
        agent.clear()
        assert len(agent.get_conversation_history()) == 0


# =============================================================================
# SecurityCopilot (Engine)
# =============================================================================

class TestSecurityCopilot:

    def test_init(self):
        copilot = SecurityCopilot()
        assert copilot.agent is not None

    def test_chat_no_database(self):
        copilot = SecurityCopilot()
        result = copilot.chat("hello")
        assert "SentinelAI" in result["response"]
        assert result["has_context"] is False

    def test_get_sidebar_no_database(self):
        copilot = SecurityCopilot()
        sidebar = copilot.get_sidebar()
        assert sidebar["risk_score"] == 0
        assert sidebar["total_scans"] == 0

    def test_get_context_summary_no_database(self):
        copilot = SecurityCopilot()
        summary = copilot.get_context_summary()
        assert summary["has_data"] is False

    def test_clear(self):
        copilot = SecurityCopilot()
        copilot.clear()
        assert len(copilot.agent.get_conversation_history()) == 0
