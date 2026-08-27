"""Tests for the in-memory cache layer (Redis fallback).

These tests exercise the Cache class directly without requiring Redis.
"""

import time

from app.utils.cache import Cache


class TestCacheGetSet:
    """Basic get / set / delete operations."""

    def test_set_and_get(self):
        c = Cache()
        c.set("k1", {"a": 1}, ttl=60)
        assert c.get("k1") == {"a": 1}

    def test_get_missing_key_returns_none(self):
        c = Cache()
        assert c.get("nonexistent") is None

    def test_set_overwrites(self):
        c = Cache()
        c.set("k", "old", ttl=60)
        c.set("k", "new", ttl=60)
        assert c.get("k") == "new"

    def test_delete_removes_key(self):
        c = Cache()
        c.set("k", "v", ttl=60)
        c.delete("k")
        assert c.get("k") is None

    def test_delete_missing_key_no_error(self):
        c = Cache()
        c.delete("nope")  # Should not raise

    def test_ttl_expiry(self):
        c = Cache()
        c.set("expire_me", "value", ttl=1)
        assert c.get("expire_me") == "value"
        time.sleep(1.1)
        assert c.get("expire_me") is None

    def test_different_keys_independent(self):
        c = Cache()
        c.set("a", 1, ttl=60)
        c.set("b", 2, ttl=60)
        assert c.get("a") == 1
        assert c.get("b") == 2


class TestCacheInvalidation:
    """Prefix-based invalidation."""

    def test_invalidate_prefix(self):
        c = Cache()
        c.set("dash:1", "a", ttl=60)
        c.set("dash:2", "b", ttl=60)
        c.set("other:1", "c", ttl=60)
        deleted = c.invalidate_prefix("dash:")
        assert deleted == 2
        assert c.get("dash:1") is None
        assert c.get("dash:2") is None
        assert c.get("other:1") == "c"

    def test_invalidate_prefix_no_match(self):
        c = Cache()
        c.set("a:1", "x", ttl=60)
        deleted = c.invalidate_prefix("zzz:")
        assert deleted == 0
        assert c.get("a:1") == "x"


class TestCacheDecorator:
    """@cache.ttl decorator."""

    def test_decorator_caches_result(self):
        c = Cache()
        call_count = 0

        @c.ttl("fn:{x}", ttl=60)
        def fn(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert fn(5) == 10
        assert fn(5) == 10  # Should be cached
        assert call_count == 1

    def test_decorator_different_args_separate_keys(self):
        c = Cache()
        calls = []

        @c.ttl("g:{a}:{b}", ttl=60)
        def g(a, b):
            calls.append((a, b))
            return a + b

        assert g(1, 2) == 3
        assert g(3, 4) == 7
        assert len(calls) == 2

    def test_decorator_none_return_not_cached(self):
        c = Cache()
        calls = []

        @c.ttl("h:{v}", ttl=60)
        def h(v):
            calls.append(v)
            return None

        h("x")
        h("x")
        assert len(calls) == 2  # None results are not cached by design
