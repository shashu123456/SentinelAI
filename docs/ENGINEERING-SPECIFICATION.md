# SentinelAI — Engineering Specification

> **Document Type:** Engineering Blueprint  
> **Version:** 1.0  
> **Date:** August 2026  
> **Classification:** Internal — Engineering Team  
> **Status:** Pre-Implementation Review  
> **Author:** CTO Office  
> **Reviewers:** Backend Lead, Frontend Lead, Security Lead, QA Lead, DevOps Lead

---

# SECTION 1: Engineering Principles

## 1.1 Core Philosophy

Every engineering decision in SentinelAI must satisfy this test:

> "Would a Staff Engineer at Google approve this code in a design review?"

If the answer is no, it doesn't ship.

## 1.2 Principles

### Clean Architecture
**What:** Separate business logic from infrastructure. Domain models know nothing about HTTP, databases, or UI.  
**Why:** Business logic is the most valuable and least replaceable code. It must survive framework migrations, database changes, and UI rewrites.  
**Enforcement:** Domain models in `models/` have zero imports from `api/`, `services/`, or `repositories/`. Violations fail CI.

### SOLID
**What:** Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion.  
**Why:** Systems built on SOLID principles are easier to test, extend, and maintain. Without them, every change risks breaking unrelated functionality.  
**Enforcement:** Code review checklist includes SOLID violations. Automated linters catch common violations.

### DRY (Don't Repeat Yourself)
**What:** Every piece of knowledge has a single, unambiguous representation.  
**Why:** Duplication is the root of inconsistency. When the same logic exists in two places, one will be updated and the other won't.  
**Enforcement:** Extract shared logic into utilities, services, or components. If you write the same code twice, the third time you must refactor.

### KISS (Keep It Simple, Stupid)
**What:** The simplest solution that works is the best solution.  
**Why:** Complexity is the enemy of reliability. Every line of code is a liability — it must be understood, tested, and maintained.  
**Enforcement:** If a solution requires more than 3 levels of abstraction, it's too complex. Simplify.

### Domain-Driven Design
**What:** The software structure mirrors the business domain. Bounded contexts define clear boundaries.  
**Why:** When code reflects the business, non-engineers can understand it. When boundaries are clear, teams can work independently.  
**Enforcement:** Each domain (Scanning, Vulnerabilities, Organizations, AI) is a bounded context with its own models, services, and repositories.

### Event-Driven Architecture
**What:** Components communicate through events, not direct calls.  
**Why:** Events decouple producers from consumers. Adding a new feature (e.g., "notify Slack when scan completes") doesn't require modifying the scan service.  
**Enforcement:** Cross-domain communication uses events. Same-domain communication uses direct service calls.

### API-First
**What:** Every feature is an API endpoint. The UI is one consumer among many (CLI, IDE extension, CI/CD integration).  
**Why:** API-first forces clean interfaces. It enables parallel development (frontend and backend simultaneously). It makes the platform extensible.  
**Enforcement:** API spec is written before implementation. Frontend mocks from the spec. Backend implements to the spec.

### Test-First
**What:** Write tests before implementation when feasible, always write tests after.  
**Why:** Tests are the specification. If you can't write a test for a feature, you don't understand the feature well enough.  
**Enforcement:** No PR merges without tests. Coverage threshold: 80% for new code.

### Security by Design
**What:** Security is not a feature — it's a property of every design decision.  
**Why:** Bolting security on after the fact is expensive and incomplete. Security must be in the architecture, not the patches.  
**Enforcement:** Security review for every PR touching auth, data access, or external interfaces. OWASP Top 10 checklist in code review.

### AI-First
**What:** AI is not an add-on — it's the core differentiator. Every workflow should have an AI-assisted path.  
**Why:** Competitors are bolting AI onto legacy products. We're building AI-native from day one. This is our moat.  
**Enforcement:** Every new feature must answer: "How does AI make this better?" If there's no AI angle, justify why.

---

# SECTION 2: System Architecture

## 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                               │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Web App  │  │ CLI      │  │ VS Code  │  │ CI/CD    │          │
│  │ React    │  │ Python   │  │ Extension│  │ Plugin   │          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
│       │              │              │              │                 │
└───────┼──────────────┼──────────────┼──────────────┼────────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY                                 │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Rate Limiter → Auth Middleware → Request ID → CORS → Logger │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       APPLICATION LAYER                             │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Auth     │  │ Scanning │  │ AI       │  │ Reporting│          │
│  │ Service  │  │ Service  │  │ Service  │  │ Service  │          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
│       │              │              │              │                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Vuln     │  │ Org      │  │ Audit    │  │ Compliance│          │
│  │ Service  │  │ Service  │  │ Service  │  │ Service   │          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
│       │              │              │              │                 │
└───────┼──────────────┼──────────────┼──────────────┼────────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                    │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │PostgreSQL│  │ Redis    │  │ S3/MinIO │  │Elastic-  │          │
│  │ (Primary)│  │ (Cache)  │  │ (Files)  │  │search    │          │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       WORKER LAYER                                  │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Scan     │  │ Report   │  │ AI       │  │ Notifi-  │          │
│  │ Worker   │  │ Worker   │  │ Worker   │  │ cation   │          │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘          │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                         │
│  │ Cleanup  │  │ Scheduler│  │ Webhook  │                         │
│  │ Worker   │  │          │  │ Worker   │                         │
│  └──────────┘  └──────────┘  └──────────┘                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     INFRASTRUCTURE LAYER                            │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Docker   │  │ K8s      │  │Prometheus│  │ Grafana  │          │
│  │ Compose  │  │ (Prod)   │  │          │  │          │          │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 2.2 Component Specifications

