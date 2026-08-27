# SentinelAI — Developer Guide

## Quick Start

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 20+ | Frontend build |
| PostgreSQL | 16+ | Production database |
| Redis | 7+ | Caching + token blacklist |
| Git | 2.30+ | Version control |

### Local Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-org/sentinelai.git
cd sentinelai

# 2. Copy environment template
cp .env.example .env
# Edit .env — set SECRET_KEY, POSTGRES_PASSWORD

# 3. Start infrastructure (Docker)
docker compose up -d postgres redis

# 4. Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 5. Frontend setup (new terminal)
cd frontend
npm install
npm run dev

# 6. Open http://localhost:5173
```

### One-Command Docker Setup

```bash
cp .env.example .env  # Edit with your values
docker compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:80
```

---

## Coding Standards

### Python (Backend)

**Formatter:** Black (line length 88)
**Linter:** Ruff
**Type Checker:** MyPy

```bash
# Format
python -m black app tests

# Lint
python -m ruff check app tests

# Type check
python -m mypy app

# All at once
python -m black app tests && python -m ruff check app tests && python -m mypy app
```

#### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Files | snake_case | `scan_service.py` |
| Classes | PascalCase | `ScanRepository` |
| Functions | snake_case | `get_current_user()` |
| Variables | snake_case | `risk_score` |
| Constants | UPPER_SNAKE | `SEVERITY_ORDER` |
| Private | `_prefix` | `_extract_module()` |

#### Function Signatures

```python
# Always use type hints
def get_findings(
    db: Session,
    user_id: int,
    *,
    severity: str | None = None,
    limit: int = 50,
) -> list[Finding]:
    """Get findings with optional filtering."""
    ...
```

#### Docstrings

```python
def record_action(
    db: Session,
    action: str,
    *,
    user_id: int | None = None,
    risk_level: str | None = None,
) -> None:
    """Persist a single audit entry (does not commit).

    If risk_level is not provided, it is auto-classified from the action.
    """
```

#### Error Handling

```python
# Always use HTTPException for API errors
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Scan not found"
)

# Never expose internal errors to clients
try:
    result = dangerous_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    raise HTTPException(status_code=500, detail="Internal error")
```

### JavaScript/React (Frontend)

**Build:** Vite 6
**Router:** React Router 6
**Charts:** Recharts
**Icons:** Lucide React

#### Component Structure

```jsx
// Functional components with hooks
export default function MyPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData().then(setData).finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;
  return <div>{/* content */}</div>;
}
```

#### API Calls

```javascript
// Always use the centralized api.js service
import { scans, security } from '../services/api';

const data = await scans.dashboard();
const result = await security.sast.scanFile(file);
```

---

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_scanner.py -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=term-missing

# Run matching pattern
python -m pytest tests/ -k "test_owasp" -v
```

#### Test Structure

```python
class TestScanEndpoint:
    """Tests for the scan upload endpoint."""

    def test_upload_valid_spec(self, client, auth_headers):
        """Upload a valid OpenAPI spec and verify scan creation."""
        with open("samples/vulnerable_api.yaml", "rb") as f:
            resp = client.post(
                "/api/scans/upload",
                files={"file": ("api.yaml", f)},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_vulnerabilities"] > 0
```

#### Test Fixtures

```python
@pytest.fixture()
def client(tmp_path):
    """Test client with fresh database."""
    ...

@pytest.fixture()
def auth_headers(client):
    """Authenticated headers for API calls."""
    ...
```

### Frontend Tests

```bash
cd frontend
npm test           # Run once
npm run test:watch  # Watch mode
```

---

## Project Architecture Patterns

### Repository Pattern

All database access goes through repositories. Never query directly from routes.

```python
# routes/scans.py — DON'T do this
findings = db.query(Finding).filter(Finding.scan_id == scan_id).all()

# routes/scans.py — DO this
scan_repo = ScanRepository(db)
findings = scan_repo.findings_for_scan(scan_id)
```

