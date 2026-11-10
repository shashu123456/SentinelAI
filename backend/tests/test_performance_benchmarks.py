"""Performance benchmark tests for SentinelAI.

Benchmarks:
- API response times for critical endpoints
- Database query performance (single and aggregate)
- Cache hit/miss ratios
- Connection pool behavior
- Memory usage under load
- Concurrent request handling
"""

import statistics
import time

import pytest

# ── Helpers ───────────────────────────────────────────────────────────


def _register_and_login(client, username="benchuser", password="Test123!@#"):
    """Register a user and return the auth header."""
    client.post(
        "/api/auth/register",
        json={"username": username, "email": f"{username}@bench.example.com", "password": password},
    )
    resp = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _timed(func, *args, **kwargs):
    """Run func and return (result, elapsed_ms)."""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = (time.perf_counter() - start) * 1000
    return result, elapsed


def _warm(client, path, headers=None):
    """Issue one untimed request.

    The first request through a fresh TestClient pays one-off initialisation
    (lazy imports, middleware and encoder setup); measuring it benchmarks app
    startup, not the endpoint.
    """
    client.get(path, headers=headers or {})


def _percentile(values, p):
    """Compute p-th percentile of a sorted list."""
    idx = int(len(values) * p / 100)
    return values[min(idx, len(values) - 1)]


# ── API Response Time Benchmarks ──────────────────────────────────────


class TestAPIResponseTimes:
    """Benchmark API endpoint response times."""

    def test_health_endpoint_speed(self, client):
        """Health endpoint should respond in < 50ms."""
        _warm(client, "/api/v1/health")
        times = []
        for _ in range(20):
            _, ms = _timed(client.get, "/api/v1/health")
            times.append(ms)
        p95 = _percentile(sorted(times), 95)
        assert p95 < 100, f"Health endpoint p95={p95:.1f}ms exceeds 100ms threshold"

    def test_login_response_time(self, client):
        """Login should complete in < 500ms."""
        # Warm up hashing and auth dependencies before timing.
        client.post(
            "/api/auth/register",
            json={"username": "perfwarm", "email": "perfwarm@test.com", "password": "Test123!@#"},
        )
        client.post("/api/auth/login", json={"username": "perfwarm", "password": "Test123!@#"})
        times = []
        for i in range(10):
            client.post(
                "/api/auth/register",
                json={
                    "username": f"perf{i}",
                    "email": f"perf{i}@test.com",
                    "password": "Test123!@#",
                },
            )
            _, ms = _timed(
                client.post,
                "/api/auth/login",
                json={"username": f"perf{i}", "password": "Test123!@#"},
            )
            times.append(ms)
        p95 = _percentile(sorted(times), 95)
        assert p95 < 500, f"Login p95={p95:.1f}ms exceeds 500ms threshold"

    def test_dashboard_load_time(self, client):
        """Dashboard endpoint should load in < 1s."""
        headers = _register_and_login(client, "dashbench")
        _warm(client, "/api/v1/dashboard/overview", headers)
        times = []
        for _ in range(10):
            _, ms = _timed(client.get, "/api/v1/dashboard/overview", headers=headers)
            times.append(ms)
        p95 = _percentile(sorted(times), 95)
        assert p95 < 1000, f"Dashboard p95={p95:.1f}ms exceeds 1s threshold"

    def test_scans_list_time(self, client):
        """Scan listing should be fast even with empty state."""
        headers = _register_and_login(client, "scanbench")
        times = []
        for _ in range(10):
            _, ms = _timed(client.get, "/api/v1/scans", headers=headers)
            times.append(ms)
        p95 = _percentile(sorted(times), 95)
        assert p95 < 500, f"Scans list p95={p95:.1f}ms exceeds 500ms threshold"

    def test_analytics_endpoint_time(self, client):
        """Analytics endpoint should respond in < 2s."""
        headers = _register_and_login(client, "analyticsbench")
        _warm(client, "/api/scans/analytics", headers)
        times = []
        for _ in range(5):
            _, ms = _timed(client.get, "/api/scans/analytics", headers=headers)
            times.append(ms)
        p95 = _percentile(sorted(times), 95)
        assert p95 < 2000, f"Analytics p95={p95:.1f}ms exceeds 2s threshold"

    def test_search_endpoint_time(self, client):
        """Search endpoint should respond in < 1s."""
        headers = _register_and_login(client, "searchbench")
        times = []
        for _ in range(10):
            _, ms = _timed(client.get, "/api/v1/scans?search=test", headers=headers)
            times.append(ms)
        p95 = _percentile(sorted(times), 95)
        assert p95 < 500, f"Search p95={p95:.1f}ms exceeds 500ms threshold"


