"""Prompt Registry — versioned, validated, evaluated prompts for SentinelAI.

Every prompt is registered with:
- Version history
- Required output schema (validation)
- Evaluation criteria
- Hallucination prevention guards
"""

from dataclasses import dataclass, field


@dataclass
class PromptVersion:
    version: str
    template: str
    output_schema: dict[str, str] | None = None
    required_fields: list[str] = field(default_factory=list)
    max_tokens: int = 2048
    temperature: float = 0.3
    system_prompt: str = ""
    created_at: str = ""
    notes: str = ""


@dataclass
class PromptRecord:
    name: str
    description: str
    versions: list[PromptVersion] = field(default_factory=list)
    current_version: str = ""
    evaluation_score: float = 0.0
    total_evaluations: int = 0
    total_validations: int = 0
    total_failures: int = 0

    def current(self) -> PromptVersion | None:
        for v in self.versions:
            if v.version == self.current_version:
                return v
        return self.versions[-1] if self.versions else None

    def validate_output(self, output: dict) -> tuple[bool, list[str]]:
        """Validate AI output against the prompt's required schema."""
        prompt = self.current()
        if not prompt:
            return True, []

        errors = []
        for field_name in prompt.required_fields:
            if field_name not in output:
                errors.append(f"Missing required field: {field_name}")
            elif not output[field_name]:
                errors.append(f"Empty required field: {field_name}")

        if prompt.output_schema:
            for field_name, expected_type in prompt.output_schema.items():
                if field_name in output:
                    value = output[field_name]
                    if expected_type == "string" and not isinstance(value, str):
                        errors.append(
                            f"Field '{field_name}' must be string, got {type(value).__name__}"
                        )
                    elif expected_type == "list" and not isinstance(value, list):
                        errors.append(
                            f"Field '{field_name}' must be list, got {type(value).__name__}"
                        )
                    elif expected_type == "number" and not isinstance(value, int | float):
                        errors.append(
                            f"Field '{field_name}' must be number, got {type(value).__name__}"
                        )

        self.total_validations += 1
        if errors:
            self.total_failures += 1
        return len(errors) == 0, errors