### Frontend
| Property | Value |
|----------|-------|
| Framework | React 18 with lazy loading |
| Bundler | Vite 6 |
| Charts | Recharts |
| Icons | Lucide React |
| Routing | React Router v6 |
| State | React Context (no Redux — too heavy for this scope) |
| Forms | Native + custom validation |
| Styling | CSS Modules (no Tailwind — we control the design system) |
| Testing | Vitest + React Testing Library |
| Linting | ESLint + Prettier |
| TypeScript | Gradual adoption (new files TS, existing files JS) |

### Backend
| Property | Value |
|----------|-------|
| Framework | FastAPI 0.115+ |
| ORM | SQLAlchemy 2.0 (async-ready) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Auth | JWT (python-jose) + bcrypt |
| Rate Limiting | SlowAPI |
| Task Queue | Celery + Redis (v2+) |
| PDF Generation | ReportLab |
| WebSockets | FastAPI WebSocket |
| Testing | pytest + httpx |
| Linting | Ruff + Black |
| Type Checking | mypy |

### Database
| Property | Value |
|----------|-------|
| Primary | PostgreSQL 16 (production) |
| Development | SQLite (local dev only) |
| Cache | Redis 7 |
| Search | PostgreSQL full-text (v1), Elasticsearch (v3+) |
| Object Storage | S3 / MinIO (reports, uploads) |

### AI Layer
| Property | Value |
|----------|-------|
| Primary | Ollama (self-hosted, local) |
| Cloud Fallback | OpenAI API (GPT-4o) |
| Embeddings | sentence-transformers (local) or OpenAI embeddings |
| Vector Store | pgvector (PostgreSQL extension) |
| Prompt Management | Version-controlled templates in codebase |
| Streaming | Server-Sent Events (SSE) |

### Workers
| Property | Value |
|----------|-------|
| Queue | Celery with Redis broker |
| Workers | 4 worker types: scan, report, AI, notification |
| Concurrency | 4 concurrent tasks per worker |
| Retry | Exponential backoff, max 3 retries |
| Dead Letter | Failed tasks logged and inspectable |
| Monitoring | Flower for worker status |

---

# SECTION 3: Folder Architecture

## 3.1 Root Structure

```
sentinelai/
├── backend/                    # Python backend
│   ├── app/                    # Application code
│   ├── alembic/                # Database migrations
│   ├── tests/                  # Test suite
│   ├── scripts/                # Utility scripts
│   ├── requirements.txt        # Dependencies
│   ├── pyproject.toml          # Project config
│   ├── alembic.ini             # Migration config
│   ├── Dockerfile              # Backend Docker
│   └── .env.example            # Environment template
│
├── frontend/                   # React frontend
│   ├── src/                    # Source code
│   ├── public/                 # Static assets
│   ├── index.html              # Entry point
│   ├── package.json            # Dependencies
│   ├── vite.config.js          # Build config
│   ├── vitest.config.js        # Test config
│   ├── .eslintrc.js            # Lint config
│   ├── .prettierrc             # Format config
│   └── Dockerfile              # Frontend Docker
│
├── cli/                        # CLI tool (Python)
│   ├── sentinel/               # CLI package
│   ├── setup.py                # Package config
│   └── README.md               # CLI docs
│
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DEPLOYMENT.md
│   ├── SECURITY.md
│   ├── CONTRIBUTING.md
│   ├── CHANGELOG.md
│   ├── DESIGN-SYSTEM.md
│   ├── PRODUCT-STRATEGY.md
│   └── ENGINEERING-SPECIFICATION.md
│
├── .github/                    # GitHub config
│   ├── workflows/              # CI/CD
│   ├── ISSUE_TEMPLATE/         # Issue templates
│   └── PULL_REQUEST_TEMPLATE.md
│
├── docker-compose.yml          # Local development
├── docker-compose.prod.yml     # Production
├── Makefile                    # Common commands
└── README.md                   # Project README
```

## 3.2 Backend Folder Structure

