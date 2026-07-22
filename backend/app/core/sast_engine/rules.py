"""SAST security rules for Python, JavaScript, and Java static analysis.

Each rule defines a pattern that detects a specific vulnerability class.
Rules are organized by language and vulnerability category.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFO = "Info"


class Language(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    ALL = "all"


@dataclass
class SecurityRule:
    id: str
    name: str
    severity: Severity
    cwe_id: str
    language: Language
    pattern: str
    description: str
    remediation: str
    confidence: float = 0.7
    owasp_category: Optional[str] = None
    tags: list = field(default_factory=list)


# =============================================================================
# PYTHON SECURITY RULES
# =============================================================================

PYTHON_RULES = [
    SecurityRule(
        id="SAST-PY-001",
        name="SQL Injection via String Formatting",
        severity=Severity.CRITICAL,
        cwe_id="CWE-89",
        language=Language.PYTHON,
        pattern=r'(?:execute|cursor\.execute|raw|rawquery)\s*\(\s*[f"\'].*\{.*\}.*[\'"]',
        description="SQL query constructed using string formatting (f-string or .format()) allows SQL injection.",
        remediation="Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
        confidence=0.85,
        owasp_category="API8",
        tags=["sql", "injection", "database"],
    ),
    SecurityRule(
        id="SAST-PY-002",
        name="SQL Injection via String Concatenation",
        severity=Severity.CRITICAL,
        cwe_id="CWE-89",
        language=Language.PYTHON,
        pattern=r'(?:execute|cursor\.execute)\s*\(\s*["\'].*["\']?\s*\+\s*\w+',
        description="SQL query constructed via string concatenation allows SQL injection.",
        remediation="Use parameterized queries instead of string concatenation.",
        confidence=0.80,
        owasp_category="API8",
        tags=["sql", "injection", "database"],
    ),
    SecurityRule(
        id="SAST-PY-003",
        name="SQL Injection via % Formatting",
        severity=Severity.CRITICAL,
        cwe_id="CWE-89",
        language=Language.PYTHON,
        pattern=r'(?:execute|cursor\.execute)\s*\(\s*["\'].*%s.*["\']\s*%\s*',
        description="SQL query constructed using % string formatting allows SQL injection.",
        remediation="Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
        confidence=0.80,
        owasp_category="API8",
        tags=["sql", "injection", "database"],
    ),
    SecurityRule(
        id="SAST-PY-010",
        name="OS Command Injection",
        severity=Severity.CRITICAL,
        cwe_id="CWE-78",
        language=Language.PYTHON,
        pattern=r'(?:os\.system|os\.popen|subprocess\.call|subprocess\.run|subprocess\.Popen)\s*\([^)]*(?:input|request|param|arg|user|data|cmd)',
        description="OS command constructed from user input allows command injection.",
        remediation="Use subprocess.run() with shell=False and a list of arguments. Validate and sanitize all inputs.",
        confidence=0.80,
        tags=["command", "injection", "os"],
    ),
    SecurityRule(
        id="SAST-PY-011",
        name="Shell=True with Variable",
        severity=Severity.HIGH,
        cwe_id="CWE-78",
        language=Language.PYTHON,
        pattern=r'subprocess\.\w+\([^)]*shell\s*=\s*True',
        description="subprocess called with shell=True enables shell injection if arguments are user-controlled.",
        remediation="Use shell=False (default) and pass arguments as a list.",
        confidence=0.65,
        tags=["command", "injection", "os"],
    ),
    SecurityRule(
        id="SAST-PY-020",
        name="Hardcoded Password in Source Code",
        severity=Severity.HIGH,
        cwe_id="CWE-798",
        language=Language.PYTHON,
        pattern=r'(?:password|passwd|pwd|secret|api_key|apikey|api_secret|token|auth)\s*=\s*["\'][^"\']{4,}["\']',
        description="Credential or secret hardcoded in source code.",
        remediation="Store secrets in environment variables or a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault).",
        confidence=0.70,
        owasp_category="API2",
        tags=["secrets", "credential", "hardcoded"],
    ),
    SecurityRule(
        id="SAST-PY-021",
        name="Hardcoded AWS Key",
        severity=Severity.CRITICAL,
        cwe_id="CWE-798",
        language=Language.PYTHON,
        pattern=r'(?:AKIA|ASIA)[A-Z0-9]{16}',
        description="AWS access key ID detected in source code.",
        remediation="Rotate the key immediately. Use IAM roles or environment variables.",
        confidence=0.95,
        tags=["secrets", "aws", "cloud"],
    ),
    SecurityRule(
        id="SAST-PY-030",
        name="Unsafe Deserialization",
        severity=Severity.CRITICAL,
        cwe_id="CWE-502",
        language=Language.PYTHON,
        pattern=r'pickle\.(?:loads?|Unpickler)\s*\(',
        description="Deserializing untrusted data with pickle can lead to arbitrary code execution.",
        remediation="Use safe serialization formats (JSON, MessagePack). If pickle is required, restrict the allowed classes.",
        confidence=0.90,
        tags=["deserialization", "rce"],
    ),
    SecurityRule(
        id="SAST-PY-031",
        name="Unsafe YAML Loading",
        severity=Severity.HIGH,
        cwe_id="CWE-502",
        language=Language.PYTHON,
        pattern=r'yaml\.(?:load|unsafe_load)\s*\([^)]*(?:stream|data|content|request)',
        description="Loading untrusted YAML data without SafeLoader can execute arbitrary Python objects.",
        remediation="Use yaml.safe_load() or yaml.safe_load_all() instead of yaml.load().",
        confidence=0.80,
        tags=["deserialization", "yaml"],
    ),
    SecurityRule(
        id="SAST-PY-040",
        name="Weak MD5 Hash",
        severity=Severity.MEDIUM,
        cwe_id="CWE-327",
        language=Language.PYTHON,
        pattern=r'hashlib\.md5\s*\(',
        description="MD5 is cryptographically broken and should not be used for security purposes.",
        remediation="Use SHA-256 or stronger: hashlib.sha256()",
        confidence=0.90,
        tags=["crypto", "hash"],
    ),
    SecurityRule(
        id="SAST-PY-041",
        name="Weak SHA1 Hash",
        severity=Severity.MEDIUM,
        cwe_id="CWE-327",
        language=Language.PYTHON,
        pattern=r'hashlib\.sha1\s*\(',
        description="SHA-1 is deprecated for security use due to collision attacks.",
        remediation="Use SHA-256 or stronger: hashlib.sha256()",
        confidence=0.85,
        tags=["crypto", "hash"],
    ),
    SecurityRule(
        id="SAST-PY-042",
        name="Weak Random Number Generator",
        severity=Severity.MEDIUM,
        cwe_id="CWE-338",
        language=Language.PYTHON,
        pattern=r'(?:random\.random|random\.randint|random\.choice|random\.randrange)\s*\(',
        description="The random module uses a predictable PRNG (Mersenne Twister). Not suitable for security contexts.",
        remediation="Use secrets module for cryptographic randomness: secrets.token_hex(), secrets.choice()",
        confidence=0.60,
        tags=["crypto", "random"],
    ),
    SecurityRule(
        id="SAST-PY-050",
        name="Path Traversal via User Input",
        severity=Severity.HIGH,
        cwe_id="CWE-22",
        language=Language.PYTHON,
        pattern=r'(?:open|Path)\s*\([^)]*(?:request|param|input|arg|data|filename)',
        description="File path constructed from user input may allow path traversal attacks.",
        remediation="Validate and sanitize file paths. Use os.path.realpath() and verify the resolved path is within allowed directories.",
        confidence=0.70,
        owasp_category="API1",
        tags=["path", "traversal", "file"],
    ),
    SecurityRule(
        id="SAST-PY-051",
        name="Insecure Temp File Usage",
        severity=Severity.LOW,
        cwe_id="CWE-377",
        language=Language.PYTHON,
        pattern=r'tempfile\.(?:mktemp|mkstemp)\s*\(',
        description="Using temp files without proper permissions can expose sensitive data.",
        remediation="Use tempfile.NamedTemporaryFile() with appropriate permissions, or use tempfile.mkstemp() with umask.",
        confidence=0.50,
        tags=["temp", "file"],
    ),
    SecurityRule(
        id="SAST-PY-060",
        name="Debug Mode Enabled",
        severity=Severity.MEDIUM,
        cwe_id="CWE-489",
        language=Language.PYTHON,
        pattern=r'debug\s*=\s*True|app\.run\([^)]*debug\s*=\s*True',
        description="Debug mode enabled in production exposes stack traces and internal information.",
        remediation="Disable debug mode in production. Use environment variables to control debug settings.",
        confidence=0.85,
        owasp_category="API8",
        tags=["config", "debug"],
    ),
    SecurityRule(
        id="SAST-PY-061",
        name="Eval/Exec with User Input",
        severity=Severity.CRITICAL,
        cwe_id="CWE-95",
        language=Language.PYTHON,
        pattern=r'(?:eval|exec)\s*\([^)]*(?:request|param|input|arg|data|user)',
        description="eval() or exec() with user-controlled input allows arbitrary code execution.",
        remediation="Never use eval() or exec() with untrusted input. Use ast.literal_eval() for safe evaluation.",
        confidence=0.90,
        tags=["code", "injection", "rce"],
    ),
    SecurityRule(
        id="SAST-PY-062",
        name="Assert Used for Validation",
        severity=Severity.LOW,
        cwe_id="CWE-617",
        language=Language.PYTHON,
        pattern=r'assert\s+(?:isinstance|hasattr|len|type|id|name|user|token|auth)',
        description="assert statements are removed when Python runs with -O flag. Do not use for security validation.",
        remediation="Use proper if/else checks with explicit error handling for security-critical validation.",
        confidence=0.50,
        tags=["validation", "logic"],
    ),
    SecurityRule(
        id="SAST-PY-070",
        name="Insecure HTTP Usage",
        severity=Severity.MEDIUM,
        cwe_id="CWE-319",
        language=Language.PYTHON,
        pattern=r'requests\.(?:get|post|put|delete|patch)\s*\(\s*["\']http://',
        description="HTTP (not HTTPS) used for outbound requests. Data transmitted in cleartext.",
        remediation="Use HTTPS for all outbound requests to protect data in transit.",
        confidence=0.80,
        tags=["network", "http", "cleartext"],
    ),
    SecurityRule(
        id="SAST-PY-071",
        name="SSL Verification Disabled",
        severity=Severity.HIGH,
        cwe_id="CWE-295",
        language=Language.PYTHON,
        pattern=r'verify\s*=\s*False|ssl\._create_unverified_context',
        description="SSL certificate verification disabled, enabling man-in-the-middle attacks.",
        remediation="Always verify SSL certificates in production. Use proper CA certificates.",
        confidence=0.90,
        tags=["ssl", "tls", "mitm"],
    ),
]

# =============================================================================
# JAVASCRIPT SECURITY RULES
# =============================================================================

JAVASCRIPT_RULES = [
    SecurityRule(
        id="SAST-JS-001",
        name="SQL Injection via Template Literal",
        severity=Severity.CRITICAL,
        cwe_id="CWE-89",
        language=Language.JAVASCRIPT,
        pattern=r'(?:query|execute|run|raw)\s*\(\s*`[^`]*\$\{',
        description="SQL query constructed using template literals allows SQL injection.",
        remediation="Use parameterized queries or prepared statements.",
        confidence=0.85,
        owasp_category="API8",
        tags=["sql", "injection"],
    ),
    SecurityRule(
        id="SAST-JS-010",
        name="Command Injection via exec",
        severity=Severity.CRITICAL,
        cwe_id="CWE-78",
        language=Language.JAVASCRIPT,
        pattern=r'(?:child_process\.exec|execSync|execFile)\s*\([^)]*(?:req\.|input|param|user|data|query)',
        description="OS command constructed from user input allows command injection.",
        remediation="Use execFile() with arguments as an array. Validate all inputs.",
        confidence=0.80,
        tags=["command", "injection"],
    ),
    SecurityRule(
        id="SAST-JS-011",
        name="eval() Usage",
        severity=Severity.CRITICAL,
        cwe_id="CWE-95",
        language=Language.JAVASCRIPT,
        pattern=r'\beval\s*\([^)]*(?:req\.|input|param|user|data|query|body)',
        description="eval() with user-controlled input allows arbitrary code execution.",
        remediation="Never use eval(). Use JSON.parse() for data, or specific parsers for configurations.",
        confidence=0.90,
        tags=["code", "injection", "rce"],
    ),
    SecurityRule(
        id="SAST-JS-020",
        name="Hardcoded Secret",
        severity=Severity.HIGH,
        cwe_id="CWE-798",
        language=Language.JAVASCRIPT,
        pattern=r'(?:password|secret|api_key|apikey|token|auth)\s*[:=]\s*["\'][^"\']{4,}["\']',
        description="Credential or secret hardcoded in source code.",
        remediation="Use environment variables (process.env) or a secrets manager.",
        confidence=0.70,
        owasp_category="API2",
        tags=["secrets", "credential"],
    ),
    SecurityRule(
        id="SAST-JS-021",
        name="Hardcoded AWS Key",
        severity=Severity.CRITICAL,
        cwe_id="CWE-798",
        language=Language.JAVASCRIPT,
        pattern=r'(?:AKIA|ASIA)[A-Z0-9]{16}',
        description="AWS access key ID detected in source code.",
        remediation="Rotate the key immediately. Use IAM roles or environment variables.",
        confidence=0.95,
        tags=["secrets", "aws"],
    ),
    SecurityRule(
        id="SAST-JS-030",
        name="XSS via innerHTML",
        severity=Severity.HIGH,
        cwe_id="CWE-79",
        language=Language.JAVASCRIPT,
        pattern=r'(?:innerHTML|outerHTML)\s*=\s*(?!["\'])(?!.*(?:textContent|innerText))',
        description="Setting innerHTML with dynamic content can lead to Cross-Site Scripting (XSS).",
        remediation="Use textContent, innerText, or a sanitization library (DOMPurify).",
        confidence=0.75,
        owasp_category="API8",
        tags=["xss", "dom"],
    ),
    SecurityRule(
        id="SAST-JS-031",
        name="XSS via document.write",
        severity=Severity.HIGH,
        cwe_id="CWE-79",
        language=Language.JAVASCRIPT,
        pattern=r'document\.write\s*\(',
        description="document.write() with dynamic content can lead to XSS.",
        remediation="Use DOM manipulation methods (createElement, appendChild) or a framework with auto-escaping.",
        confidence=0.70,
        tags=["xss", "dom"],
    ),
    SecurityRule(
        id="SAST-JS-040",
        name="Weak Crypto Algorithm",
        severity=Severity.MEDIUM,
        cwe_id="CWE-327",
        language=Language.JAVASCRIPT,
        pattern=r'(?:createHash|createCipher)\s*\(\s*["\'](?:md5|sha1)["\']',
        description="Weak cryptographic algorithm (MD5/SHA1) in use.",
        remediation="Use SHA-256 or stronger: createHash('sha256')",
        confidence=0.90,
        tags=["crypto", "hash"],
    ),
    SecurityRule(
        id="SAST-JS-050",
        name="Path Traversal",
        severity=Severity.HIGH,
        cwe_id="CWE-22",
        language=Language.JAVASCRIPT,
        pattern=r'(?:readFile|readFileSync|createReadStream)\s*\([^)]*(?:req\.|param|input|query|user)',
        description="File read with user-controlled path may allow path traversal.",
        remediation="Validate and sanitize file paths. Use path.resolve() and verify within allowed directory.",
        confidence=0.70,
        tags=["path", "traversal"],
    ),
    SecurityRule(
        id="SAST-JS-060",
        name="Insecure Cookie Settings",
        severity=Severity.MEDIUM,
        cwe_id="CWE-614",
        language=Language.JAVASCRIPT,
        pattern=r'(?:httpOnly|secure|sameSite)\s*[:=]\s*false',
        description="Insecure cookie configuration (missing httpOnly, secure, or sameSite flags).",
        remediation="Set httpOnly: true, secure: true, sameSite: 'strict' for sensitive cookies.",
        confidence=0.75,
        tags=["cookie", "session"],
    ),
    SecurityRule(
        id="SAST-JS-070",
        name="Regex DoS (ReDoS)",
        severity=Severity.MEDIUM,
        cwe_id="CWE-1333",
        language=Language.JAVASCRIPT,
        pattern=r'new\s+RegExp\s*\([^)]*(?:req\.|param|input|query|user)',
        description="User input used in RegExp constructor may cause ReDoS (Regular Expression Denial of Service).",
        remediation="Validate input length before using in regex, or use a safe regex library.",
        confidence=0.60,
        tags=["dos", "regex"],
    ),
]

# =============================================================================
# JAVA SECURITY RULES
# =============================================================================

JAVA_RULES = [
    SecurityRule(
        id="SAST-JV-001",
        name="SQL Injection via String Concatenation",
        severity=Severity.CRITICAL,
        cwe_id="CWE-89",
        language=Language.JAVA,
        pattern=r'(?:Statement|executeQuery|executeUpdate)\s*\([^)]*\+\s*(?:req\.|input|param|user|request)',
        description="SQL query constructed via string concatenation allows SQL injection.",
        remediation="Use PreparedStatement with parameterized queries: ps.setString(1, userInput)",
        confidence=0.85,
        owasp_category="API8",
        tags=["sql", "injection"],
    ),
    SecurityRule(
        id="SAST-JV-002",
        name="SQL Injection via String.format",
        severity=Severity.CRITICAL,
        cwe_id="CWE-89",
        language=Language.JAVA,
        pattern=r'(?:Statement|executeQuery|executeUpdate)\s*\(\s*String\.format\s*\(',
        description="SQL query constructed using String.format allows SQL injection.",
        remediation="Use PreparedStatement with parameterized queries.",
        confidence=0.80,
        tags=["sql", "injection"],
    ),
    SecurityRule(
        id="SAST-JV-010",
        name="Command Injection via Runtime.exec",
        severity=Severity.CRITICAL,
        cwe_id="CWE-78",
        language=Language.JAVA,
        pattern=r'(?:Runtime\.getRuntime\(\)\.exec|ProcessBuilder)\s*\([^)]*(?:req\.|input|param|user|request)',
        description="OS command constructed from user input allows command injection.",
        remediation="Validate and sanitize inputs. Use ProcessBuilder with argument arrays.",
        confidence=0.80,
        tags=["command", "injection"],
    ),
    SecurityRule(
        id="SAST-JV-020",
        name="Hardcoded Password",
        severity=Severity.HIGH,
        cwe_id="CWE-798",
        language=Language.JAVA,
        pattern=r'(?:password|passwd|secret|api_key|apikey|token)\s*=\s*"[^"]{4,}"',
        description="Credential or secret hardcoded in source code.",
        remediation="Use environment variables, JNDI, or a secrets vault.",
        confidence=0.70,
        owasp_category="API2",
        tags=["secrets", "credential"],
    ),
    SecurityRule(
        id="SAST-JV-021",
        name="Hardcoded AWS Key",
        severity=Severity.CRITICAL,
        cwe_id="CWE-798",
        language=Language.JAVA,
        pattern=r'(?:AKIA|ASIA)[A-Z0-9]{16}',
        description="AWS access key ID detected in source code.",
        remediation="Rotate the key immediately. Use IAM roles.",
        confidence=0.95,
        tags=["secrets", "aws"],
    ),
    SecurityRule(
        id="SAST-JV-030",
        name="Unsafe Deserialization",
        severity=Severity.CRITICAL,
        cwe_id="CWE-502",
        language=Language.JAVA,
        pattern=r'ObjectInputStream\s*\([^)]*\)\.readObject\s*\(',
        description="Deserializing untrusted data with Java ObjectInputStream can lead to remote code execution.",
        remediation="Use safe serialization (JSON, Protocol Buffers). Avoid ObjectInputStream with untrusted data.",
        confidence=0.90,
        tags=["deserialization", "rce"],
    ),
    SecurityRule(
        id="SAST-JV-040",
        name="Weak Cryptographic Algorithm",
        severity=Severity.MEDIUM,
        cwe_id="CWE-327",
        language=Language.JAVA,
        pattern=r'(?:MessageDigest\.getInstance|Cipher\.getInstance)\s*\(\s*"(?:MD5|SHA-1?)[^"]*"\s*\)',
        description="Weak cryptographic algorithm (MD5/SHA1) in use.",
        remediation="Use SHA-256 or stronger: MessageDigest.getInstance(\"SHA-256\")",
        confidence=0.90,
        tags=["crypto", "hash"],
    ),
    SecurityRule(
        id="SAST-JV-050",
        name="XSS via getParameter",
        severity=Severity.HIGH,
        cwe_id="CWE-79",
        language=Language.JAVA,
        pattern=r'(?:request\.getParameter|req\.getParam)\s*\([^)]*\).*(?:println|print|write|innerHTML)',
        description="User input reflected in response without encoding may cause XSS.",
        remediation="Encode all user input before rendering: OWASP Java Encoder.",
        confidence=0.70,
        tags=["xss"],
    ),
    SecurityRule(
        id="SAST-JV-060",
        name="LDAP Injection",
        severity=Severity.HIGH,
        cwe_id="CWE-90",
        language=Language.JAVA,
        pattern=r'(?:DirContext|LdapContext)\s*\([^)]*(?:req\.|input|param|user)',
        description="User input in LDAP query may allow LDAP injection.",
        remediation="Validate and escape LDAP special characters. Use parameterized LDAP searches.",
        confidence=0.70,
        tags=["ldap", "injection"],
    ),
    SecurityRule(
        id="SAST-JV-070",
        name="XXE Vulnerability",
        severity=Severity.HIGH,
        cwe_id="CWE-611",
        language=Language.JAVA,
        pattern=r'(?:DocumentBuilderFactory|SAXParser|XMLReader|TransformerFactory)\s*(?:\.newInstance)?\s*\(',
        description="XML parser without disabling external entities may be vulnerable to XXE attacks.",
        remediation="Disable external entities: factory.setFeature(\"http://apache.org/xml/features/disallow-doctype-decl\", true)",
        confidence=0.60,
        tags=["xxe", "xml"],
    ),
]

# =============================================================================
# COMBINED RULE SET
# =============================================================================

ALL_RULES = PYTHON_RULES + JAVASCRIPT_RULES + JAVA_RULES

# Index rules by language for fast lookup
RULES_BY_LANGUAGE = {
    Language.PYTHON: PYTHON_RULES,
    Language.JAVASCRIPT: JAVASCRIPT_RULES,
    Language.JAVA: JAVA_RULES,
}

# File extensions to language mapping
EXTENSION_LANGUAGE_MAP = {
    ".py": Language.PYTHON,
    ".js": Language.JAVASCRIPT,
    ".jsx": Language.JAVASCRIPT,
    ".ts": Language.JAVASCRIPT,
    ".tsx": Language.JAVASCRIPT,
    ".mjs": Language.JAVASCRIPT,
    ".java": Language.JAVA,
}


def get_rules_for_file(filename: str) -> list[SecurityRule]:
    """Return applicable rules based on file extension."""
    import os
    ext = os.path.splitext(filename)[1].lower()
    lang = EXTENSION_LANGUAGE_MAP.get(ext)
    if lang is None:
        return []
    return RULES_BY_LANGUAGE.get(lang, [])


def get_rules_by_severity(severity: Severity) -> list[SecurityRule]:
    """Return all rules matching a given severity."""
    return [r for r in ALL_RULES if r.severity == severity]


def get_rules_by_tag(tag: str) -> list[SecurityRule]:
    """Return all rules matching a given tag."""
    return [r for r in ALL_RULES if tag in r.tags]
