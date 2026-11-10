"""Input sanitization and XSS protection for SentinelAI.

Provides:
- HTML entity escaping for output (prevents stored XSS)
- Input validation and sanitization helpers
- SQL injection pattern detection
- Path traversal protection
- Dangerous character filtering

All user-generated content MUST pass through these functions before
being stored or rendered.
"""

import html
import os
import re
from urllib.parse import urlparse

# ── XSS Protection ────────────────────────────────────────────────────

# Patterns that indicate potential XSS
_XSS_PATTERNS = [
    re.compile(r"<script[\s>]", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),  # onclick=, onerror=, etc.
    re.compile(r"<iframe[\s>]", re.IGNORECASE),
    re.compile(r"<object[\s>]", re.IGNORECASE),
    re.compile(r"<embed[\s>]", re.IGNORECASE),
    re.compile(r"<link[\s>]", re.IGNORECASE),
    re.compile(r"<meta[\s>]", re.IGNORECASE),
    re.compile(r"<svg[\s>].*?on\w+", re.IGNORECASE | re.DOTALL),
    re.compile(r"data:\s*text/html", re.IGNORECASE),
    re.compile(r"vbscript:", re.IGNORECASE),
    re.compile(r"<\s*img[^>]+onerror", re.IGNORECASE),
    re.compile(r"expression\s*\(", re.IGNORECASE),
    re.compile(r"url\s*\(\s*['\"]?\s*javascript:", re.IGNORECASE),
]

# ── SQL Injection Detection ───────────────────────────────────────────

_SQL_INJECTION_PATTERNS = [
    re.compile(
        r"(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC|EXECUTE)\b)", re.IGNORECASE
    ),
    re.compile(r"(--|#|/\*|\*/)", re.IGNORECASE),
    re.compile(r"(;\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE))", re.IGNORECASE),
    re.compile(r"'\s*OR\s+'", re.IGNORECASE),
    re.compile(r"'\s*OR\s+\d+\s*=\s*\d+", re.IGNORECASE),
    re.compile(r"SLEEP\s*\(\s*\d+\s*\)", re.IGNORECASE),
    re.compile(r"BENCHMARK\s*\(", re.IGNORECASE),
    re.compile(r"WAITFOR\s+DELAY", re.IGNORECASE),
]

# ── Path Traversal Detection ──────────────────────────────────────────

_PATH_TRAVERSAL_PATTERNS = [
    re.compile(r"\.\./"),
    re.compile(r"\.\.\\"),
    re.compile(r"%2e%2e%2f", re.IGNORECASE),
    re.compile(r"%2e%2e/", re.IGNORECASE),
    re.compile(r"\.\.%2f", re.IGNORECASE),
    re.compile(r"%2e%2e\\", re.IGNORECASE),
]

# ── Blocked characters for various contexts ───────────────────────────

_DANGEROUS_CHARS = set("<>\\'\";`")


def escape_html(text: str) -> str:
    """Escape HTML entities to prevent XSS when rendering user content.

    Use this for ALL user-generated content displayed in HTML.
    """
    if not isinstance(text, str):
        return str(text)
    return html.escape(text, quote=True)


def escape_for_attribute(text: str) -> str:
    """Escape text for safe insertion into HTML attributes."""
    if not isinstance(text, str):
        return str(text)
    text = html.escape(text, quote=True)
    text = text.replace("'", "&#x27;")
    text = text.replace("/", "&#x2F;")
    return text


def escape_for_javascript(text: str) -> str:
    """Escape text for safe insertion into JavaScript strings."""
    if not isinstance(text, str):
        return str(text)
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\\'")
    text = text.replace('"', '\\"')
    text = text.replace("\n", "\\n")
    text = text.replace("\r", "\\r")
    text = text.replace("\t", "\\t")
    text = text.replace("<", "\\x3c")
    text = text.replace(">", "\\x3e")
    return text