### Service Layer

Business logic lives in services. Routes handle HTTP, services handle domain.

```python
# routes/scans.py
def upload_and_scan(...):
    scan = execute_scan(db, user_id, api_name, spec)  # Service call
    return scan

# services/scan_service.py
def execute_scan(db, user_id, api_name, spec):
    # Parse, scan, risk score, AI analysis, save
    ...
```

### Middleware Stack (Execution Order)

```
Request → CORS → RequestID → SecurityHeaders → Logging → RateLimit → Envelope → Route
Response ← CORS ← RequestID ← SecurityHeaders ← Logging ← RateLimit ← Envelope ← Route
```

### Audit Logging Pattern

```python
# Record any security-relevant event
record_action(
    db,
    "scan.completed",
    user_id=user.id,
    username=user.username,
    entity_type="scan",
    entity_id=scan.id,
    risk_level="medium",
    ip_address=get_client_ip(request),
    user_agent=request.headers.get("user-agent"),
    request_id=getattr(request.state, "request_id", None),
)
```

---

## Debugging

### Common Issues

| Issue | Solution |
|-------|----------|
| `database is locked` | Stop other processes using the DB file |
| `ModuleNotFoundError` | Activate venv: `source venv/bin/activate` |
| `CORS error` | Check `CORS_ORIGINS` in `.env` matches frontend URL |
| `401 Unauthorized` | Token expired — implement refresh flow |
| `Redis unavailable` | Start Redis: `docker compose up -d redis` |
| `Migration failed` | Run `alembic upgrade head` |

### Debug Mode

```bash
# Backend with debug logging
LOG_LEVEL=DEBUG uvicorn app.main:app --reload --log-level debug

# Frontend with Vite debug
DEBUG=vite:* npm run dev
```

### Inspect API

```bash
# OpenAPI docs
open http://localhost:8000/docs

# ReDoc
open http://localhost:8000/redoc

# Raw OpenAPI spec
curl http://localhost:8000/openapi.json | python -m json.tool
```

### Test Database

```bash
# Create fresh test database
rm sentinelai.db
alembic upgrade head

# Or use PostgreSQL for testing
TEST_DATABASE_URL=postgresql://user:pass@localhost/testdb pytest
```

---

## Deployment

### Docker Compose (Recommended)

```bash
# Production deployment
cp .env.example .env
# Edit .env with production values

docker compose up -d --build

# Verify
./scripts/smoke-test.sh
```

### Render

1. Push to GitHub
2. Connect repo on render.com — `render.yaml` auto-detected
3. PostgreSQL + Redis provisioned automatically
4. Deploy

### Railway

1. Connect repo on railway.app
2. Add PostgreSQL + Redis plugins
3. Set `SECRET_KEY` env var
4. Deploy — `railway.json` configures everything

### Environment Variables

See `.env.example` for all 25+ configurable variables. Key ones:

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | JWT signing key (64+ chars) |
| `POSTGRES_PASSWORD` | Yes | Database password |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | No | Redis connection string |
| `SENTRY_DSN` | No | Error tracking DSN |
| `OLLAMA_MODEL` | No | AI model name (default: mistral) |

---

## Contributing

### Branch Strategy

```
main ← production-ready
  └── feature/* ← new features
  └── fix/*     ← bug fixes
  └── docs/*    ← documentation
```

### Commit Convention

```
feat: add audit log export endpoint
fix: resolve cache invalidation race condition
docs: update architecture diagram
test: add RBAC tests for audit endpoints
refactor: extract risk scoring into service layer
```

### Pull Request Checklist

- [ ] Tests pass (`pytest tests/ -q`)
- [ ] Lint passes (`black --check && ruff check`)
- [ ] Type check passes (`mypy app`)
- [ ] Build succeeds (`npm run build`)
- [ ] New tests for new features
- [ ] Documentation updated
- [ ] No hardcoded secrets
- [ ] Audit logging for new endpoints
