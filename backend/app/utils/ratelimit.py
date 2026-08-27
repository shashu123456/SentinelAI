from slowapi import Limiter
from slowapi.util import get_remote_address


def get_rate_limit_key(request):
    """Rate limit key: use user ID if authenticated, otherwise IP address.

    This ensures:
    - Authenticated users are rate-limited per account (not per IP)
    - Unauthenticated users are rate-limited per IP
    - Users behind shared IPs (NAT, VPN) get fair limits
    """
    # Try to get user from request state (set by auth middleware)
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"
    return get_remote_address(request)


limiter = Limiter(key_func=get_rate_limit_key)
