# SentinelAI Architecture

## System Overview

SentinelAI follows a layered architecture with clear separation of concerns:

```
Client (React) → API Layer (FastAPI) → Core Engines → Database
```

## Frontend Architecture

- **React 18** with functional components and hooks
- **React Router 6** for client-side routing with protected routes
- **Vite 6** as build tool with API proxy configuration
- **Context API** for authentication state management

### Pages
- **Login/Register**: JWT-based authentication
- **Dashboard**: Statistics cards, severity distribution, recent scans table
- **New Scan (API Scanner)**: Drag-and-drop OpenAPI upload with live/instant mode selection
- **SAST Scanner**: Source code upload for static analysis (Python/JS/Java)
- **Dependency Scanner**: Package manifest upload for CVE detection
- **Security Copilot**: AI chat interface with context-aware security reasoning
- **Live Scan**: WebSocket-driven terminal with real-time progress
- **Scan Results**: Risk circle, severity cards, AI analysis, finding details

## Backend Architecture

### API Layer
- **FastAPI** with automatic OpenAPI documentation
- **Rate limiting** via slowapi (30 req/min per IP)
- **CORS** configured for development origins
- **Request logging** middleware with timing

### Core Engines

#### Parser (`core/security_engine/parser.py`)
- Resolves `$ref` JSON pointers
- Extracts endpoints, methods, parameters, request bodies
- Determines per-endpoint authentication requirements
- Extracts security schemes from components

#### Scanner (`core/security_engine/scanner.py`)
- 10 independent OWASP Top 10 check functions
- Pattern-based detection with confidence scoring
- CWE mapping for each finding category
- Evidence collection with detection reasoning

#### Risk Engine (`core/risk_engine/scorer.py`)
- Weighted severity scoring (Critical=25, High=15, Medium=8, Low=3, Info=1)
- Normalized to 0-100 scale
- Floor rules: Critical >= 80, High >= 60, Medium >= 30

#### AI Engine (`core/ai_engine/analyzer.py`)
- Ollama integration with Mistral model
- Structured prompt for 5-field analysis output
- Multi-layer JSON response parsing
- Rule-based fallback when LLM unavailable

#### SAST Engine (`core/sast_engine/`)
- 40+ regex-based security rules across Python, JavaScript, Java
- Pattern matching for SQL injection, command injection, hardcoded secrets, weak crypto, XSS, path traversal
- Line-level findings with CWE mapping and confidence scores
- Skips node_modules, venv, __pycache__ automatically

#### Dependency Scanner (`core/dep_scanner/`)
- Parses requirements.txt, package.json, pom.xml
- Curated CVE database with 50+ known vulnerabilities
- Semantic version comparison to determine affected packages
- Covers critical packages: Django, Flask, Spring, lodash, axios, etc.

#### Security Copilot (`core/copilot/`)
- Context-aware security reasoning system (not a generic chatbot)
- Maintains conversation history and scan context
- Intent classification: explain, remediate, executive summary, attack analysis, compliance
- Ollama integration with rule-based fallback
- Loads scan findings, SAST results, and dependency data for contextual analysis

### Data Layer
- **SQLAlchemy ORM** with declarative base
- **SQLite** for development (PostgreSQL-ready)
- Models: User, Scan, Finding, AIAnalysis
- Cascade deletes for data integrity

### Background Tasks
- **asyncio** task management for async scans
- **WebSocket** progress publishing
- In-memory task store with subscriber pattern

### Report Generation
- **ReportLab** for PDF generation
- Professional card-based layout
- Page headers/footers with numbering
- Confidential disclaimer

## Data Flow

### Sync Scan
```
Upload → Parse Spec → Run OWASP Checks → Calculate Risk → AI Analysis → Save to DB → Return Results
```

### Async (Live) Scan
```
Upload → Create Task → Spawn Background Task → Return Task ID
                                                  ↓
Client ← WebSocket ← Progress Updates ← Publish Progress
                                                  ↓
Client → "View Results" → GET /api/scans/{id} → Display
```

## Security Design

- Password hashing via bcrypt
- JWT tokens with 60-minute expiration
- OAuth2PasswordBearer for API auth
- Rate limiting per IP address
- File upload validation (type, size, encoding)
- Input validation via Pydantic models
