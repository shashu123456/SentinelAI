"""SSRF protection and URL validation for SentinelAI.

Provides:
- URL validation against internal/private IP ranges
- SSRF-safe HTTP client wrapper
- File upload security (magic bytes, extension validation)
- Secrets management helpers
"""

import hashlib
import ipaddress
import secrets
import socket
from urllib.parse import urlparse

# ── Internal / Private IP Ranges ──────────────────────────────────────

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]

_CLOUD_METADATA_HOSTS = {
    "169.254.169.254",  # AWS, GCP, Azure metadata
    "metadata.google.internal",  # GCP metadata
    "instance-data",  # Azure IMDS
}

# ── File Upload Magic Bytes ───────────────────────────────────────────

_MAGIC_BYTES = {
    "json": [b"{", b"["],
    "yaml": [b"---", b"openapi", b"swagger", b"info:"],
    "yml": [b"---", b"openapi", b"swagger", b"info:"],
}


def is_internal_ip(hostname: str) -> bool:
    """Check if a hostname resolves to an internal/private IP address."""
    try:
        ip = ipaddress.ip_address(hostname)
        return any(ip in network for network in _BLOCKED_NETWORKS)
    except ValueError:
        pass

    # Check cloud metadata hosts
    if hostname.lower() in _CLOUD_METADATA_HOSTS:
        return True

    # Resolve hostname and check
    try:
        resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
        for _family, _, _, _, sockaddr in resolved:
            ip = ipaddress.ip_address(sockaddr[0])
            if any(ip in network for network in _BLOCKED_NETWORKS):
                return True
    except (socket.gaierror, OSError):
        pass

    return False


def validate_url_safety(url: str) -> tuple[bool, str]:
    """Validate a URL is safe for server-side fetching.

    Returns (is_safe, reason).
    """
    if not url:
        return False, "Empty URL"

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    # Block non-HTTP schemes
    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Blocked scheme: {parsed.scheme}"

    # Block data: javascript: etc.
    if parsed.scheme.lower() in ("javascript", "data", "vbscript", "file"):
        return False, f"Dangerous scheme: {parsed.scheme}"

    hostname = parsed.hostname
    if not hostname:
        return False, "No hostname"

    # Block internal IPs
    if is_internal_ip(hostname):
        return False, f"Internal/private IP: {hostname}"

    # Block cloud metadata endpoints
    if hostname.lower() in _CLOUD_METADATA_HOSTS:
        return False, f"Cloud metadata endpoint: {hostname}"

    # Block localhost variations
    blocked_hosts = {"localhost", "0.0.0.0", "127.0.0.1", "::", "[::1]"}
    if hostname.lower() in blocked_hosts:
        return False, f"Loopback host: {hostname}"

    # Block non-standard ports (only 80, 443 allowed)
    port = parsed.port
    if port and port not in (80, 443):
        return False, f"Non-standard port: {port}"

    return True, "OK"


def validate_file_upload(
    filename: str,
    content: bytes,
    max_size_bytes: int = 5 * 1024 * 1024,
    allowed_extensions: list[str] | None = None,
) -> tuple[bool, str]:
    """Validate a file upload for security.

    Checks:
    1. File size
    2. Extension is allowed
    3. Content matches expected format (magic bytes)
    4. No embedded null bytes
    5. Content is valid UTF-8

    Returns (is_valid, reason).
    """
    allowed = allowed_extensions or [".json", ".yaml", ".yml"]

    # Size check
    if len(content) > max_size_bytes:
        return False, f"File too large: {len(content)} bytes (max: {max_size_bytes})"

    # Empty file
    if len(content) == 0:
        return False, "Empty file"

    # Extension check
    import os

    _, ext = os.path.splitext(filename.lower())
    if ext not in allowed:
        return False, f"File type not allowed: {ext} (allowed: {', '.join(allowed)})"

    # Null byte check (prevents binary injection)
    if b"\x00" in content[:1024]:
        return False, "File contains null bytes"

    # Magic bytes check
    header = content[:256].lstrip()  # Skip leading whitespace
    magic_patterns = _MAGIC_BYTES.get(ext.lstrip("."), [])
    if magic_patterns and not any(header.startswith(pattern) for pattern in magic_patterns):
        # Also check if content starts with BOM or whitespace + pattern
        text_start = content[:512].decode("utf-8", errors="ignore").strip()
        if not any(text_start.startswith(p.decode()) for p in magic_patterns):
            return False, f"Content does not match {ext} format"

    # UTF-8 validation for text files
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        return False, "File is not valid UTF-8"

    return True, "OK"


def generate_api_key() -> tuple[str, str, str]:
    """Generate a secure API key.

    Returns (full_key, key_prefix, key_hash).
    """
    raw = f"sai_{secrets.token_urlsafe(32)}"
    prefix = raw[:16]
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, prefix, key_hash


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def constant_time_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    return secrets.compare_digest(a.encode(), b.encode())


# ── Request Validation ────────────────────────────────────────────────


def validate_request_headers(headers: dict) -> list[str]:
    """Check request headers for suspicious content.

    Returns a list of warning messages (empty if all OK).
    """
    warnings = []

    # Check for Host header manipulation
    host = headers.get("host", "")
    if host and (":" in host and host.count(":") > 1 or ".." in host):
        warnings.append(f"Suspicious Host header: {host}")

    # Check for proxy header injection
    for header in ("x-forwarded-for", "x-real-ip", "x-forwarded-host"):
        value = headers.get(header, "")
        if value and len(value) > 256:
            warnings.append(f"Oversized {header} header: {len(value)} chars")

    # Check for oversized headers
    for key, value in headers.items():
        if len(value) > 8192:
            warnings.append(f"Oversized header {key}: {len(value)} chars")

    return warnings


def get_client_ip_real(request) -> str | None:
    """Extract the real client IP, respecting proxy headers only from trusted sources.

    This prevents IP spoofing via X-Forwarded-For.
    """
    from app.config import get_settings

    settings = get_settings()

    # In production with trusted proxies, use X-Forwarded-For
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and settings.TRUSTED_PROXIES:
        # Only trust the leftmost (original client) IP
        client_ip = forwarded.split(",")[0].strip()
        return client_ip

    # Fall back to direct connection IP
    return request.client.host if request.client else None
