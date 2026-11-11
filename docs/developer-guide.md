# SentinelAI — Developer Guide

> Everything you need to set up, develop, test, and deploy SentinelAI.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Backend Development](#backend-development)
- [Frontend Development](#frontend-development)
- [Testing](#testing)
- [Debugging](#debugging)
- [Database](#database)
- [Environment Variables](#environment-variables)
- [Common Tasks](#common-tasks)

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| PostgreSQL | 16+ | Production database |
| Redis | 7+ | Cache & sessions |
| Docker | 24+ | Containerization |
| Git | 2.40+ | Version control |

### Optional

| Tool | Purpose |
|------|---------|
| Ollama | Local AI copilot |
| pgAdmin | Database GUI |
| Postman | API testing |

---

## Quick Start

### One-Command Setup (recommended)

```bash
git clone https://github.com/your-org/sentinelai.git
cd sentinelai
make setup     # venv + deps + .env + migrations + demo data
make dev       # backend :8000 and frontend :5173
```

Sign in with `demo / demo1234`. `make doctor` diagnoses the environment,
`make` lists every command, and [DEVELOPER-ONBOARDING.md](DEVELOPER-ONBOARDING.md)
is the 15-minute guided tour. See [CLI.md](CLI.md) for the `sentinel` CLI.

### Manual Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Docker Setup

```bash
docker compose up --build
# Frontend: http://localhost:80
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## Development Setup

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies (requirements-dev.txt includes runtime + tooling)
pip install -r requirements-dev.txt

# Set up database
cp .env.example .env  # Edit with your DB credentials
python -m alembic upgrade head

# Create initial data (admin user)
python -c "from app.database.database import init_database; init_database()"

# Start development server
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev  # Runs on http://localhost:5173

# Build for production
npm run build

# Preview production build
npm run preview
```

### Development Defaults

| Setting | Value |
|---------|-------|
| Admin username | `admin` |
| Admin password | `admin123` |
| Backend port | 8000 |
| Frontend port | 5173 |
| Database | SQLite (`sentinelai.db`) |
| Redis | localhost:6379 (optional) |

---

## Project Structure

```
sentinelai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/          # API endpoints (12 modules)
│   │   │   ├── v1/              # Versioned API wrapper
│   │   │   ├── middleware.py    # Response envelope
│   │   │   ├── envelope.py      # Standard response format
│   │   │   ├── errors.py        # Exception handlers
│   │   │   └── websocket.py     # Real-time streaming
│   │   ├── core/
│   │   │   ├── security_engine/ # OWASP scanner (21 rules)
│   │   │   ├── sast_engine/     # Static analysis (48 rules)
│   │   │   ├── dep_scanner/     # Dependency CVE detection
│   │   │   ├── risk_engine/     # CVSS scoring
│   │   │   ├── ai_engine/       # Vulnerability analysis
│   │   │   └── copilot/         # AI security assistant
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── repositories/        # Data access layer
│   │   ├── services/            # Business logic
│   │   ├── reports/             # Report generation
│   │   ├── utils/               # Cross-cutting concerns
│   │   ├── config.py            # Settings
│   │   ├── main.py              # FastAPI app
│   │   ├── tasks.py             # Background tasks
│   │   └── database.py          # Engine & sessions
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # Test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # Reusable UI components
│   │   ├── pages/               # Route pages (19 routes)
│   │   ├── context/             # React contexts
│   │   ├── services/            # API client
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── main.jsx
│   ├── public/
│   ├── nginx.conf
│   ├── Dockerfile
│   └── package.json
├── deploy/                      # Deployment configs
│   ├── terraform/               # Infrastructure as code
│   ├── loki/                    # Log aggregation
│   ├── alertmanager/            # Alert rules
│   └── prometheus/              # Metrics config
├── scripts/                     # Automation scripts
├── docs/                        # Documentation
├── docker-compose.yml
├── .github/workflows/ci.yml
└── README.md
```

---

## Coding Standards

### Python (Backend)

| Rule | Standard |
|------|----------|
| Formatter | Black |
| Linter | Ruff |
| Line length | 88 (Black default) |
| Type hints | Required for public APIs |
| Docstrings | Google style |
| Import order | stdlib → third-party → local |

```python
# Good
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import Scan
from app.repositories.scans import ScanRepository
from app.utils.security import get_current_user

router = APIRouter()


@router.get("/scans/{scan_id}")
def get_scan(
    scan_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get scan by ID with full details."""
    repo = ScanRepository(db)
    scan = repo.get(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return {"success": True, "data": scan}
```

### JavaScript/JSX (Frontend)

| Rule | Standard |
|------|----------|
| Component style | Functional + Hooks |
| State | React Context (Auth, Org, Theme) |
| Styling | CSS Modules / Global CSS |
| Naming | PascalCase components, camelCase functions |
| File naming | PascalCase.jsx for components, camelCase.js for utils |

```jsx
// Good: Functional component with hooks
function ScanCard({ scan, onSelect }) {
  const [loading, setLoading] = useState(false);

  const handleClick = useCallback(() => {
    onSelect(scan.id);
  }, [scan.id, onSelect]);

  return (
    <div className="scan-card" onClick={handleClick}>
      <h3>{scan.api_name}</h3>
      <span className={`badge badge-${scan.risk_level}`}>
        {scan.risk_level}
      </span>
    </div>
  );
}
```

---

## Backend Development

### Adding a New Endpoint

```bash
# 1. Define the model (if new table)
# Edit backend/app/models/models.py

# 2. Create the Pydantic schema
# Edit backend/app/schemas/schemas.py

# 3. Create the repository
# Edit backend/app/repositories/<module>.py

# 4. Create the service (if business logic needed)
# Edit backend/app/services/<module>.py

# 5. Create the route
# Edit backend/app/api/routes/<module>.py

# 6. Register in main.py
# Add: app.include_router(new_router, prefix="/api/v1/<module>", tags=["<module>"])

# 7. Create migration
cd backend
alembic revision --autogenerate -m "add <feature>"
alembic upgrade head

# 8. Write tests
# Edit backend/tests/test_<module>.py
```

### Adding a New Scanner Rule

```python
# In backend/app/core/security_engine/scanner.py or sast_engine/rules.py

# OWASP rule format:
check_registry = {
    "SA-22": {
        "id": "SA-22",
        "owasp": "API1",
        "title": "My New Check",
        "severity": "high",
        "description": "Description of the vulnerability",
        "cwe": "CWE-XXX",
        "cvss_base": 7.5,
        "remediation": "How to fix this issue",
    },
}

# Then implement the check function:
def check_sa_22(endpoint, schema):
    """Check for my new vulnerability."""
    findings = []
    # ... detection logic ...
    return findings
```

### Background Tasks

```python
# In backend/app/tasks.py

# Tasks run in background threads
# Update scan status, generate reports, run AI analysis
```

---

## Frontend Development

### Adding a New Page

```bash
# 1. Create the page component
# Edit frontend/src/pages/NewPage.jsx

# 2. Add route to App.jsx
# Add: <Route path="/new-page" element={<ProtectedRoute><NewPage /></ProtectedRoute>} />

# 3. Add navigation link to Navbar.jsx
# Add to sidebar nav items
```

### Adding a New Component

```bash
# 1. Create component file
# Edit frontend/src/components/NewComponent.jsx

# 2. Import in parent
# Import and use in the page

# 3. Add styles
# Add CSS classes to App.css or component-specific CSS
```

### API Service Pattern

```javascript
// frontend/src/services/api.js

// Add new API method
export const newModuleAPI = {
  getAll: (params) => api.get("/v1/new-module", { params }),
  getById: (id) => api.get(`/v1/new-module/${id}`),
  create: (data) => api.post("/v1/new-module", data),
  update: (id, data) => api.put(`/v1/new-module/${id}`, data),
  delete: (id) => api.delete(`/v1/new-module/${id}`),
};
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
python -m pytest tests/ --cov=app --cov-report=html

# Run specific test
python -m pytest tests/test_scanner.py::TestSecurityEngine::test_bola_detection -v

# Run only failed tests from last run
python -m pytest tests/ --lf
```

### Test Organization

```
backend/tests/
├── conftest.py                 # Fixtures, test DB setup
├── test_auth.py                # Authentication tests
├── test_scanner.py             # OWASP scanner tests
├── test_sast.py                # SAST engine tests
├── test_dep_scanner.py         # Dependency scanner tests
├── test_copilot.py             # AI copilot tests
├── test_reports.py             # Report generation tests
├── test_organizations.py       # Organization management tests
├── test_enterprise_multitenancy.py  # Enterprise features tests
├── test_security_hardening.py  # Security hardening tests
├── test_audit.py               # Audit logging tests
├── test_websocket.py           # WebSocket tests
├── test_rate_limiting.py       # Rate limiting tests
├── test_migrations.py          # Database migration tests
└── test_integration.py         # Integration tests
```

### Writing Tests

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.database import init_database

@pytest.fixture(scope="module")
def client():
    """Create test client with initialized database."""
    init_database()  # Creates tables + admin user
    with TestClient(app) as c:
        yield c

@pytest.fixture
def auth_headers(client):
    """Get authenticated headers."""
    resp = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_upload_scan(client, auth_headers):
    """Test scanning an OpenAPI spec."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {
            "/users/{id}": {
                "get": {"responses": {"200": {"description": "OK"}}}
            }
        },
    }
    response = client.post(
        "/api/scans/upload",
        headers=auth_headers,
        files={"file": ("spec.json", json.dumps(spec).encode(), "application/json")},
        data={"api_name": "Test"},
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["total_endpoints"] == 1
    assert data["status"] == "completed"
```

---

## Debugging

### Backend

```bash
# Verbose logging
export LOG_LEVEL=debug
python -m uvicorn app.main:app --reload --log-level debug

# Database debugging
python -c "
from app.database.database import get_engine
from sqlalchemy import text
engine = get_engine()
with engine.connect() as conn:
    result = conn.execute(text('SELECT * FROM users'))
    for row in result:
        print(row)
"
```

### Frontend

```bash
# Debug mode
VITE_DEBUG=true npm run dev

# Browser DevTools
# React DevTools extension for component inspection
# Network tab for API calls
# Console for errors
```

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Ensure venv is activated and requirements installed |
| `Address already in use` | Kill process on port: `lsof -ti:8000 \| xargs kill -9` |
| `JWT errors` | Check SECRET_KEY in .env matches |
| `401 on refresh` | Clear localStorage, login again |
| `CORS errors` | Check CORS_ORIGINS in .env |

---

## Database

### Common Operations

```bash
# Create migration
cd backend
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Check current version
alembic current

# Reset database (DANGER)
rm sentinelai.db
alembic upgrade head
```

### Database Queries

```sql
-- List all tables
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public';

-- Count records per table
SELECT 'users' as t, count(*) FROM users
UNION ALL SELECT 'scans', count(*) FROM scans
UNION ALL SELECT 'findings', count(*) FROM findings;

-- Find slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC LIMIT 10;
```

---

## Environment Variables

### Required

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | — | JWT signing key (min 32 chars) |
| `DATABASE_URL` | `sqlite:///sentinelai.db` | Database connection string |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379` | Redis connection |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `mistral` | AI model name |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed origins |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENVIRONMENT` | `development` | Environment name |

See `.env.example` for the complete list.

---

## Common Tasks

### Add New Database Table

```python
# 1. Add model to backend/app/models/models.py
class NewTable(Base):
    __tablename__ = "new_table"
    id = Column(Integer, primary_key=True)
    # ...

# 2. Generate migration
cd backend && alembic revision --autogenerate -m "add new_table"

# 3. Apply
alembic upgrade head
```

### Add New API Endpoint

```bash
# 1. Add route to backend/app/api/routes/<module>.py
# 2. Register in main.py
# 3. Test with curl or Swagger UI
# 4. Write tests
```

### Add New Frontend Page

```bash
# 1. Create frontend/src/pages/NewPage.jsx
# 2. Add route in App.jsx
# 3. Add nav link in Navbar.jsx
# 4. Add API method in services/api.js
```

### Generate Release

```bash
# 1. Update CHANGELOG.md
# 2. Create git tag
git tag -a v1.x.0 -m "Release v1.x.0"
# 3. Verify
git log --oneline -5
```
