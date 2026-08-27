# SentinelAI Architecture Diagrams

## System Architecture

```mermaid
graph TB
    subgraph Client["Client Layer"]
        SPA["React SPA<br/>Vite + Framer Motion"]
        PWA["PWA Service Worker"]
        Mobile["Mobile UI<br/>Bottom Nav + Gestures"]
    end

    subgraph Gateway["API Gateway"]
        FastAPI["FastAPI<br/>183 Routes"]
        Middleware["Middleware Stack<br/>CORS · CSRF · Headers · Rate Limit"]
        Auth["Auth Layer<br/>JWT + Refresh + RBAC"]
    end

    subgraph Services["Service Layer"]
        Scanner["Scanner Engine<br/>OWASP API Top 10"]
        SAST["SAST Engine<br/>48 Rules"]
        DepScan["Dependency Scanner<br/>CVE Detection"]
        AI["AI Platform<br/>12 Capabilities"]
        SaaS["SaaS Service<br/>10 Domain Modules"]
        Plugin["Plugin System<br/>6 Interfaces"]
        SRE["SRE Layer<br/>Circuit Breaker · SLA"]
    end

    subgraph Storage["Storage Layer"]
        PG["PostgreSQL<br/>38 Tables"]
        Redis["Redis<br/>Cache · Sessions"]
        FS["File Storage<br/>Reports · Exports"]
    end

    subgraph Observability["Observability"]
        Metrics["Prometheus<br/>30+ Metrics"]
        Logging["Structured Logging<br/>JSON · Correlation IDs"]
        Audit["Audit Trail<br/>Immutable Events"]
    end

    Client --> Gateway
    Gateway --> Services
    Services --> Storage
    Services --> Observability
```

## Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Redis as Redis

    U->>FE: Login (username + password)
    FE->>API: POST /api/auth/login
    
    API->>DB: Query user by username
    DB-->>API: User record
    
    API->>API: bcrypt verify password
    API->>API: Generate JWT access token (JTI + exp)
    API->>DB: Store refresh token (SHA-256 hash)
    API->>Redis: Set refresh cookie (HTTP-only)
    
    API-->>FE: { access_token, user }
    FE->>FE: Store token in memory
    FE->>FE: Set Authorization header

    Note over U,Redis: Subsequent requests

    U->>FE: Navigate to page
    FE->>API: GET /api/... + Bearer token
    
    API->>API: Decode JWT, check JTI blacklist
    API->>DB: Query user, verify active
    API-->>FE: Protected resource

    Note over U,Redis: Token refresh

    FE->>API: POST /api/auth/refresh (cookie)
    
    API->>DB: Validate refresh token hash
    API->>API: Check revocation + expiry
    API->>API: Detect token reuse (theft)
    API->>DB: Revoke old, create new refresh token
    API->>Redis: Set new refresh cookie
    
    API-->>FE: { access_token, user }
```

## Scanner Engine Architecture

```mermaid
graph LR
    subgraph Input["Scan Input"]
        API["API Spec<br/>OpenAPI/Swagger"]
        URL["API Endpoint"]
        Config["Scan Config"]
    end

    subgraph Engine["Scanner Engine"]
        Parser["Spec Parser<br/>YAML · JSON · URL"]
        OWASP["OWASP Checker<br/>21 Rules"]
        Auth["Auth Analyzer<br/>Token Validation"]
        Config2["Config Checker<br/>CORS · Headers"]
        Rate["Rate Limit Detector"]
    end

    subgraph Output["Scan Output"]
        Findings["Findings<br/>Severity + CVSS"]
        Risk["Risk Score<br/>Weighted Algorithm"]
        AI["AI Analysis<br/>Executive Summary"]
    end

    Input --> Parser
    Parser --> OWASP
    Parser --> Auth
    Parser --> Config2
    Parser --> Rate
    OWASP --> Findings
    Auth --> Findings
    Config2 --> Findings
    Rate --> Findings
    Findings --> Risk
    Findings --> AI
```

## AI Platform Architecture

```mermaid
graph TB
    subgraph Interface["AI Interface"]
        Copilot["AI Copilot<br/>Natural Language"]
        Exec["Executive Report<br/>CISO Dashboard"]
        Advisor["Security Advisor<br/>Context-Aware"]
    end

    subgraph Engine["AI Engine"]
        PromptReg["Prompt Registry<br/>Versioned · Validated"]
        KB["Knowledge Base<br/>CWE · OWASP · CVE"]
        RAG["RAG Pipeline<br/>TF-IDF Search"]
        Graph["Knowledge Graph<br/>Attack Paths"]
        Memory["Conversation Memory<br/>Persistent · Entity Extraction"]
    end

    subgraph Validation["Hallucination Prevention"]
        Schema["Schema Validation<br/>Required Fields"]
        Temp["Temperature Control<br/>0.1–0.4"]
        Fallback["Fallback Chain<br/>AI → KB → Rules → Templates"]
        Ground["Data Grounding<br/>Real Scan Data Only"]
    end

    subgraph Providers["LLM Providers"]
        Ollama["Ollama<br/>Local LLM"]
        OpenAI["OpenAI API<br/>GPT-4"]
        Custom["Custom Provider<br/>Via Plugin SDK"]
    end

    Copilot --> Engine
    Exec --> Engine
    Advisor --> Engine
    Engine --> Validation
    Engine --> Providers
