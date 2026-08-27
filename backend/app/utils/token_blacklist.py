"""Token blacklist for JWT revocation.

Uses Redis in production with an in-memory fallback for development/testing.
Every access token gets a JTI (JWT ID) claim. When a token needs to be revoked
(e.g., on logout), its JTI is added to the blacklist with a TTL matching the
token's remaining lifetime.
"""

import os
import time
import threading

from app.utils.logger import logger


class TokenBlacklist:
    """Thread-safe token blacklist with Redis backend and in-memory fallback."""

    def __init__(self):
        self._redis_client = None
        self._memory_store: dict[str, float] = {}  # jti -> expiry_timestamp
        self._lock = threading.Lock()
        self._backend: str = "memory"
        self._initialize_backend()

    def _initialize_backend(self):
        """Try to connect to Redis; fall back to in-memory store."""
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        try:
            import redis

            client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
            client.ping()
            self._redis_client = client
            self._backend = "redis"
            logger.info("Token blacklist: using Redis backend")
        except Exception:
            self._backend = "memory"
            logger.warning(
                "Token blacklist: Redis unavailable, using in-memory store. "
                "Token revocation will not survive server restarts."
            )

    def add(self, jti: str, expires_at: float) -> None:
        """Add a JTI to the blacklist until its expiry time."""
        if self._backend == "redis":
            ttl = max(int(expires_at - time.time()), 1)
            try:
                self._redis_client.setex(f"bl:{jti}", ttl, "1")
            except Exception as e:
                logger.error(f"Failed to blacklist token in Redis: {e}")
                # Fall back to memory for this operation
                with self._lock:
                    self._memory_store[jti] = expires_at
        else:
            with self._lock:
                self._memory_store[jti] = expires_at

    def is_blacklisted(self, jti: str) -> bool:
        """Check if a JTI is in the blacklist."""
        if self._backend == "redis":
            try:
                return self._redis_client.exists(f"bl:{jti}") > 0
            except Exception as e:
                logger.error(f"Failed to check blacklist in Redis: {e}")
                # Fall back to memory check
                with self._lock:
                    return jti in self._memory_store
        else:
            with self._lock:
                if jti in self._memory_store:
                    # Check if expired
                    if self._memory_store[jti] < time.time():
                        del self._memory_store[jti]
                        return False
                    return True
                return False

    def revoke_all_for_user(self, user_id: int) -> int:
        """Revoke all tokens for a user. Returns count of revoked tokens.

        In Redis, we store a user-level revocation timestamp. Any token
        issued before this timestamp is considered revoked.
        """
        if self._backend == "redis":
            try:
                key = f"bl:user:{user_id}"
                self._redis_client.setex(key, 86400 * 7, str(time.time()))
                return 1
            except Exception as e:
                logger.error(f"Failed to revoke all tokens in Redis: {e}")
                return 0
        else:
            # In-memory: we can't revoke all without iterating, so we use a version
            with self._lock:
                self._memory_store[f"user_rev:{user_id}"] = time.time()
            return 1

    def is_user_revoked(self, user_id: int, issued_at: float) -> bool:
        """Check if all tokens for a user have been revoked after issued_at."""
        if self._backend == "redis":
            try:
                key = f"bl:user:{user_id}"
                revocation_time = self._redis_client.get(key)
                if revocation_time and float(revocation_time) > issued_at:
                    return True
                return False
            except Exception:
                return False
        else:
            with self._lock:
                revocation_time = self._memory_store.get(f"user_rev:{user_id}")
                if revocation_time and revocation_time > issued_at:
                    return True
                return False

    def cleanup(self) -> int:
        """Remove expired entries from in-memory store. Returns count removed."""
        if self._backend != "memory":
            return 0
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._memory_store.items() if v < now]
            for k in expired:
                del self._memory_store[k]
            return len(expired)


# Singleton instance
blacklist = TokenBlacklist()