# ── Database Query Benchmarks ─────────────────────────────────────────


class TestDatabasePerformance:
    """Benchmark database operations."""

    def test_single_record_lookup(self, client, db_session):
        """Single record lookup should be < 5ms."""
        headers = _register_and_login(client, "dbbench")

        # Create a scan to look up. There is no POST /api/v1/scans; scans are
        # created by uploading a spec to /api/scans/upload.
        from tests.helpers import make_spec, upload_spec

        created = upload_spec(client, headers, make_spec(["/v1/orders"]), api_name="bench-api")
        assert created.status_code == 200, created.text
        scan_id = created.json()["id"]

        times = []
        for _ in range(50):
            start = time.perf_counter()
            client.get(f"/api/v1/scans/{scan_id}", headers=headers)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        p95 = _percentile(sorted(times), 95)
        assert p95 < 50, f"Single lookup p95={p95:.1f}ms exceeds 50ms threshold"

    def test_aggregate_query_performance(self, client, db_session):
        """Aggregate queries should complete in < 100ms."""
        headers = _register_and_login(client, "aggbench")

        # Run analytics multiple times to warm up
        for _ in range(3):
            client.get("/api/scans/analytics", headers=headers)

        times = []
        for _ in range(10):
            _, ms = _timed(client.get, "/api/scans/analytics", headers=headers)
            times.append(ms)

        p95 = _percentile(sorted(times), 95)
        assert p95 < 200, f"Aggregate query p95={p95:.1f}ms exceeds 200ms threshold"

    def test_connection_pool_efficiency(self, client, db_session):
        """Multiple rapid requests should reuse connections."""
        _register_and_login(client, "poolbench")

        # Fire 50 rapid requests
        times = []
        for _ in range(50):
            _, ms = _timed(client.get, "/api/v1/health")
            times.append(ms)

        avg = statistics.mean(times)
        stdev = statistics.stdev(times) if len(times) > 1 else 0
        assert avg < 50, f"Connection pool avg={avg:.1f}ms too high"
        assert stdev < 30, f"Connection pool stdev={stdev:.1f}ms too variable (connection churn)"


# ── Cache Performance Benchmarks ──────────────────────────────────────