```

## Plugin System Architecture

```mermaid
graph TB
    subgraph SDK["Plugin SDK"]
        Scanner["ScannerPlugin<br/>scan() → findings"]
        Report["ReportPlugin<br/>generate() → bytes"]
        AIProv["AIProviderPlugin<br/>complete() → str"]
        Notif["NotificationPlugin<br/>send() → bool"]
        Export["ExportPlugin<br/>export() → bytes"]
        AuthP["AuthProviderPlugin<br/>authenticate() → dict"]
    end

    subgraph Registry["Plugin Registry"]
        Discover["Discovery<br/>File System + DB"]
        Load["Loading<br/>Dynamic Import"]
        Validate["Validation<br/>Manifest + Permissions"]
        Sandboxed["Execution<br/>Timeout + Memory Limits"]
    end

    subgraph Lifecycle["Lifecycle"]
        Install["Install"]
        Enable["Enable"]
        Disable["Disable"]
        Uninstall["Uninstall"]
        Health["Health Check"]
    end

    SDK --> Registry
    Registry --> Lifecycle
```

## SaaS Architecture

```mermaid
graph TB
    subgraph Billing["Billing Layer"]
        Plans["Plans<br/>Free · Pro · Enterprise"]
        Sub["Subscriptions<br/>Active · Past Due · Canceled"]
        Usage["Usage Tracking<br/>Scans · API · Members"]
        Quota["Quota Enforcement<br/>Per-Plan Limits"]
    end

    subgraph Features["Feature Management"]
        Flags["Feature Flags<br/>Plan-Gated · Org-Scoped"]
        License["License Manager<br/>Trial · Enterprise"]
    end

    subgraph Org["Organization Layer"]
        Orgs["Organizations<br/>Multi-Tenant"]
        Teams["Teams<br/>RBAC + Permissions"]
        Projects["Projects<br/>Isolated Scans"]
        Invite["Invitations<br/>Email + Role"]
    end

    subgraph WhiteLabel["White Label"]
        Branding["Custom Branding<br/>Logo · Colors · Domain"]
        Email["Email Templates<br/>Customizable"]
        Onboard["Onboarding Wizard<br/>Step-Based"]
    end

    Plans --> Sub
    Sub --> Usage
    Usage --> Quota
    Flags --> Plans
    Orgs --> Teams
    Teams --> Projects
```

## Data Flow: Scan Lifecycle

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant DB as Database
    participant Scanner as Scanner Engine
    participant AI as AI Platform
    participant WS as WebSocket

    U->>API: POST /api/v1/scans (api_name)
    API->>API: Validate input + RBAC
    API->>DB: INSERT scan (status=pending)
    API-->>U: 201 Created

    API->>WS: Broadcast scan started
    
    API->>Scanner: Execute scan
    Scanner->>Scanner: Parse API spec
    Scanner->>Scanner: Run OWASP checks
    Scanner->>Scanner: Analyze auth
    Scanner->>Scanner: Check config
    
    Scanner->>DB: INSERT findings
    Scanner->>DB: UPDATE scan (status=running)
    Scanner->>WS: Progress update
    
    Scanner->>Scanner: Calculate risk score
    Scanner->>Scanner: Assign severity
    
    Scanner->>DB: UPDATE scan (status=completed, risk_score)
    
    API->>AI: Generate executive summary
    AI->>AI: Validate prompt
    AI->>AI: Knowledge base lookup
    AI->>AI: Generate with fallback
    AI->>AI: Schema validation
    
    AI->>DB: INSERT ai_analysis
    API->>WS: Broadcast scan complete
    
    U->>API: GET /api/v1/scans/{id}
    API->>DB: JOIN scans + findings + ai_analysis
    API-->>U: Complete scan detail
```

## Folder Structure

```
sentinelai/
├── backend/
│   ├── app/
│   │   ├── api/routes/          # 15 route modules (183 endpoints)
│   │   ├── core/
│   │   │   ├── ai_platform/     # AI engine, knowledge base, prompts
│   │   │   ├── copilot/         # AI copilot agent
│   │   │   ├── plugins/         # Plugin SDK, registry, examples
│   │   │   ├── security_engine/ # OWASP scanner
│   │   │   ├── sast_engine/     # Static analysis
│   │   │   └── dep_scanner/     # Dependency scanning
│   │   ├── database/            # Engine, session, query monitor, migrations
│   │   ├── models/              # SQLAlchemy models (4 modules)
│   │   ├── repositories/        # Data access layer
│   │   ├── schemas/             # Pydantic schemas (6 domain modules)
│   │   ├── services/            # Business logic (saas/, audit, etc.)
│   │   ├── utils/               # Security, RBAC, tracing, SLA, etc.
│   │   └── tasks.py             # Background task registry
│   ├── alembic/versions/        # Database migrations
│   ├── tests/                   # 33 test files
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/          # 20+ shared components
│   │   ├── pages/               # 30+ route pages
│   │   ├── contexts/            # Auth, Theme contexts
│   │   └── services/            # API client, config
│   └── Dockerfile
├── docker-compose.yml           # 10-service stack
├── .github/workflows/           # CI/CD pipeline
├── terraform/                   # AWS deployment
└── docs/                        # 14 documentation files
```