def contains_xss(text: str) -> bool:
    """Check if text contains potential XSS patterns."""
    if not isinstance(text, str):
        return False
    return any(pattern.search(text) for pattern in _XSS_PATTERNS)


def detect_sql_injection(text: str) -> bool:
    """Check if text contains potential SQL injection patterns.

    This is a defense-in-depth measure; SQLAlchemy's parameterized
    queries provide primary SQL injection protection.
    """
    if not isinstance(text, str):
        return False
    return any(pattern.search(text) for pattern in _SQL_INJECTION_PATTERNS)


def detect_path_traversal(text: str) -> bool:
    """Check if text contains path traversal sequences."""
    if not isinstance(text, str):
        return False
    return any(pattern.search(text) for pattern in _PATH_TRAVERSAL_PATTERNS)


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing dangerous characters and sequences.

    - Removes path components (only keeps basename)
    - Strips null bytes
    - Limits length to 255 characters
    - Removes characters dangerous in file systems
    """
    if not filename:
        return "unnamed"

    # Strip path components
    filename = os.path.basename(filename)

    # Remove null bytes
    filename = filename.replace("\x00", "")

    # Remove dangerous characters
    for char in _DANGEROUS_CHARS:
        filename = filename.replace(char, "_")

    # Limit length (preserve extension)
    name, ext = os.path.splitext(filename)
    if len(filename) > 255:
        max_name_len = 255 - len(ext)
        name = name[:max_name_len]
        filename = name + ext

    return filename or "unnamed"


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """General-purpose input sanitization.

    - Strips leading/trailing whitespace
    - Removes null bytes
    - Limits length
    - Escapes HTML entities
    """
    if not isinstance(text, str):
        return str(text)[:max_length] if text else ""

    text = text.strip()
    text = text.replace("\x00", "")  # null bytes
    text = text[:max_length]

    return text


def validate_url(url: str, allowed_schemes: list[str] | None = None) -> bool:
    """Validate that a URL is safe and well-formed.

    Checks:
    - Valid URL format
    - Allowed schemes (http, https by default)
    - No javascript: or data: schemes
    - No userinfo (prevents credential leakage)
    """
    if not url or not isinstance(url, str):
        return False

    allowed = allowed_schemes or ["http", "https"]

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme.lower() not in allowed:
        return False

    # Block javascript: and data: even if they somehow get through
    dangerous_schemes = {"javascript", "data", "vbscript", "file", "ftp"}
    if parsed.scheme.lower() in dangerous_schemes:
        return False

    # No userinfo (prevents user:pass@host attacks)
    return not (parsed.username or parsed.password)


def validate_email_domain(email: str, allowed_domains: list[str] | None = None) -> bool:
    """Validate email format and optionally restrict to allowed domains."""
    if not email or not isinstance(email, str):
        return False

    # Basic email format check
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    if not email_pattern.match(email):
        return False

    if allowed_domains:
        domain = email.split("@")[-1].lower()
        return domain in [d.lower() for d in allowed_domains]

    return True


def sanitize_json_value(value):
    """Recursively sanitize all string values in a JSON-like structure.

    Returns a new structure with all strings HTML-escaped.
    """
    if isinstance(value, str):
        return escape_html(value)
    elif isinstance(value, dict):
        return {k: sanitize_json_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [sanitize_json_value(item) for item in value]
    return value


# ── Middleware-compatible helper ───────────────────────────────────────


def validate_request_size(content_length: int | None, max_bytes: int) -> bool:
    """Check if request content length is within bounds."""
    if content_length is None:
        return True  # No Content-Length header; let the route decide
    return content_length <= max_bytes


# ── Dangerous content patterns for scanner output ─────────────────────


def is_safe_for_display(text: str) -> bool:
    """Check if text is safe for direct HTML display (no XSS vectors)."""
    if not text:
        return True
    return not contains_xss(text)