class PromptRegistry:
    """Central registry for all AI prompts with versioning and validation."""

    def __init__(self):
        self._prompts: dict[str, PromptRecord] = {}
        self._register_all()

    def _register(self, name: str, description: str, *versions: PromptVersion):
        record = PromptRecord(name=name, description=description, versions=list(versions))
        if versions:
            record.current_version = versions[-1].version
        self._prompts[name] = record

    def get(self, name: str) -> PromptRecord | None:
        return self._prompts.get(name)

    def render(self, name: str, **kwargs) -> tuple[str, dict]:
        """Render a prompt with variables. Returns (rendered_prompt, metadata)."""
        record = self._prompts.get(name)
        if not record:
            raise ValueError(f"Prompt '{name}' not found in registry")

        version = record.current()
        if not version:
            raise ValueError(f"No versions registered for prompt '{name}'")

        template = version.template
        for key, value in kwargs.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))

        metadata = {
            "prompt_name": name,
            "version": version.version,
            "temperature": version.temperature,
            "max_tokens": version.max_tokens,
            "system_prompt": version.system_prompt,
        }
        return template, metadata

    def list_all(self) -> list[dict]:
        return [
            {
                "name": r.name,
                "description": r.description,
                "current_version": r.current_version,
                "evaluation_score": r.evaluation_score,
                "total_evaluations": r.total_evaluations,
                "total_validations": r.total_validations,
                "total_failures": r.total_failures,
                "version_count": len(r.versions),
            }
            for r in self._prompts.values()
        ]

    def _register_all(self):
        """Register all production prompts."""

        # ── Executive Report ──────────────────────────────────────────────
        self._register(
            "executive_report",
            "Generate executive-level security report from scan data",
            PromptVersion(
                version="1.0",
                template=(
                    "You are a senior cybersecurity advisor presenting to a board of directors.\n\n"
                    "Based on the following security assessment data, generate an executive report.\n\n"
                    "IMPORTANT RULES:\n"
                    "- Only reference data explicitly provided below\n"
                    "- Do NOT invent vulnerabilities or metrics not present in the data\n"
                    "- If data is insufficient, state what information is missing\n"
                    "- Use precise numbers from the provided data\n\n"
                    "Assessment Data:\n{scan_data}\n\n"
                    "Generate a JSON response with these exact keys:\n"
                    "- executive_summary: 2-3 sentences for C-level\n"
                    "- risk_assessment: Overall risk posture (1 paragraph)\n"
                    "- key_findings: List of top 5 findings (each with name, severity, impact)\n"
                    "- recommendations: List of 3-5 prioritized actions\n"
                    "- compliance_impact: Brief compliance implications\n"
                    "- trend: 'improving', 'worsening', or 'stable' with reasoning\n\n"
                    "Return ONLY valid JSON."
                ),
                required_fields=["executive_summary", "risk_assessment", "recommendations"],
                output_schema={
                    "executive_summary": "string",
                    "risk_assessment": "string",
                    "key_findings": "list",
                    "recommendations": "list",
                    "trend": "string",
                },
                temperature=0.3,
                system_prompt="You are a cybersecurity expert who provides accurate, data-driven security assessments. Never speculate or invent data.",
            ),
            PromptVersion(
                version="1.1",
                template=(
                    "You are a CISO presenting a quarterly security review.\n\n"
                    "Security Data:\n{scan_data}\n\n"
                    "Compliance Data:\n{compliance_data}\n\n"
                    "Historical Trends:\n{trend_data}\n\n"
                    "Generate a JSON executive report with:\n"
                    "- executive_summary: 2-3 sentences\n"
                    "- risk_assessment: Risk posture paragraph\n"
                    "- key_findings: Top 5 with name, severity, business_impact\n"
                    "- recommendations: Prioritized actions with effort estimate\n"
                    "- compliance_status: Current compliance posture\n"
                    "- trend: improving/worsening/stable with data-backed reasoning\n"
                    "- next_quarter_focus: Areas to prioritize\n\n"
                    "Rules: Only use provided data. Never invent metrics."
                ),
                required_fields=["executive_summary", "risk_assessment", "recommendations"],
                temperature=0.3,
                system_prompt="You are a CISO. Provide precise, data-driven analysis. Never speculate.",
            ),
        )

        # ── Risk Explanation ──────────────────────────────────────────────
        self._register(
            "risk_explanation",
            "Explain risk scores and risk levels in detail",
            PromptVersion(
                version="1.0",
                template=(
                    "Explain the following risk assessment to a technical team lead.\n\n"
                    "Risk Score: {risk_score}/100\n"
                    "Risk Level: {risk_level}\n"
                    "Findings: {findings_summary}\n\n"
                    "Explain:\n"
                    "1. What the risk score means\n"
                    "2. Why it's at this level\n"
                    "3. What specific findings drive this score\n"
                    "4. What would lower the score\n\n"
                    "Return JSON: {explanation, factors, improvement_steps}"
                ),
                required_fields=["explanation", "factors"],
                temperature=0.3,
            ),
        )

        # ── Threat Prediction ─────────────────────────────────────────────
        self._register(
            "threat_prediction",
            "Predict potential threats based on current vulnerabilities",
            PromptVersion(
                version="1.0",
                template=(
                    "Based on the following vulnerability data, predict likely threat scenarios.\n\n"
                    "Current Vulnerabilities:\n{vulnerabilities}\n\n"
                    "API Surface:\n{api_surface}\n\n"
                    "Rules:\n"
                    "- Only predict threats that are logically possible given the actual vulnerabilities\n"
                    "- Do NOT invent vulnerabilities that don't exist in the data\n"
                    "- Reference specific CWEs and OWASP categories present in the data\n\n"
                    "Return JSON with:\n"
                    "- immediate_threats: [{threat_name, likelihood, impact, affected_components}]\n"
                    "- attack_scenarios: [{scenario, steps, entry_point, data_at_risk}]\n"
                    "- risk_factors: [{factor, severity, mitigation}]\n"
                    "- predictions: [{prediction, confidence, basis}]\n\n"
                    "Return ONLY valid JSON."
                ),
                required_fields=["immediate_threats", "attack_scenarios"],
                temperature=0.4,
                system_prompt="Predict threats based ONLY on the vulnerabilities provided. Never invent new vulnerabilities.",
            ),
        )

        # ── Root Cause Explanation ────────────────────────────────────────
        self._register(
            "root_cause",
            "Explain the root cause of a security vulnerability",
            PromptVersion(
                version="1.0",
                template=(
                    "Explain the root cause of this security vulnerability.\n\n"
                    "Vulnerability: {vulnerability_name}\n"
                    "Category: {owasp_category}\n"
                    "CWE: {cwe_id}\n"
                    "Description: {description}\n"
                    "Endpoint: {affected_endpoint}\n"
                    "Evidence: {evidence}\n\n"
                    "Explain:\n"
                    "1. Root cause: Why does this vulnerability exist?\n"
                    "2. Code pattern: What code pattern causes this?\n"
                    "3. Design flaw: What design decision led to this?\n"
                    "4. Common mistakes: What developer mistakes cause this?\n\n"
                    "Return JSON: {root_cause, code_pattern, design_flaw, common_mistakes}"
                ),
                required_fields=["root_cause", "code_pattern"],
                temperature=0.3,
            ),
        )

        # ── Code Fix Generation ───────────────────────────────────────────
        self._register(
            "code_fix",
            "Generate code fix for a security vulnerability",
            PromptVersion(
                version="1.0",
                template=(
                    "Generate a code fix for this security vulnerability.\n\n"
                    "Vulnerability: {vulnerability_name}\n"
                    "CWE: {cwe_id}\n"
                    "Description: {description}\n"
                    "Endpoint: {affected_endpoint}\n"
                    "Method: {affected_method}\n\n"
                    "Rules:\n"
                    "- Generate only secure, production-ready code\n"
                    "- Follow OWASP secure coding guidelines\n"
                    "- Include error handling\n"
                    "- Add comments explaining security fixes\n"
                    "- If language/framework is unknown, use Python/FastAPI\n\n"
                    "Return JSON:\n"
                    "- vulnerable_pattern: Example of insecure code\n"
                    "- secure_pattern: The fixed code\n"
                    "- explanation: What changed and why\n"
                    "- dependencies: Any new dependencies needed\n"
                    "- testing: How to verify the fix"
                ),
                required_fields=["vulnerable_pattern", "secure_pattern", "explanation"],
                temperature=0.2,
                system_prompt="Generate secure, production-ready code. Never suggest code that introduces new vulnerabilities.",
            ),
        )

        # ── Architecture Review ───────────────────────────────────────────
        self._register(
            "architecture_review",
            "Review API architecture for security design flaws",
            PromptVersion(
                version="1.0",
                template=(
                    "Review this API architecture for security design flaws.\n\n"
                    "API Specification:\n{api_spec}\n\n"
                    "Endpoints: {total_endpoints}\n"
                    "Authentication: {auth_schemes}\n"
                    "Current Findings: {findings_summary}\n\n"
                    "Analyze:\n"
                    "1. Authentication design\n"
                    "2. Authorization model\n"
                    "3. Data flow security\n"
                    "4. Input validation strategy\n"
                    "5. Error handling patterns\n"
                    "6. Rate limiting adequacy\n\n"
                    "Return JSON:\n"
                    "- overall_assessment: Security maturity level (1-5)\n"
                    "- strengths: List of good design decisions\n"
                    "- weaknesses: List of design flaws with severity\n"
                    "- recommendations: Prioritized architectural improvements\n"
                    "- security_debt: Estimated effort to fix (days)"
                ),
                required_fields=["overall_assessment", "strengths", "weaknesses"],
                temperature=0.3,
            ),
        )

        # ── Security Advisor ──────────────────────────────────────────────
        self._register(
            "security_advisor",
            "Context-aware security recommendations",
            PromptVersion(
                version="1.0",
                template=(
                    "You are a security advisor. Based on the user's question and security context, "
                    "provide actionable security advice.\n\n"
                    "User Question: {question}\n\n"
                    "Security Context:\n{security_context}\n\n"
                    "Rules:\n"
                    "- Ground all advice in the actual scan data provided\n"
                    "- Reference specific findings when relevant\n"
                    "- Provide actionable, specific guidance (not generic advice)\n"
                    "- If the question cannot be answered from available data, say so\n\n"
                    "Return JSON: {answer, relevant_findings, action_items, references}"
                ),
                required_fields=["answer"],
                temperature=0.4,
                system_prompt="You are a senior security advisor. Provide specific, actionable advice grounded in real data.",
            ),
        )

        # ── Scan Summarizer ───────────────────────────────────────────────
        self._register(
            "scan_summarizer",
            "Generate concise scan summary",
            PromptVersion(
                version="1.0",
                template=(
                    "Summarize this security scan result.\n\n"
                    "Scan: {api_name} ({api_version})\n"
                    "Risk Score: {risk_score}/100 ({risk_level})\n"
                    "Endpoints: {total_endpoints}\n"
                    "Findings: {total_vulnerabilities}\n\n"
                    "Severity Breakdown:\n{severity_breakdown}\n\n"
                    "Top Findings:\n{top_findings}\n\n"
                    "Generate a concise, structured summary with:\n"
                    "- headline: One-line assessment\n"
                    "- risk_level: Critical/High/Medium/Low\n"
                    "- key_issues: Top 3 issues in plain language\n"
                    "- next_step: Single most important next action\n"
                    "- confidence: How confident in this assessment (0-100)\n\n"
                    "Return JSON."
                ),
                required_fields=["headline", "risk_level", "key_issues"],
                temperature=0.2,
            ),
        )

        # ── Natural Language Search ────────────────────────────────────────
        self._register(
            "nl_search",
            "Translate natural language queries into structured search",
            PromptVersion(
                version="1.0",
                template=(
                    "Convert this natural language security query into structured search parameters.\n\n"
                    "Query: {query}\n\n"
                    "Available fields: severity, owasp_category, cwe_id, vulnerability_name, "
                    "affected_endpoint, cvss_score, confidence, description\n\n"
                    "Return JSON:\n"
                    "- intent: What the user is looking for\n"
                    "- filters: {field: {operator, value}} (operators: eq, neq, gt, lt, gte, lte, contains, in)\n"
                    "- sort_by: field to sort by\n"
                    "- limit: max results\n\n"
                    "Return ONLY valid JSON."
                ),
                required_fields=["intent", "filters"],
                temperature=0.1,
            ),
        )

        # ── Dashboard Summary ─────────────────────────────────────────────
        self._register(
            "dashboard_summary",
            "Generate dashboard security summary",
            PromptVersion(
                version="1.0",
                template=(
                    "Generate a brief dashboard security summary.\n\n"
                    "Data:\n{dashboard_data}\n\n"
                    "Return JSON with:\n"
                    "- status_line: One-line security status\n"
                    "- highlights: 3 key data points\n"
                    "- alert: True if immediate action needed, with message\n"
                    "- score_trend: improving/worsening/stable\n\n"
                    "Keep it brief and data-driven."
                ),
                required_fields=["status_line", "highlights"],
                temperature=0.2,
            ),
        )

        # ── Automatic Remediation ─────────────────────────────────────────
        self._register(
            "auto_remediation",
            "Generate automatic remediation steps",
            PromptVersion(
                version="1.0",
                template=(
                    "Generate step-by-step remediation for this vulnerability.\n\n"
                    "Vulnerability: {vulnerability_name}\n"
                    "Severity: {severity}\n"
                    "CWE: {cwe_id}\n"
                    "OWASP: {owasp_category}\n"
                    "Description: {description}\n"
                    "Endpoint: {affected_endpoint}\n"
                    "Current Remediation: {existing_remediation}\n\n"
                    "Rules:\n"
                    "- Provide specific, actionable steps\n"
                    "- Include code examples where applicable\n"
                    "- Prioritize steps by impact\n"
                    "- Estimate effort for each step\n\n"
                    "Return JSON:\n"
                    "- steps: [{step, description, code_example (optional), effort_hours}]\n"
                    "- testing_steps: How to verify the fix\n"
                    "- estimated_total_hours: Total effort\n"
                    "- prerequisites: Dependencies or requirements"
                ),
                required_fields=["steps"],
                temperature=0.2,
            ),
        )


# Singleton
_registry = None


def get_prompt_registry() -> PromptRegistry:
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
    return _registry