```
backend/app/
├── __init__.py
├── main.py                     # FastAPI app factory
├── config.py                   # Settings (pydantic-settings)
├── tasks.py                    # Celery app + task definitions
│
├── api/                        # HTTP layer
│   ├── __init__.py
│   ├── errors.py               # Exception handlers
│   ├── middleware.py            # Custom middleware
│   ├── routes/                 # Route modules (one per domain)
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── scans.py
│   │   ├── security.py
│   │   ├── organizations.py
│   │   ├── audit.py
│   │   ├── metrics.py
│   │   ├── testimonials.py
│   │   ├── admin.py
│   │   └── websocket.py
│   └── v1/                     # API versioning
│       ├── __init__.py
│       └── routers/
│
├── core/                       # Business logic engines
│   ├── __init__.py
│   ├── security_engine/        # API vulnerability scanner
│   │   ├── __init__.py
│   │   ├── scanner.py
│   │   └── rules/
│   ├── sast_engine/            # Static analysis
│   │   ├── __init__.py
│   │   ├── scanner.py
│   │   └── rules/
│   ├── dep_scanner/            # Dependency vulnerability scanner
│   │   ├── __init__.py
│   │   ├── scanner.py
│   │   └── cve_database.py
│   ├── ai_engine/              # AI integration
│   │   ├── __init__.py
│   │   ├── analyzer.py
│   │   ├── prompts/            # Version-controlled prompts
│   │   └── fallback.py
│   └── risk_engine/            # Risk scoring
│       ├── __init__.py
│       └── scorer.py
│
├── models/                     # SQLAlchemy ORM models
│   ├── __init__.py
│   └── models.py               # All models in one file (v1)
│
├── schemas/                    # Pydantic schemas
│   ├── __init__.py
│   └── schemas.py              # Request/response schemas
│
├── repositories/               # Data access layer
│   ├── __init__.py
│   ├── base.py                 # Generic repository
│   ├── users.py
│   ├── scans.py
│   ├── findings.py
│   ├── organizations.py
│   ├── reports.py
│   ├── audit.py
│   ├── refresh_tokens.py
│   └── reset_tokens.py
│
├── services/                   # Business logic services
│   ├── __init__.py
│   ├── scan_service.py
│   ├── audit_service.py
│   └── risk_engine.py
│
├── reports/                    # Report generation
│   ├── __init__.py
│   └── generator.py
│
├── utils/                      # Shared utilities
│   ├── __init__.py
│   ├── security.py             # Password hashing, JWT
│   ├── ratelimit.py            # Rate limiting config
│   ├── logger.py               # Structured logging
│   └── cvss.py                 # CVSS scoring
│
└── database/                   # Database configuration
    ├── __init__.py
    └── database.py             # Engine, session, Base
```

## 3.3 Frontend Folder Structure

```
frontend/src/
├── main.jsx                    # Entry point
├── App.jsx                     # Root component + routing
├── App.css                     # Global app styles
├── index.css                   # Design tokens + global styles
├── config.js                   # API URLs, feature flags
│
├── context/                    # React Context providers
│   ├── AuthContext.jsx          # Authentication state
│   ├── ThemeContext.jsx         # Dark/light mode
│   └── ToastContext.jsx         # Toast notifications
│
├── components/                 # Shared components
│   ├── Navbar.jsx               # Sidebar navigation
│   ├── CommandPalette.jsx       # ⌘K command palette
│   ├── Breadcrumbs.jsx          # Breadcrumb navigation
│   ├── Charts.jsx               # Recharts wrappers
│   ├── Skeleton.jsx             # Loading skeletons
│   ├── TiltCard.jsx             # 3D tilt effect
│   ├── Toast.jsx                # Toast notifications
│   ├── ErrorBoundary.jsx        # Error boundary
│   ├── KeyboardShortcuts.jsx    # Global shortcuts
│   └── [Component].css          # Co-located styles
│
├── pages/                      # Page components (one per route)
│   ├── Landing.jsx              # Public landing page
│   ├── Login.jsx                # Auth page
│   ├── Dashboard.jsx            # Executive dashboard
│   ├── NewScan.jsx              # API scanner upload
│   ├── ScanResult.jsx           # Scan results detail
│   ├── ScanLive.jsx             # Live scan progress
│   ├── SASTScan.jsx             # SAST analysis
│   ├── DepScan.jsx              # Dependency scanner
│   ├── Copilot.jsx              # AI security copilot
│   ├── VulnerabilityExplorer.jsx # Centralized findings
│   ├── AuditCenter.jsx          # Audit log timeline
│   ├── ReportCenter.jsx         # Report generation
│   ├── Settings.jsx             # Platform settings
│   ├── SystemHealth.jsx         # System health monitoring
│   └── [Page].css               # Co-located styles
│
├── services/                   # API service layer
│   └── api.js                   # Centralized API client
│
└── hooks/                      # Custom React hooks (future)
    ├── useDebounce.js
    ├── useIntersection.js
    └── useKeyboard.js
```

## 3.4 Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Files (components) | PascalCase | `VulnerabilityExplorer.jsx` |
| Files (utilities) | camelCase | `formatSeverity.js` |
| Files (styles) | PascalCase (match component) | `VulnerabilityExplorer.css` |
| Files (tests) | `[Name].test.[ext]` | `Dashboard.test.jsx` |
| Functions | camelCase | `loadDashboard()` |
| Components | PascalCase | `SeverityDonut` |
| Constants | SCREAMING_SNAKE | `API_BASE`, `SEVERITY_COLORS` |
| Database tables | snake_case | `organization_members` |
| Database columns | snake_case | `created_at` |
| API endpoints | kebab-case | `/api/scan-results` |
| CSS classes | kebab-case | `dash-core-card` |
| CSS variables | kebab-case with prefix | `--accent-cyan`, `--bg-surface` |

---

# SECTION 4: Coding Standards

## 4.1 Python Standards

### Formatting
- **Formatter:** Black (line length 88)
- **Import sorting:** isort (profile=black)
- **Linting:** Ruff (replaces flake8, pyupgrade, isort)

### Functions
```python
# GOOD
def compute_risk_score(findings: list[Finding]) -> RiskAssessment:
    """Compute composite risk assessment from a list of findings.
    
    Args:
        findings: List of Finding model instances.
        
    Returns:
        RiskAssessment with score, level, and recommendations.
        
    Raises:
        ValueError: If findings list is empty.
    """
    ...

# BAD
def compute(f, s=False):
    ...
```

