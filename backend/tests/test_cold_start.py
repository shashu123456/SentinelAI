"""Cold start must never block on an unreachable Redis.

Regression tests for the defect where ``TokenBlacklist`` connected to Redis in
``__init__`` while being constructed by a module-level singleton, so every
process that imported ``app.main`` paid a TCP connect + retry timeout (~20s on
Windows) whenever Redis was unreachable.

The black-hole address below is non-routable, so a TCP connect can only end in a
timeout. Neither test sleeps: elapsed time is measured with perf_counter.
"""

import importlib
import sys
import time

BLACKHOLE = "redis://10.255.255.1:6379/0"


def _reimport(monkeypatch, *modules):
    monkeypatch.setenv("REDIS_URL", BLACKHOLE)
    for name in list(sys.modules):
        if any(name == m or name.startswith(m + ".") for m in modules):
            del sys.modules[name]


def test_blacklist_module_import_does_not_connect(monkeypatch):
    """Importing the module must not perform network I/O."""
    _reimport(monkeypatch, "app.utils.token_blacklist")

    start = time.perf_counter()
    mod = importlib.import_module("app.utils.token_blacklist")
    elapsed = time.perf_counter() - start

    # Singleton exists but has not tried to reach Redis yet.
    assert mod.blacklist._backend == "uninitialized"
    assert elapsed < 2.0, f"import took {elapsed:.2f}s; it must not touch the network"


def test_app_main_import_not_blocked_by_blackhole_redis(monkeypatch):
    """Re-importing app.main must not pay a Redis timeout.

    This measures the *incremental* import of app.main after its dependency
    graph is warm. A cold first import of app.main costs ~16-17s in this
    repository purely from module loading (measured with -X importtime), which
    is unrelated to Redis and is not what this test asserts. What must hold is
    that an unreachable Redis adds no measurable time: before the fix, this same
    import stalled for an extra ~20s inside client.ping().
    """
    _reimport(monkeypatch, "app.utils.token_blacklist", "app.main")
    importlib.import_module("app.main")  # warm the dependency graph

    _reimport(monkeypatch, "app.utils.token_blacklist", "app.main")
    start = time.perf_counter()
    mod = importlib.import_module("app.main")
    elapsed = time.perf_counter() - start

    assert mod.app is not None
    assert elapsed < 2.0, f"warm re-import of app.main took {elapsed:.2f}s"


def test_first_use_falls_back_to_memory_quickly(monkeypatch):
    """First use pays at most the bounded connect timeout, then falls back."""
    _reimport(monkeypatch, "app.utils.token_blacklist")
    mod = importlib.import_module("app.utils.token_blacklist")

    client = mod.TokenBlacklist()
    start = time.perf_counter()
    client.add("jti-cold-start", time.time() + 60)
    elapsed = time.perf_counter() - start

    assert client._backend == "memory"
    assert client.is_blacklisted("jti-cold-start") is True
    # 0.5s connect timeout plus redis-py retries; must stay well under a cold
    # start budget and far below the ~20s this used to cost.
    assert elapsed < 5.0, f"first use took {elapsed:.2f}s"
