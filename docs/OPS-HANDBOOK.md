# SentinelAI — Operations Handbook

> Production operations guide for monitoring, alerting, incident response, and maintaining SentinelAI.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Observability Stack](#observability-stack)
3. [Monitoring Endpoints](#monitoring-endpoints)
4. [Circuit Breakers](#circuit-breakers)
5. [SLA & Error Budget](#sla--error-budget)
6. [Alert Thresholds](#alert-thresholds)
7. [Incident Response](#incident-response)
8. [Runbooks](#runbooks)
9. [Performance Tuning](#performance-tuning)
10. [Scaling Guide](#scaling-guide)
11. [Disaster Recovery](#disaster-recovery)

---

## System Overview

### Architecture at a Glance

```
                    ┌─────────────────────────┐
                    │      Load Balancer       │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     Nginx (80/443)       │
                    │   TLS + Rate Limiting    │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
    ┌─────────▼─────────┐ ┌─────▼──────┐ ┌────────▼────────┐
    │  Backend (8000)    │ │ Frontend   │ │  Prometheus      │
    │  FastAPI + Uvicorn │ │ (5173)     │ │  (9090)          │
    └─────────┬─────────┘ └────────────┘ └────────┬────────┘
              │                                    │
    ┌─────────┼──────────┐              ┌──────────▼──────────┐
    │         │          │              │     Grafana          │
    │    ┌────▼────┐ ┌───▼────┐        │     (3001)           │
    │    │ Postgres │ │ Redis  │        └──────────────────────┘
    │    │ (5432)  │ │ (6379) │
    │    └─────────┘ └────────┘
    │
    ┌▼──────────┐
    │  Ollama    │
    │  (11434)   │
    └───────────┘
```

### Service Dependencies

| Service | Purpose | Failure Impact | Recovery |
|---------|---------|---------------|----------|
| PostgreSQL | Primary database | Full outage | Automatic reconnect |
| Redis | Caching, token blacklist | Degraded (in-memory fallback) | Auto-reconnect |
| Ollama | AI engine | AI features unavailable | Rule-based fallback |
| Nginx | TLS termination, static files | No external access | Restart |
| Prometheus | Metrics collection | No metrics dashboard | Restart |
| Grafana | Visualization | No dashboards | Restart |

---

## Observability Stack

### Logging

**Structured JSON logging** with correlation IDs, user context, and request tracking.

```bash
# View logs
docker-compose logs -f backend

# Filter by level
docker-compose logs backend | grep '"level": "ERROR"'

# Filter by correlation ID
docker-compose logs backend | grep '"request_id": "abc-123"'
```

**Log fields:**
- `timestamp` — ISO 8601 with timezone
- `level` — INFO, WARNING, ERROR, CRITICAL
- `logger` — Source module
- `message` — Human-readable message
- `request_id` — Correlation ID for request tracing
- `user_id` — Authenticated user
- `scan_id` — Active scan context
- `duration_ms` — Request duration
- `exception` — Error details with traceback

### Distributed Tracing

Every request gets a correlation ID that propagates through:
- HTTP headers (`X-Request-ID`, `X-Correlation-ID`, `X-Trace-ID`)
- Log entries (automatic context binding)
- Span tracking (function-level timing)

```python
# Create a span in application code
from app.utils.tracing import create_span

with create_span("scan.parse_spec", {"scan_id": 42}) as span:
    result = parse_spec()
    span.set_attribute("endpoints_found", len(result))
```

### Prometheus Metrics

**172+ routes** including `/metrics` endpoint for Prometheus scraping.

**Key metrics:**
- `sentinelai_http_requests_total` — Request count by method/path/status
- `sentinelai_http_request_duration_seconds` — Latency histogram
- `sentinelai_scans_total` — Scan count by type
- `sentinelai_findings_total` — Findings by severity
- `sentinelai_ai_requests_total` — AI copilot requests
- `sentinelai_cpu_usage_percent` — CPU utilization
- `sentinelai_memory_rss_bytes` — Process memory
- `sentinelai_db_latency_seconds` — Database probe latency
- `sentinelai_uptime_seconds` — Process uptime

---

## Monitoring Endpoints

### Health Checks

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `GET /` | Basic health check | No |
| `GET /api/health` | API health status | No |
| `GET /api/health/detailed` | Full system health with all checks | No |
| `GET /metrics` | Prometheus metrics | No |

### SRE Dashboard

| Endpoint | Purpose |
|----------|---------|
| `GET /api/sre/sla` | SLA compliance summary |
| `GET /api/sre/sla/error-budget` | Error budget status and burn rate |
| `GET /api/sre/sla/availability` | Availability metrics |
| `GET /api/sre/sla/latency` | Latency percentiles |
| `GET /api/sre/alerts` | Active alerts |
| `GET /api/sre/alerts/history` | Alert history |
| `GET /api/sre/uptime` | Service uptime status |
| `GET /api/sre/incidents` | Active incidents |
| `GET /api/sre/incidents/history` | Incident history |
| `GET /api/sre/resilience` | Circuit breaker and bulkhead status |
| `GET /api/sre/traces` | Recent trace spans |
| `GET /api/sre/performance` | Performance metrics |

---

## Circuit Breakers

SentinelAI uses circuit breakers to prevent cascading failures.

### Pre-configured Breakers

| Breaker | Threshold | Recovery | Protects |
|---------|-----------|----------|----------|
| `ollama` | 3 failures | 30s | AI engine calls |
| `database` | 5 failures | 15s | Database queries |
| `redis` | 3 failures | 20s | Redis operations |
| `scanner` | 5 failures | 10s | External scanner APIs |

### States

```
CLOSED ──(failures >= threshold)──→ OPEN
  ↑                                  │
  │                          (timeout expires)
  │                                  ↓
  └──(success)── HALF_OPEN ←──(failure)
```

### Bulkheads

| Bulkhead | Max Concurrent | Protects |
|----------|---------------|----------|
| `ai_engine` | 5 | AI copilot requests |
| `scanner` | 3 | Scan operations |
| `database` | 20 | Database connections |

---

## SLA & Error Budget

### SLA Targets

| Metric | Target | Acceptable |
|--------|--------|-----------|
| Availability | 99.9% | 99.0% |
| P95 Latency | 500ms | 1000ms |
| P99 Latency | 1000ms | 2000ms |
| Error Rate | <1% | <5% |

### Error Budget

- **Budget**: 0.1% of requests can fail (≈43 minutes/month of downtime)
- **Burn Rate**: How fast the budget is consumed
  - 1.0x = consuming at expected rate
  - 2.0x = consuming twice as fast
  - 10.0x = critical — budget exhausted in ~2.5 hours

### Monitoring Error Budget

```bash
# Check error budget status
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/sre/sla/error-budget

# Response:
{
  "budget_percent": 0.1,
  "allowed_failures": 100,
  "actual_failures": 15,
  "remaining_percent": 85.0,
  "burn_rate": 0.15,
  "status": "healthy"
}
```

---

## Alert Thresholds

### Default Thresholds

| Alert | Metric | Threshold | Severity |
|-------|--------|-----------|----------|
| Availability Critical | availability | <99.0% | CRITICAL |
| Availability Warning | availability | <99.5% | WARNING |
| Latency P95 Warning | latency_p95 | >500ms | WARNING |
| Latency P99 Critical | latency_p99 | >1000ms | CRITICAL |
| Error Rate Critical | error_rate | >5.0% | CRITICAL |
| Error Budget Critical | burn_rate | >10.0x | CRITICAL |

### Alert Lifecycle

1. **Fired** — Threshold breached, alert created
2. **Acknowledged** — Engineer has acknowledged the alert
3. **Resolved** — Metric returns to normal, auto-resolved

---

## Incident Response

### Severity Levels

| Level | Description | Response Time | Example |
|-------|-------------|--------------|---------|
| P1 Critical | Complete outage | 15 minutes | Database down, auth broken |
| P2 High | Major feature degraded | 1 hour | Scan engine failing, AI unavailable |
| P3 Medium | Minor feature affected | 4 hours | Export failing, webhook delays |
| P4 Low | Cosmetic or minor | 24 hours | UI glitch, non-critical error |

### Incident Lifecycle

```
Detected → Triaged → Investigating → Identified → Mitigating → Monitoring → Resolved → Post-Mortem
```

### Communication Template

```
INCIDENT [P2] — Scan Engine Degraded

Status: Investigating
Started: 2026-08-27 14:30 UTC
Impact: Scan completion times elevated, ~30% of scans timing out
Current: Investigating database connection pool exhaustion
Next Update: 30 minutes

Workaround: Restart backend service if scans are critical
```

---

## Runbooks

### Runbook 1: High Error Rate

**Symptoms:** Error rate >5%, alerts firing
**Severity:** P2

**Diagnosis:**
```bash
# Check error rate
curl http://localhost:8000/api/sre/sla/error-rate

# Check recent errors in logs
docker-compose logs backend --tail=100 | grep '"level": "ERROR"'

# Check circuit breaker status
curl http://localhost:8000/api/sre/resilience
```

**Resolution:**
1. Identify failing endpoint from error logs
2. Check if database is healthy: `curl http://localhost:8000/api/health/detailed`
3. If database is down, check connection pool: look for "pool" in health check
4. If AI engine is down, circuit breaker should be OPEN — verify fallback works
5. Restart backend if needed: `docker-compose restart backend`
6. Monitor for 15 minutes after resolution

### Runbook 2: High Latency

**Symptoms:** P95 >500ms, slow request alerts
**Severity:** P2-P3

**Diagnosis:**
```bash
# Check latency percentiles
curl http://localhost:8000/api/sre/sla/latency

# Check slow requests
curl http://localhost:8000/api/sre/performance

# Check database latency
curl http://localhost:8000/api/health/detailed | jq '.details.database'

# Check memory pressure
curl http://localhost:8000/api/sre/performance | jq '.requests.memory'
```

**Resolution:**
1. Identify slow endpoints from performance stats
2. Check database query latency — if >100ms, investigate slow queries
3. Check memory usage — if >80%, may need restart or scaling
4. Check if AI engine is responding — fallback should handle this
5. Consider scaling: `docker-compose up --scale backend=3`

### Runbook 3: Database Connection Issues

**Symptoms:** "database unhealthy", connection errors
**Severity:** P1

**Diagnosis:**
```bash
# Check database health
curl http://localhost:8000/api/health/detailed | jq '.details.database'

# Check connection pool
curl http://localhost:8000/api/health/detailed | jq '.details.database.pool_size'

# Check database directly
docker-compose exec postgres psql -U sentinelai -c "SELECT 1"
```

**Resolution:**
1. Verify PostgreSQL is running: `docker-compose ps postgres`
2. Check connection pool saturation — if all connections are checked out, restart backend
3. Check for long-running queries: `SELECT * FROM pg_stat_activity WHERE state = 'active'`
4. Kill long queries if needed: `SELECT pg_terminate_backend(pid)`
5. Restart backend: `docker-compose restart backend`
6. If persistent, check disk space and memory

### Runbook 4: Circuit Breaker Open

**Symptoms:** "Circuit breaker is OPEN" errors
**Severity:** P2-P3

**Diagnosis:**
```bash
# Check which breaker is open
curl http://localhost:8000/api/sre/resilience | jq '.circuit_breakers[] | select(.state == "open")'
```

**Resolution:**
1. Identify which service is failing (ollama, database, redis)
2. Check if the underlying service is running
3. Wait for automatic recovery (recovery timeout varies: 10-30s)
4. If persistent, restart the failing service
5. Manually reset if needed: call the reset endpoint
6. Verify recovery: check that breaker transitions to CLOSED

### Runbook 5: AI Engine Unavailable

**Symptoms:** AI features returning rule-based fallbacks
**Severity:** P3

**Diagnosis:**
```bash
# Check AI engine status
curl http://localhost:8000/api/health/detailed | jq '.details.ai_engine'

# Check if Ollama is running
curl http://localhost:11434/api/tags
```

**Resolution:**
1. AI engine is optional — rule-based fallback handles all requests
2. If Ollama is not running, start it: `ollama serve` or `docker-compose up ollama`
3. Pull the model: `ollama pull mistral`
4. Verify: `curl http://localhost:11434/api/tags`
5. AI features will automatically resume once Ollama is healthy

### Runbook 6: Redis Unavailable

**Symptoms:** "Token blacklist: Redis unavailable" warnings
**Severity:** P3

**Diagnosis:**
```bash
# Check Redis status
curl http://localhost:8000/api/health/detailed | jq '.details.redis'

# Check Redis directly
docker-compose exec redis redis-cli ping
```

**Resolution:**
1. Redis is optional — in-memory fallback handles token blacklist
2. If Redis is not running: `docker-compose up redis`
3. If Redis is running but unreachable, check network/firewall
4. Note: Token revocation won't survive server restarts without Redis
5. Restart backend after Redis recovery: `docker-compose restart backend`

### Runbook 7: Memory Pressure

**Symptoms:** High memory usage, OOM kills, slow responses
**Severity:** P2

**Diagnosis:**
```bash
# Check memory
curl http://localhost:8000/api/sre/performance | jq '.requests.memory'

# Check OS memory
free -h
ps aux | grep uvicorn
```

**Resolution:**
1. Check if memory is growing (memory leak) or spiked (large scan)
2. If gradual growth, restart backend: `docker-compose restart backend`
3. If spike, check for large OpenAPI specs being parsed
4. Monitor GC stats from performance endpoint
5. Consider increasing container memory limit in docker-compose.yml
6. For persistent issues, scale horizontally

### Runbook 8: Disk Full

**Symptoms:** "No space left on device" errors
**Severity:** P1

**Diagnosis:**
```bash
# Check disk
df -h
docker system df
```

**Resolution:**
1. Clean Docker resources: `docker system prune -f`
2. Remove old logs: `truncate -s 0 sentinelai.log`
3. Clean pytest cache: `rm -rf backend/.pytest_cache backend/__pycache__`
4. Check for large scan artifacts
5. If using PostgreSQL, check WAL: `SELECT pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), 0))`

---

## Performance Tuning

### Database

- **Connection pool**: 20 primary + 10 overflow connections
- **WAL mode** for SQLite (development)
- **Indexes**: 26+ on frequently queried columns
- **Slow query threshold**: 500ms

### Caching

- **Dashboard cache TTL**: 60 seconds
- **Analytics cache TTL**: 30 seconds
- **Health cache TTL**: 15 seconds
- **Redis**: Token blacklist, session cache, rate limiting

### Frontend

- **Code splitting**: All pages lazy-loaded with React.lazy
- **Bundle size**: Monitor with `npx vite build --analyze`
- **Recharts**: Separate chunk (117KB gzipped)

---

## Scaling Guide

### Vertical Scaling

| Resource | Current | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4+ cores for 1000+ users |
| Memory | 2GB | 4GB+ for large scans |
| Disk | 20GB | 100GB+ for audit logs |

### Horizontal Scaling

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      replicas: 3
```

### Database Scaling

1. **Read replicas** for analytics queries
2. **Connection pooling** via PgBouncer
3. **Partitioning** for audit_logs and findings (by date)
4. **Archive** old data to cold storage

---

## Disaster Recovery

### Backup Strategy

| Data | Frequency | Retention | Method |
|------|-----------|-----------|--------|
| PostgreSQL | Daily | 30 days | pg_dump |
| Redis | Hourly | 7 days | RDB snapshot |
| Audit logs | Daily | 365 days | pg_dump + archive |
| Configuration | On change | Indefinite | Git |

### Recovery Procedures

**Database restore:**
```bash
pg_restore -d sentinelai backup.dump
```

**Full stack restore:**
```bash
git clone <repo>
cd sentinelai
cp .env.example .env  # Edit with production values
docker-compose up -d
```

**RTO:** 15 minutes (from backup)
**RPO:** 1 hour (data loss window)

### Rollback

```bash
# Rollback to previous version
git checkout v1.1.0
docker-compose up --build -d
```