### Naming
```python
# Variables: snake_case
scan_results = []
total_findings = 0

# Functions: snake_case, verb first
def get_user_by_id(user_id: int) -> User | None: ...
def create_scan(user_id: int, api_name: str) -> Scan: ...
def compute_cvss_score(severity: str, category: str) -> float: ...

# Classes: PascalCase
class ScanRepository(BaseRepository[Scan]): ...
class RiskAssessment: ...

# Constants: SCREAMING_SNAKE
MAX_FILE_SIZE = 10 * 1024 * 1024
SEVERITY_ORDER = ("Critical", "High", "Medium", "Low", "Info")

# Private: leading underscore
def _validate_spec(spec: dict) -> bool: ...
```

### Type Hints
```python
# Always use type hints on function signatures
def process_scan(
    db: Session,
    user_id: int,
    spec: dict,
    enable_ai: bool = True,
) -> ScanResult:
    ...

# Use union types (not Optional)
def get_user(user_id: int) -> User | None: ...

# Use generics for repositories
class BaseRepository(Generic[ModelT]):
    def __init__(self, db: Session) -> None: ...
```

### Docstrings
- Every public function must have a docstring
- Use Google style docstrings
- Include Args, Returns, Raises sections
- Private functions: single-line docstring is sufficient

### Error Handling
```python
# GOOD: Specific exceptions with context
class ScanValidationError(Exception):
    def __init__(self, detail: str, field: str | None = None):
        self.detail = detail
        self.field = field

# BAD: Bare except or generic Exception
try:
    ...
except Exception:
    pass
```

## 4.2 React/JavaScript Standards

### Components
```jsx
// Functional components ONLY — no class components
function SeverityBadge({ severity, size = 'md' }) {
  const config = SEVERITY_CONFIG[severity];
  return (
    <span className={`badge ${severity.toLowerCase()}`} style={{ color: config.color }}>
      <config.icon size={size === 'sm' ? 12 : 14} />
      {severity}
    </span>
  );
}

// PropTypes or TypeScript for prop validation
SeverityBadge.propTypes = {
  severity: PropTypes.oneOf(['Critical', 'High', 'Medium', 'Low', 'Info']).isRequired,
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
};
```

### Hooks
```jsx
// Custom hooks: use[Feature] naming
function useDebounce(value, delay = 300) {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debouncedValue;
}
```

### State Management
```
Rule: State lives in the lowest common ancestor that needs it.

- Auth state → AuthContext (global)
- Theme state → ThemeContext (global)
- Page data → Page component (local)
- Form data → Form component (local)
- UI state (modals, drawers) → Component that owns it (local)

Never use Redux for this project. Context + useState is sufficient.
```

### CSS
```css
/* Use CSS custom properties for theming */
.badge {
  color: var(--accent-cyan);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
}

/* BEM-like naming for components */
.dash-core-card { /* block */ }
.dash-core-card:hover { /* state */ }
.dash-core-icon { /* element */ }

/* Co-located CSS: each component has its own CSS file */
/* Dashboard.jsx → Dashboard.css */
/* No global CSS files for component styles */
```

---

# SECTION 5: Backend Standards

## 5.1 Layer Responsibilities

```
HTTP Request
    │
    ▼
Middleware (auth, rate limit, request ID, logging)
    │
    ▼
Route Handler (validate input, call service, return response)
    │
    ▼
Service (business logic, orchestration, validation)
    │
    ├──▶ Repository (data access, queries)
    ├──▶ Core Engine (scanning, AI, risk scoring)
    └──▶ External Service (email, webhooks)
```

### Rules
1. **Routes** never contain business logic. They validate input, call services, and format responses.
2. **Services** never import from `api/`. They are HTTP-agnostic.
3. **Repositories** never contain business logic. They only access the database.
4. **Models** never import from services, repositories, or API layers.

## 5.2 API Response Standards

### Success Response
```json
{
  "id": 123,
  "name": "Petstore API",
  "status": "completed",
  "created_at": "2026-08-20T14:30:00Z"
}
```

### List Response (Paginated)
```json
{
  "items": [...],
  "total": 142,
  "page": 1,
  "page_size": 20
}
```

### Error Response
```json
{
  "detail": "Scan not found",
  "code": "SCAN_NOT_FOUND",
  "field": null
}
```

### Validation Error Response
```json
{
  "detail": "Validation failed",
  "errors": [
    {"field": "email", "message": "Invalid email format"},
    {"field": "password", "message": "Must be at least 8 characters"}
  ]
}
```

## 5.3 Pagination

```python
# Query parameters
?page=1&page_size=20&sort_by=created_at&order=desc

# Default page_size: 20
# Maximum page_size: 100
# Always return total count for client-side pagination
```

## 5.4 Filtering

```python
# Query parameters
?severity=High&status=active&search=payment

# Filters are AND-combined
# Search is OR across name, description, endpoint
# Date ranges: ?date_from=2026-01-01&date_to=2026-01-31
```

## 5.5 Sorting

```python
# Query parameter
?sort_by=-created_at,risk_score
# Prefix - for descending
# Multiple fields separated by comma
```

## 5.6 Transactions

```python
# Use explicit transactions for multi-step operations
def create_organization(db: Session, data: OrgCreate, user_id: int) -> Organization:
    org = Organization(name=data.name, slug=data.slug, owner_id=user_id)
    db.add(org)
    db.flush()  # Get ID without committing
    
    member = OrganizationMember(organization_id=org.id, user_id=user_id, role="admin")
    db.add(member)
    
    db.commit()  # Commit both atomically
    db.refresh(org)
    return org
```

