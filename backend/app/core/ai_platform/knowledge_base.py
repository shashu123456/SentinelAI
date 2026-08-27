"""Knowledge Base — structured security knowledge for grounded AI responses.

Every fact in this module is sourced from OWASP, CWE, NIST, and PCI DSS.
AI responses must reference this knowledge, never invent facts.
"""

from dataclasses import dataclass, field


@dataclass
class VulnerabilityKnowledge:
    cwe_id: str
    name: str
    owasp_category: str
    severity_baseline: str
    description: str
    root_cause: str
    common_patterns: list[str]
    remediation_steps: list[str]
    code_example_vulnerable: str
    code_example_secure: str
    references: list[str]


@dataclass
class OWASPRule:
    rule_id: str
    category: str
    owasp_api: str
    title: str
    description: str
    detection_logic: str
    severity: str
    confidence_base: int


@dataclass
class CWEEntry:
    cwe_id: str
    name: str
    description: str
    severity: str
    common_in: list[str]
    mitigation: str


# ═══════════════════════════════════════════════════════════════════════════
# VULNERABILITY KNOWLEDGE
# ═══════════════════════════════════════════════════════════════════════════

VULNERABILITY_KNOWLEDGE: dict[str, VulnerabilityKnowledge] = {
    "CWE-89": VulnerabilityKnowledge(
        cwe_id="CWE-89",
        name="SQL Injection",
        owasp_category="A03",
        severity_baseline="Critical",
        description="SQL injection occurs when user-supplied data is incorporated into SQL queries without proper sanitization or parameterization.",
        root_cause="Direct string concatenation or formatting of user input into SQL query strings instead of using parameterized queries.",
        common_patterns=[
            "f\"SELECT * FROM users WHERE id = {user_id}\"",
            "\"SELECT * FROM users WHERE name = '\" + name + \"'\"",
            "cursor.execute(f\"SELECT * FROM users WHERE id = {id}\")",
        ],
        remediation_steps=[
            "Use parameterized queries or prepared statements",
            "Apply input validation and sanitization",
            "Use an ORM with parameterized queries",
            "Implement least-privilege database permissions",
            "Enable SQL query logging for monitoring",
        ],
        code_example_vulnerable=(
            "cursor.execute(f\"SELECT * FROM users WHERE username = '{username}'\")"
        ),
        code_example_secure=(
            "cursor.execute(\"SELECT * FROM users WHERE username = %s\", (username,))"
        ),
        references=[
            "https://cwe.mitre.org/data/definitions/89.html",
            "https://owasp.org/Top10/A03_2021-Injection/",
        ],
    ),
    "CWE-79": VulnerabilityKnowledge(
        cwe_id="CWE-79",
        name="Cross-Site Scripting (XSS)",
        owasp_category="A03",
        severity_baseline="High",
        description="XSS vulnerabilities occur when user-supplied data is included in web pages without proper encoding or sanitization.",
        root_cause="Failure to encode output data before rendering in HTML, JavaScript, or CSS contexts.",
        common_patterns=[
            "innerHTML = userInput",
            "document.write(userInput)",
            "<div>{user_input}</div> without escaping",
            "eval(userInput)",
        ],
        remediation_steps=[
            "Encode all output data (HTML entity, JavaScript, URL encoding)",
            "Use Content Security Policy (CSP) headers",
            "Sanitize HTML input with a whitelist approach",
            "Use frameworks that auto-escape by default",
            "Avoid innerHTML, use textContent instead",
        ],
        code_example_vulnerable="element.innerHTML = userInput",
        code_example_secure="element.textContent = userInput",
        references=[
            "https://cwe.mitre.org/data/definitions/79.html",
            "https://owasp.org/Top10/A03_2021-Injection/",
        ],
    ),
    "CWE-639": VulnerabilityKnowledge(
        cwe_id="CWE-639",
        name="Broken Object Level Authorization (BOLA)",
        owasp_category="API1",
        severity_baseline="High",
        description="BOLA vulnerabilities allow attackers to access unauthorized resources by manipulating object identifiers in API requests.",
        root_cause="API endpoints that accept resource IDs without verifying the requesting user has authorization to access that specific resource.",
        common_patterns=[
            "GET /api/users/{other_user_id} without ownership check",
            "PUT /api/orders/{order_id} without verifying order belongs to user",
            "DELETE /api/files/{file_id} without access control",
        ],
        remediation_steps=[
            "Implement object-level authorization checks on every endpoint",
            "Use indirect object references (mapping internal IDs to user-scoped IDs)",
            "Apply the principle of least privilege",
            "Implement access control at the API gateway level",
        ],
        code_example_vulnerable=(
            "@app.get('/api/users/{user_id}')\n"
            "def get_user(user_id: int):\n"
            "    return db.query(User).get(user_id)"
        ),
        code_example_secure=(
            "@app.get('/api/users/{user_id}')\n"
            "def get_user(user_id: int, current_user = Depends(get_current_user)):\n"
            "    if user_id != current_user.id and current_user.role != 'admin':\n"
            "        raise HTTPException(403)\n"
            "    return db.query(User).get(user_id)"
        ),
        references=[
            "https://cwe.mitre.org/data/definitions/639.html",
            "https://owasp.org/API-Security/editions/2023/0xa1-broken-object-level-authorization/",
        ],
    ),
    "CWE-306": VulnerabilityKnowledge(
        cwe_id="CWE-306",
        name="Missing Authentication for Critical Function",
        owasp_category="API2",
        severity_baseline="Critical",
        description="The application does not perform authentication for critical functions, allowing unauthorized access.",
        root_cause="API endpoints that perform sensitive operations (create, update, delete) without requiring authentication.",
        common_patterns=[
            "POST /api/admin/users without auth middleware",
            "DELETE /api/data/{id} without authentication check",
            "No authentication decorator on sensitive routes",
        ],
        remediation_steps=[
            "Require authentication on all endpoints that modify data",
            "Implement role-based access control",
            "Use authentication middleware consistently",
            "Audit all endpoints for missing auth",
        ],
        code_example_vulnerable="@app.post('/api/admin/users')\ndef create_user(data): ...",
        code_example_secure="@app.post('/api/admin/users')\ndef create_user(data, user = Depends(require_admin)): ...",
        references=[
            "https://cwe.mitre.org/data/definitions/306.html",
            "https://owasp.org/API-Security/editions/2023/0xa2-broken-authentication/",
        ],
    ),
    "CWE-918": VulnerabilityKnowledge(
        cwe_id="CWE-918",
        name="Server-Side Request Forgery (SSRF)",
        owasp_category="API7",
        severity_baseline="High",
        description="SSRF vulnerabilities allow attackers to make the server perform requests to unintended locations.",
        root_cause="The application fetches resources from user-supplied URLs without validating the target location.",
        common_patterns=[
            "requests.get(user_url) without URL validation",
            "urllib.request.urlopen(user_input)",
            "fetch(user_supplied_url) on server side",
        ],
        remediation_steps=[
            "Validate and whitelist allowed URLs/domains",
            "Block internal/private IP ranges",
            "Use a network-level firewall",
            "Disable unnecessary URL schemes",
            "Implement response validation",
        ],
        code_example_vulnerable="response = requests.get(user_url)",
        code_example_secure="response = requests.get(validate_and_sanitize_url(user_url))",
        references=[
            "https://cwe.mitre.org/data/definitions/918.html",
            "https://owasp.org/API-Security/editions/2023/0xa7-server-side-request-forgery/",
        ],
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# CWE KNOWLEDGE
# ═══════════════════════════════════════════════════════════════════════════

CWE_KNOWLEDGE: dict[str, CWEEntry] = {
    "CWE-89": CWEEntry("CWE-89", "SQL Injection", "Improper sanitization of SQL queries", "Critical", ["Python", "Java", "PHP"], "Use parameterized queries"),
    "CWE-79": CWEEntry("CWE-79", "XSS", "Improper output encoding", "High", ["JavaScript", "HTML"], "Encode all output"),
    "CWE-22": CWEEntry("CWE-22", "Path Traversal", "Improper path validation", "High", ["Python", "Node.js"], "Validate and sanitize file paths"),
    "CWE-78": CWEEntry("CWE-78", "OS Command Injection", "Unsanitized input in system commands", "Critical", ["Python", "PHP"], "Avoid shell execution, use subprocess"),
    "CWE-639": CWEEntry("CWE-639", "BOLA", "Missing object-level authorization", "High", ["REST APIs"], "Check ownership on every request"),
    "CWE-306": CWEEntry("CWE-306", "Missing Auth", "No authentication on sensitive ops", "Critical", ["REST APIs"], "Require auth on all endpoints"),
    "CWE-918": CWEEntry("CWE-918", "SSRF", "Unvalidated server-side requests", "High", ["Python", "Node.js"], "Whitelist allowed URLs"),
    "CWE-502": CWEEntry("CWE-502", "Deserialization", "Unsafe deserialization of untrusted data", "Critical", ["Python", "Java"], "Avoid deserializing untrusted data"),
    "CWE-798": CWEEntry("CWE-798", "Hard-coded Credentials", "Credentials embedded in source code", "High", ["All languages"], "Use environment variables"),
    "CWE-327": CWEEntry("CWE-327", "Broken Crypto", "Use of weak cryptographic algorithms", "High", ["All languages"], "Use modern algorithms (AES-256, SHA-256)"),
}


# ═══════════════════════════════════════════════════════════════════════════
# KNOWLEDGE BASE ACCESS
# ═══════════════════════════════════════════════════════════════════════════

class KnowledgeBase:
    """Central knowledge base for security knowledge retrieval."""

    def __init__(self):
        self.vulnerabilities = VULNERABILITY_KNOWLEDGE
        self.cwe = CWE_KNOWLEDGE

    def get_vulnerability(self, cwe_id: str) -> VulnerabilityKnowledge | None:
        return self.vulnerabilities.get(cwe_id)

    def get_cwe(self, cwe_id: str) -> CWEEntry | None:
        return self.cwe.get(cwe_id)

    def validate_finding_against_knowledge(self, finding: dict) -> dict:
        """Validate a finding against the knowledge base and enrich it."""
        cwe_id = finding.get("cwe_id", "")
        kb_entry = self.vulnerabilities.get(cwe_id) or self.cwe.get(cwe_id)

        if not kb_entry:
            return {
                "validated": False,
                "enrichment": None,
                "note": f"No knowledge base entry for {cwe_id}",
            }

        return {
            "validated": True,
            "enrichment": {
                "known_root_cause": getattr(kb_entry, "root_cause", None),
                "known_mitigation": getattr(kb_entry, "mitigation", None) or getattr(kb_entry, "remediation_steps", []),
                "severity_baseline": getattr(kb_entry, "severity_baseline", None) or getattr(kb_entry, "severity", None),
                "references": getattr(kb_entry, "references", []),
            },
        }

    def get_knowledge_for_prompt(self, finding: dict) -> str:
        """Get structured knowledge to include in AI prompts."""
        cwe_id = finding.get("cwe_id", "")
        kb = self.vulnerabilities.get(cwe_id)
        if not kb:
            return f"No specific knowledge available for {cwe_id}."

        return (
            f"CWE Knowledge for {kb.cwe_id} ({kb.name}):\n"
            f"Root Cause: {kb.root_cause}\n"
            f"Common Patterns: {', '.join(kb.common_patterns[:3])}\n"
            f"Remediation: {'; '.join(kb.remediation_steps[:3])}\n"
            f"Secure Pattern: {kb.code_example_secure}\n"
            f"References: {', '.join(kb.references)}"
        )


_kb = None


def get_knowledge_base() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
