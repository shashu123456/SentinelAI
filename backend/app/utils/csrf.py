"""CSRF protection for cookie-based operations.

The refresh token is stored in an HttpOnly cookie, which means JavaScript
can't read it. However, the browser automatically sends cookies on requests,
making them vulnerable to CSRF attacks.

Solution: Pair the refresh cookie with a CSRF token in a separate non-HttpOnly
cookie. The frontend reads the CSRF token and sends it in a header. The backend
validates that the header matches the cookie value.
"""

import hashlib
import hmac
import secrets


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(32)


def hash_csrf_token(token: str, secret: str) -> str:
    """Create an HMAC signature of the CSRF token for cookie storage."""
    return hmac.new(
        secret.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def validate_csrf_token(token: str, signature: str, secret: str) -> bool:
    """Validate that the CSRF token matches its signature."""
    if not token or not signature:
        return False
    expected = hash_csrf_token(token, secret)
    return hmac.compare_digest(expected, signature)