## 5.7 Error Handling

```python
# Custom exceptions map to HTTP status codes
EXCEPTION_MAP = {
    NotFoundError: 404,
    ValidationError: 422,
    ConflictError: 409,
    AuthenticationError: 401,
    AuthorizationError: 403,
    RateLimitError: 429,
    ScanError: 500,
}

# In route handlers
@router.get("/scans/{scan_id}")
def get_scan(scan_id: int, current_user: User = Depends(get_current_user)):
    scan = scan_repo.get_owned(scan_id, current_user.id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan
```

---

# SECTION 6: Frontend Standards

## 6.1 Page Component Pattern

```jsx
function PageName() {
  // 1. State declarations
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 2. Data fetching
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const result = await api.getData();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 3. Loading state
  if (loading) return <SkeletonPage />;

  // 4. Error state
  if (error) return <ErrorState message={error} onRetry={loadData} />;

  // 5. Empty state
  if (!data?.length) return <EmptyState />;

  // 6. Content
  return (
    <div className="page-content">
      <PageHeader />
      <PageContent data={data} />
    </div>
  );
}
```

## 6.2 Component Composition

```
Page Component (data fetching, state)
    └── Section Component (layout, grouping)
        ├── Card Component (content container)
        │   ├── Header (title, actions)
        │   └── Body (content)
        ├── Table Component (data display)
        └── Chart Component (visualization)
```

## 6.3 Accessibility Requirements

| Requirement | Implementation |
|------------|---------------|
| Focus visible | 2px accent-cyan outline on all interactive elements |
| Keyboard navigation | Tab order follows visual order |
| Screen reader | Semantic HTML, ARIA labels on icons |
| Color contrast | 4.5:1 minimum for text |
| Motion | `prefers-reduced-motion` respected |
| Error identification | Errors linked to form fields via `aria-describedby` |

---

# SECTION 7: Security Standards

## 7.1 Authentication

| Property | Value |
|----------|-------|
| Token type | JWT (HS256) |
| Access token lifetime | 30 minutes |
| Refresh token lifetime | 7 days |
| Refresh token rotation | On every use |
| Token storage | HttpOnly cookie + localStorage fallback |
| Password hashing | bcrypt (cost factor 12) |
| Password policy | Min 8 chars, 1 uppercase, 1 number, 1 special |
| Account lockout | 5 failed attempts → 15 minute lockout |
| Rate limiting | 5 login attempts per minute per IP |

## 7.2 Authorization

| Role | Permissions |
|------|-----------|
| **admin** | Full access to all resources, user management, settings |
| **analyst** | Create/manage scans, view findings, export reports |
| **member** | View scans, view findings, limited export |
| **viewer** | Read-only access to all resources |

### RBAC Enforcement
```python
# Every protected endpoint must check authorization
@router.delete("/scans/{scan_id}")
def delete_scan(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scan = scan_repo.get_owned(scan_id, current_user.id)
    if scan is None:
        raise HTTPException(status_code=404)
    scan_repo.soft_delete(scan)
    db.commit()
```

## 7.3 Security Headers

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
X-XSS-Protection: 0
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'
Strict-Transport-Security: max-age=31536000; includeSubDomains (HTTPS only)
```

## 7.4 Input Validation

```
Rule: Never trust user input. Validate everything at the boundary.

- Backend: Pydantic schemas validate all request bodies
- Frontend: Form validation before submission (but never trust it)
- Database: Check constraints on critical columns
- API: Content-Type validation, file type validation, size limits
```

## 7.5 Secrets Management

```
Rule: Never hardcode secrets. Never commit secrets. Never log secrets.

- Environment variables for all configuration
- .env.local for local development (gitignored)
- Docker secrets for container deployments
- No secrets in code, logs, error messages, or API responses
```

---

# SECTION 8: AI Standards

## 8.1 Prompt Management

```
Rule: Prompts are version-controlled code, not strings in functions.

Location: backend/app/core/ai_engine/prompts/
Format: One file per prompt template
Versioning: Git history provides versioning
Testing: Each prompt has a test that verifies output format
```

### Prompt Template Format
```python
# prompts/vulnerability_explain.py

PROMPT_VERSION = "1.2.0"
PROMPT_NAME = "vulnerability_explanation"

TEMPLATE = """
You are a senior application security engineer. Explain the following vulnerability 
to a developer who needs to fix it.

Vulnerability: {vulnerability_name}
Category: {owasp_category}
CWE: {cwe_id}
Severity: {severity}
Endpoint: {affected_endpoint}
Description: {description}

Provide:
1. A clear explanation of what the vulnerability is
2. How an attacker would exploit it
3. The business impact
4. A specific fix with code example in the developer's language

Be concise, actionable, and avoid jargon.
"""

