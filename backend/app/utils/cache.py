"""General-purpose caching layer with Redis + in-memory fallback.

Provides a simple key-value cache for expensive queries like dashboard stats,
analytics, and aggregate metrics. Falls back to a thread-safe in-memory LRU
cache when Redis is unavailable (dev, tests, single-server deployments).

Usage::

    from app.utils.cache import cache

    @cache.ttl("dashboard:{user_id}", ttl=60)
    def get_dashboard(user_id: int) -> dict: ...

    # Or manually:
    cache.set("dash:42", data, ttl=120)
    data = cache.get("dash:42")
    cache.invalidate("dash:42")
    cache.invalidate_prefix("dash:")
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

_REDIS_URL: str | None = None
_redis_client: Any = None  # redis.Redis or None
_mem_store: dict[str, tuple[Any, float]] = {}
_mem_lock = threading.Lock()
_MEM_MAX = 5000  # max entries in memory fallback


def _get_redis():
    """Lazy-initialise a Redis connection, return None on failure."""
    global _redis_client, _REDIS_URL
    try:
        from app.config import get_settings

        settings = get_settings()
        redis_url = getattr(settings, "REDIS_URL", None)
        if not redis_url:
            # Try common env var
            import os

            redis_url = os.environ.get("REDIS_URL") or os.environ.get("SENTINEL_REDIS_URL")

        if not redis_url:
            return None

        if redis_url == _REDIS_URL and _redis_client is not None:
            return _redis_client

        import redis

        _redis_client = redis.from_url(redis_url, decode_responses=True, socket_timeout=2)
        _redis_client.ping()
        _REDIS_URL = redis_url
        logger.info("Redis cache connected: %s", redis_url)
        return _redis_client
    except Exception:
        logger.debug("Redis unavailable, using in-memory cache", exc_info=True)
        _redis_client = None
        return None


def _prefix_key(key: str) -> str:
    return f"sentinelai:cache:{key}"


class Cache:
    """Simple cache interface with Redis primary and in-memory fallback."""

    # ------------------------------------------------------------------ #
    # Core get / set / delete
    # ------------------------------------------------------------------ #

    def get(self, key: str) -> Any | None:
        r = _get_redis()
        prefix = _prefix_key(key)
        if r is not None:
            try:
                raw = r.get(prefix)
                if raw is not None:
                    return json.loads(raw)
                return None
            except Exception:
                logger.debug("Redis GET failed for %s", key, exc_info=True)
        # Memory fallback
        with _mem_lock:
            entry = _mem_store.get(prefix)
            if entry is None:
                return None
            value, expires = entry
            if expires < time.time():
                del _mem_store[prefix]
                return None
            return value

    def set(self, key: str, value: Any, ttl: int = 60) -> None:
        r = _get_redis()
        prefix = _prefix_key(key)
        serialized = json.dumps(value, default=str)
        if r is not None:
            try:
                r.setex(prefix, ttl, serialized)
                return
            except Exception:
                logger.debug("Redis SET failed for %s", key, exc_info=True)
        # Memory fallback
        with _mem_lock:
            if len(_mem_store) >= _MEM_MAX:
                self._evict_oldest()
            _mem_store[prefix] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        r = _get_redis()
        prefix = _prefix_key(key)
        if r is not None:
            try:
                r.delete(prefix)
            except Exception:
                logger.debug("Redis DELETE failed for %s", key, exc_info=True)
        with _mem_lock:
            _mem_store.pop(prefix, None)

    def invalidate_prefix(self, prefix: str) -> int:
        """Delete all keys starting with *prefix*. Returns count deleted."""
        full_prefix = _prefix_key(prefix)
        count = 0
        r = _get_redis()
        if r is not None:
            try:
                keys = list(r.scan_iter(match=f"{full_prefix}*", count=200))
                if keys:
                    count = r.delete(*keys)
            except Exception:
                logger.debug("Redis invalidate_prefix failed", exc_info=True)
        with _mem_lock:
            to_delete = [k for k in _mem_store if k.startswith(full_prefix)]
            count += len(to_delete)
            for k in to_delete:
                del _mem_store[k]
        return count

    # ------------------------------------------------------------------ #
    # Decorator
    # ------------------------------------------------------------------ #

    def ttl(self, key_pattern: str, ttl: int = 60) -> Callable:
        """Cache a function's return value.

        *key_pattern* may contain ``{arg}`` placeholders matching positional /
        keyword arguments.  Example::

            @cache.ttl("dash:{user_id}", ttl=60)
            def get_dashboard(user_id): ...
        """

        def decorator(fn: Callable) -> Callable:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                import inspect

                bound = inspect.signature(fn).bind(*args, **kwargs)
                bound.apply_defaults()
                try:
                    cache_key = key_pattern.format(**bound.arguments)
                except (KeyError, IndexError):
                    # Can't build key → skip cache
                    return fn(*args, **kwargs)

                cached = self.get(cache_key)
                if cached is not None:
                    return cached

                result = fn(*args, **kwargs)
                self.set(cache_key, result, ttl=ttl)
                return result

            wrapper.__name__ = fn.__name__
            wrapper.__doc__ = fn.__doc__
            return wrapper

        return decorator

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _evict_oldest(self) -> None:
        """Remove the 20% oldest entries from the in-memory store."""
        if not _mem_store:
            return
        entries = sorted(_mem_store.items(), key=lambda kv: kv[1][1])
        evict_count = max(1, len(entries) // 5)
        for key, _ in entries[:evict_count]:
            _mem_store.pop(key, None)


# Module-level singleton
cache = Cache()