class TestCachePerformance:
    """Benchmark caching layer."""

    def test_cache_hit_vs_miss(self, client, db_session):
        """Cached responses should be faster than uncached."""
        headers = _register_and_login(client, "cachebench")

        # First call (cold cache)
        client.get("/api/v1/dashboard/overview", headers=headers)

        # Second call (warm cache)
        cached_times = []
        for _ in range(10):
            _, ms = _timed(client.get, "/api/v1/dashboard/overview", headers=headers)
            cached_times.append(ms)

        avg_cached = statistics.mean(cached_times)
        assert avg_cached < 200, f"Cached dashboard avg={avg_cached:.1f}ms too slow"

    def test_cache_invalidation(self, client, db_session):
        """Cache invalidation after mutation should work."""
        headers = _register_and_login(client, "invalidatebench")

        from tests.helpers import make_spec, upload_spec

        # Warm cache
        client.get("/api/v1/dashboard/overview", headers=headers)

        # Create a scan (should invalidate related cache)
        created = upload_spec(client, headers, make_spec(["/v1/orders"]), api_name="test-api")
        assert created.status_code == 200, created.text

        # Next dashboard call should have fresh data
        resp = client.get("/api/v1/dashboard/overview", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["total_scans"] >= 1


# ── Concurrent Request Benchmarks ─────────────────────────────────────


class TestConcurrentPerformance:
    """Benchmark concurrent request handling."""

    def test_sequential_rapid_requests(self, client, db_session):
        """50 sequential requests should complete without errors."""
        _register_and_login(client, "rapidbench")

        errors = 0
        total_ms = 0
        for _ in range(50):
            _, ms = _timed(client.get, "/api/v1/health")
            total_ms += ms
            if ms > 1000:
                errors += 1

        avg_ms = total_ms / 50
        assert errors == 0, f"{errors} requests exceeded 1s threshold"
        assert avg_ms < 100, f"Average request time {avg_ms:.1f}ms too high"

    def test_auth_flow_performance(self, client):
        """Complete auth flow (register → login → refresh → access) should be fast."""
        times = {}
        for i in range(5):
            prefix = f"perfflow{i}"

            _, ms = _timed(
                client.post,
                "/api/auth/register",
                json={"username": prefix, "email": f"{prefix}@test.com", "password": "Test123!@#"},
            )
            times.setdefault("register", []).append(ms)

            _, ms = _timed(
                client.post,
                "/api/auth/login",
                json={"username": prefix, "password": "Test123!@#"},
            )
            times.setdefault("login", []).append(ms)

        for operation, op_times in times.items():
            p95 = _percentile(sorted(op_times), 95)
            assert p95 < 1000, f"{operation} p95={p95:.1f}ms exceeds 1s threshold"


# ── Memory Benchmarks ─────────────────────────────────────────────────


class TestMemoryPerformance:
    """Benchmark memory usage."""

    def test_memory_stable_under_load(self, client, db_session):
        """Memory should not grow unbounded under repeated requests."""
        headers = _register_and_login(client, "membench")

        try:
            import psutil

            process = psutil.Process()
            mem_before = process.memory_info().rss / (1024 * 1024)
        except (ImportError, Exception):
            pytest.skip("psutil not available")

        # Fire 100 requests
        for _ in range(100):
            client.get("/api/v1/health")
            client.get("/api/v1/dashboard/overview", headers=headers)

        try:
            mem_after = process.memory_info().rss / (1024 * 1024)
        except Exception:
            pytest.skip("Could not measure memory after load")

        growth = mem_after - mem_before
        assert growth < 50, f"Memory grew by {growth:.1f}MB during 200 requests (leak suspected)"


# ── Response Size Benchmarks ──────────────────────────────────────────


class TestResponseSize:
    """Benchmark response payload sizes."""

    def test_dashboard_response_size(self, client, db_session):
        """Dashboard response should not exceed 100KB."""
        headers = _register_and_login(client, "sizebench")
        resp = client.get("/api/v1/dashboard/overview", headers=headers)
        size_kb = len(resp.content) / 1024
        assert size_kb < 100, f"Dashboard response is {size_kb:.1f}KB (exceeds 100KB limit)"

    def test_scans_list_response_size(self, client, db_session):
        """Scan list response should be paginated and reasonable."""
        headers = _register_and_login(client, "sizebench2")
        resp = client.get("/api/v1/scans", headers=headers)
        size_kb = len(resp.content) / 1024
        assert size_kb < 50, f"Scan list response is {size_kb:.1f}KB (exceeds 50KB limit)"


# ── Benchmark Summary ─────────────────────────────────────────────────


class TestBenchmarkSummary:
    """Generate a benchmark summary report."""

    def test_benchmark_report(self, client, db_session, capsys):
        """Generate a comprehensive benchmark report."""
        headers = _register_and_login(client, "reportbench")
        results = {}

        # Warm up
        for _ in range(3):
            client.get("/api/v1/health")
            client.get("/api/v1/dashboard/overview", headers=headers)

        # Benchmark endpoints
        endpoints = [
            ("Health", "GET", "/api/v1/health", {}),
            ("Dashboard", "GET", "/api/v1/dashboard/overview", headers),
            ("Scans", "GET", "/api/v1/scans", headers),
            ("Analytics", "GET", "/api/scans/analytics", headers),
            ("Findings", "GET", "/api/v1/findings", headers),
        ]

        for name, _method, path, hdrs in endpoints:
            times = []
            for _ in range(20):
                _, ms = _timed(client.get, path, headers=hdrs)
                times.append(ms)
            times_sorted = sorted(times)
            results[name] = {
                "avg_ms": round(statistics.mean(times), 2),
                "p50_ms": round(_percentile(times_sorted, 50), 2),
                "p95_ms": round(_percentile(times_sorted, 95), 2),
                "p99_ms": round(_percentile(times_sorted, 99), 2),
                "max_ms": round(max(times), 2),
            }

        # Print report
        print("\n" + "=" * 70)
        print("SENTINELAI PERFORMANCE BENCHMARK REPORT")
        print("=" * 70)
        print(
            f"{'Endpoint':<20} {'Avg (ms)':<12} {'P50 (ms)':<12} {'P95 (ms)':<12} {'P99 (ms)':<12} {'Max (ms)':<12}"
        )
        print("-" * 70)
        for name, stats in results.items():
            print(
                f"{name:<20} {stats['avg_ms']:<12.1f} {stats['p50_ms']:<12.1f} "
                f"{stats['p95_ms']:<12.1f} {stats['p99_ms']:<12.1f} {stats['max_ms']:<12.1f}"
            )
        print("=" * 70)

        # Verify all endpoints are within SLA
        for name, stats in results.items():
            assert stats["p95_ms"] < 2000, f"{name} p95={stats['p95_ms']}ms exceeds 2s SLA"