RESPONSE_SCHEMA = {
    "explanation": str,
    "exploitation": str,
    "business_impact": str,
    "fix": str,
    "code_example": str,
}
```

## 8.2 AI Response Standards

| Property | Requirement |
|----------|------------|
| Response format | Always structured (JSON schema) |
| Max tokens | 2048 for explanations, 4096 for code generation |
| Temperature | 0.3 for explanations, 0.1 for code, 0.7 for brainstorming |
| Fallback | Rule-based response if AI unavailable |
| Caching | Cache identical prompts for 24 hours |
| Streaming | Use SSE for responses > 5 seconds |
| Logging | Log prompt + response for quality monitoring |

## 8.3 Hallucination Prevention

1. **Always provide context** — Never ask AI about something it can't see
2. **Validate output format** — Parse AI response against expected schema
3. **Confidence scoring** — If AI confidence < 60%, mark as "AI-assisted" not "AI-determined"
4. **Human-in-the-loop** — AI suggestions are recommendations, not automated actions
5. **Citation requirement** — AI must reference specific findings/data, not general knowledge

---

# SECTION 9: Scanner Standards

## 9.1 Scanner Architecture

```
Each scanner follows the same interface:

Scanner Interface:
  - scan(spec/context) → ScanResult
  - get_rules() → list[Rule]
  - get_metadata() → ScannerMetadata

ScanResult:
  - findings: list[Finding]
  - risk_score: int
  - risk_level: str
  - metadata: dict
  - duration_ms: int
```

## 9.2 Finding Model

```python
class Finding:
    vulnerability_name: str          # Human-readable name
    owasp_category: str              # OWASP Top 10 category
    cwe_id: str | None               # CWE identifier
    severity: str                    # Critical, High, Medium, Low, Info
    confidence: int                  # 0-100, how confident we are
    description: str                 # What the vulnerability is
    evidence: str | None             # Proof of the vulnerability
    impact: str                      # What could happen
    remediation: str                 # How to fix it
    cvss_score: float | None         # CVSS v3.1 score
    cvss_vector: str | None          # CVSS vector string
    affected_endpoint: str | None    # Which endpoint
    affected_method: str | None      # HTTP method
    detection_reason: str | None     # Why this was flagged
    false_positive_note: str | None  # Why this might be a false positive
```

## 9.3 Severity Classification

| Severity | CVSS Range | Remediation SLA | Description |
|----------|-----------|----------------|-------------|
| Critical | 9.0-10.0 | 24 hours | Remote code execution, auth bypass, data breach |
| High | 7.0-8.9 | 7 days | Privilege escalation, significant data exposure |
| Medium | 4.0-6.9 | 30 days | Information disclosure, limited impact |
| Low | 0.1-3.9 | 90 days | Best practice violations, minor issues |
| Info | 0.0 | None | Informational findings, no direct risk |

## 9.4 Confidence Scoring

| Confidence | Meaning | Action |
|-----------|---------|--------|
| 90-100% | Deterministic finding, provable | Auto-flag |
| 70-89% | High confidence, strong indicators | Flag for review |
| 50-69% | Medium confidence, possible issue | Flag with note |
| 30-49% | Low confidence, heuristic-based | Suggest review |
| 0-29% | Very low, likely false positive | Log only |

---

# SECTION 10: Performance Standards

## 10.1 Latency Targets

| Operation | Target (p50) | Target (p95) | Target (p99) |
|-----------|-------------|-------------|-------------|
| API endpoint | 50ms | 200ms | 500ms |
| Dashboard load | 500ms | 1s | 2s |
| Scan (API) | 5s | 15s | 30s |
| Scan (SAST) | 10s | 30s | 60s |
| AI response | 2s | 5s | 10s |
| Report generation | 3s | 10s | 30s |

## 10.2 Throughput Targets

| Metric | Target |
|--------|--------|
| Concurrent users | 100 |
| Concurrent scans | 10 |
| API requests/second | 500 |
| WebSocket connections | 50 |

## 10.3 Caching Rules

| Data | Cache Duration | Invalidation |
|------|---------------|-------------|
| Dashboard stats | 60 seconds | On new scan |
| User profile | 5 minutes | On update |
| Severity distribution | 60 seconds | On new scan |
| Analytics data | 5 minutes | On new scan |
| Testimonials | 1 hour | On update |
| Health status | 30 seconds | Auto-refresh |

## 10.4 Database Optimization

```
Indexes (required):
  - users: username (unique), email (unique)
  - scans: user_id + created_at, status, deleted_at
  - findings: scan_id + severity, scan_id + owasp_category
  - audit_logs: user_id + created_at, entity_type + entity_id
  - refresh_tokens: token_hash (unique), user_id

Query Rules:
  - Never SELECT * — always specify columns
  - Always paginate lists (never return unbounded results)
  - Use exists() for membership checks, not join + count
  - Use bulk operations for batch inserts/updates
  - Soft delete: never hard delete user data
```

---

# SECTION 11: Observability

## 11.1 Structured Logging

```python
# Every log entry must include:
# - Timestamp (ISO 8601)
# - Level (INFO, WARNING, ERROR, CRITICAL)
# - Request ID (UUID)
# - User ID (if authenticated)
# - Module name
# - Message
# - Duration (if applicable)

# Format:
[2026-08-20T14:30:00Z] INFO [req-abc123] [user-42] [scans] Scan completed in 3.2s (14 findings)
```

## 11.2 Metrics

| Metric | Type | Labels |
|--------|------|--------|
| http_requests_total | Counter | method, path, status |
| http_request_duration_seconds | Histogram | method, path |
| scans_total | Counter | scanner_type, status |
| scan_duration_seconds | Histogram | scanner_type |
| findings_total | Counter | severity, scanner_type |
| active_scans | Gauge | scanner_type |
| ai_requests_total | Counter | model, status |
| ai_request_duration_seconds | Histogram | model |

## 11.3 Alerts

| Alert | Condition | Severity |
|-------|----------|----------|
| High error rate | 5xx > 5% for 5 minutes | Critical |
| Slow responses | p95 > 1s for 10 minutes | Warning |
| Queue backlog | Pending tasks > 100 | Warning |
| Database connections | Active > 80% pool | Critical |
| Memory usage | > 80% for 5 minutes | Warning |
| Disk usage | > 90% | Critical |

---

# SECTION 12: Testing Standards

## 12.1 Test Pyramid

```
                    ┌─────────┐
                    │ E2E (5%)│
                    ├─────────┤
                  │Integration│
                  │   (15%)   │
                  ├───────────┤
                │    Unit     │
                │    (80%)    │
                └─────────────┘
```

## 12.2 Coverage Targets

| Layer | Target | Minimum |
|-------|--------|---------|
| Unit tests | 80% | 70% |
| Integration tests | 60% | 50% |
| API tests | 100% of endpoints | 90% |
| Overall | 75% | 65% |

## 12.3 Test Categories

| Category | What | When |
|----------|------|------|
| Unit | Individual functions, pure logic | Every commit |
| Integration | Service + repository + DB | Every commit |
| API | HTTP endpoint behavior | Every commit |
| Security | Auth, authz, input validation | Every PR |
| Performance | Response times, scan duration | Weekly |
| E2E | Full user workflows | Before release |

## 12.4 Test Naming Convention

```python
# Pattern: test_[action]_[condition]_[expected_result]

def test_create_organization_with_valid_data_returns_201():
def test_create_organization_without_auth_returns_401():
def test_create_organization_with_duplicate_slug_returns_409():
def test_delete_scan_as_non_owner_returns_404():
def test_scan_with_empty_spec_returns_400():
```

## 12.5 CI Requirements

```
Every PR must pass:
1. Python linting (Ruff)
2. Python type checking (mypy)
3. Python tests (pytest)
4. Frontend linting (ESLint)
5. Frontend build (Vite)
6. Frontend tests (Vitest)
7. Security scan (Bandit)
8. Dependency audit (pip-audit, npm audit)

Merge is blocked until all checks pass.
```

---

# SECTION 13: DevOps Standards

## 13.1 Docker

```dockerfile
# Backend: Multi-stage build
FROM python:3.11-slim as builder
# ... build dependencies ...
FROM python:3.11-slim as runtime
# ... copy only what's needed ...

# Frontend: Multi-stage build
FROM node:20-alpine as builder
# ... build React app ...
FROM nginx:alpine as runtime
# ... serve static files ...
```

## 13.2 Environments

| Environment | Purpose | Database | Backend | Frontend |
|------------|---------|----------|---------|----------|
| Local | Development | SQLite | localhost:8000 | localhost:5173 |
| Staging | Pre-production testing | PostgreSQL | staging-api.sentinelai.com | staging.sentinelai.com |
| Production | Live | PostgreSQL + Redis | api.sentinelai.com | sentinalai.com |

## 13.3 CI/CD Pipeline

```
PR Created
    │
    ├──▶ Lint (Python + JS)
    ├──▶ Type Check (mypy + TS)
    ├──▶ Unit Tests
    ├──▶ Integration Tests
    ├──▶ Security Scan
    ├──▶ Build Verification
    │
    ▼
PR Merged to main
    │
    ├──▶ Deploy to Staging
    ├──▶ Run E2E Tests
    ├──▶ Performance Tests
    │
    ▼
Release Tag (v1.0.0)
    │
    ├──▶ Build Docker Images
    ├──▶ Push to Registry
    ├──▶ Deploy to Production
    ├──▶ Smoke Tests
    └──▶ Notify Team
```

## 13.4 Database Migrations

```
Rule: Every schema change is an Alembic migration.

Migration naming: [timestamp]_[description].py
Example: 0004_add_api_keys_table.py

Migration rules:
  - Never modify a committed migration
  - Always test migration up AND down
  - Never drop columns in production without backup
  - Always add columns as nullable first, then backfill
  - Never rename columns (add new, migrate data, drop old)
```

---

# SECTION 14: Documentation Standards

## 14.1 Required Documentation

| Document | Location | Audience | Updated |
|----------|----------|----------|---------|
| README.md | Root | Everyone | Every feature |
| API.md | docs/ | Backend engineers | Every endpoint |
| ARCHITECTURE.md | docs/ | All engineers | Every architectural change |
| SECURITY.md | docs/ | Security team | Every security change |
| CONTRIBUTING.md | Root | Contributors | On setup |
| CHANGELOG.md | Root | Everyone | Every release |
| DESIGN-SYSTEM.md | docs/ | Designers, frontend | Every UI change |
| DEPLOYMENT.md | docs/ | DevOps | Every infra change |

## 14.2 Code Documentation

```
Rule: Code is documentation. Comments explain WHY, not WHAT.

# GOOD: Explains non-obvious decision
# We use flush() here instead of commit() because we need the ID
# for the audit log, but the transaction isn't complete yet.
db.flush()

# BAD: Explains what the code does
# Add the object to the session
db.add(obj)
```

---

# SECTION 15: Release Strategy

## 15.1 Versioning

```
Semantic Versioning: MAJOR.MINOR.PATCH

MAJOR: Breaking API changes, database migrations, major feature additions
MINOR: New features, non-breaking API additions
PATCH: Bug fixes, security patches, performance improvements

Examples:
  1.0.0 → Initial release
  1.1.0 → Added dependency scanner
  1.1.1 → Fixed false positive in SQL injection rule
  2.0.0 → New API version, breaking changes
```

## 15.2 Release Process

```
1. Create release branch: release/v1.1.0
2. Final testing on staging
3. Update CHANGELOG.md
4. Create Git tag: v1.1.0
5. Build and push Docker images
6. Deploy to production
7. Smoke test
8. Monitor for 24 hours
9. Merge release branch to main
```

## 15.3 Backward Compatibility

```
Rule: Never break the API without a version bump.

- API v1 is the current version
- Breaking changes go to API v2
- Deprecated endpoints return Sunset header
- Minimum deprecation period: 6 months
```

---

# SECTION 16: Risk Register

## 16.1 Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Database corruption | Critical | Low | Automated backups, soft deletes, migration testing |
| Memory leak in workers | High | Medium | Worker recycling, memory monitoring, limits |
| AI service outage | Medium | High | Fallback to rule-based, graceful degradation |
| Dependency vulnerability | High | Medium | Automated scanning, Dependabot, pinning |
| API breaking change | High | Low | Versioning, backward compatibility, deprecation policy |

## 16.2 Security Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| SQL injection | Critical | Low | Parameterized queries, ORM, input validation |
| JWT token theft | High | Medium | Short expiry, refresh rotation, HTTPS only |
| Rate limit bypass | Medium | Medium | Multiple rate limiting layers, IP + user |
| Secrets in code | Critical | Low | Pre-commit hooks, secret scanning, env vars |
| XSS attack | High | Low | CSP headers, input sanitization, React auto-escaping |

## 16.3 Scalability Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Database bottleneck | High | Medium | Read replicas, connection pooling, caching |
| Queue backlog | Medium | Medium | Auto-scaling workers, priority queues |
| Memory exhaustion | High | Low | Resource limits, monitoring, alerting |
| Cold start latency | Medium | High | Warm pools, connection keep-alive, caching |

## 16.4 AI Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Hallucinated vulnerability | High | Medium | Confidence scoring, human review, validation |
| Prompt injection | High | Low | Input sanitization, output validation, guardrails |
| AI cost overrun | Medium | Medium | Token limits, caching, budget alerts |
| Model deprecation | Low | Low | Abstraction layer, multiple providers |

---

# SECTION 17: Definition of Done

## Feature Completion Checklist

Every feature must satisfy ALL of the following before merging:

### Implementation
- [ ] Code follows coding standards (Section 4)
- [ ] All planned functionality implemented
- [ ] No TODO placeholders in production code
- [ ] No hardcoded values (config where possible)
- [ ] Error handling for all failure modes
- [ ] Input validation on all boundaries
- [ ] Logging at appropriate levels

### Testing
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing
- [ ] Edge cases tested
- [ ] Error states tested
- [ ] No existing tests broken

### Security
- [ ] Authentication enforced (if protected endpoint)
- [ ] Authorization checked (if resource-specific)
- [ ] Input sanitized
- [ ] No secrets in code or logs
- [ ] Rate limiting applied (if public endpoint)

### Performance
- [ ] No N+1 queries
- [ ] Pagination on list endpoints
- [ ] Caching where appropriate
- [ ] No blocking operations in request path

### Documentation
- [ ] API docs updated (if endpoint added/changed)
- [ ] README updated (if new setup step)
- [ ] CHANGELOG updated (if user-facing change)
- [ ] Code comments for non-obvious decisions

### Accessibility (Frontend)
- [ ] Keyboard navigable
- [ ] Screen reader compatible
- [ ] Color contrast meets WCAG AA
- [ ] Focus visible
- [ ] Reduced motion respected

### Review
- [ ] Code reviewed by at least 1 other engineer
- [ ] Security review (if touching auth/data)
- [ ] UI reviewed against design system
- [ ] No merge conflicts

---

# FINAL REVIEW

## Architecture Strengths

1. **Clean separation of concerns** — Each layer has a single responsibility
2. **API-first design** — Enables CLI, IDE extension, and CI/CD integration
3. **Plugin-ready scanners** — New languages/rules without core changes
4. **AI abstraction layer** — Swap between Ollama and OpenAI without code changes
5. **Comprehensive observability** — Logging, metrics, tracing, and audit from day one

## Architecture Weaknesses (Acknowledged)

1. **Single-file models** — Will need splitting at ~50 models
2. **Synchronous scan execution** — Celery workers solve this, but adds complexity
3. **SQLite for dev** — PostgreSQL-specific features won't be tested locally
4. **No event bus** — v1 uses direct service calls; events added in v2
5. **No GraphQL** — REST only; GraphQL considered for v3 if client complexity grows

## Recommendations Before Implementation

1. **Set up CI/CD first** — Before writing any feature code
2. **Write API spec first** — OpenAPI spec before backend implementation
3. **Build the test harness** — pytest fixtures, mocking, and CI integration
4. **Establish the design system** — CSS variables and component library before pages
5. **Deploy to staging early** — Get the deployment pipeline working with a hello-world

---

*This document is the definitive engineering specification for SentinelAI.*  
*It supersedes all previous technical documents.*  
*All engineering decisions must align with this specification.*  
*Last updated: August 20, 2026*
