# SentinelAI — User Guide

## Getting Started

### Create Your Account

1. Open SentinelAI in your browser
2. Click **Register** on the login page
3. Enter username, email, and password
4. Click **Create Account**
5. You'll be redirected to the Dashboard

### First Scan

1. Click **API Scanner** in the sidebar
2. Drag and drop your OpenAPI/Swagger spec (`.yaml` or `.json`)
3. Choose **Live Scan** for real-time progress or **Instant Scan** for quick results
4. Click **Start Scan**
5. Review findings when the scan completes

---

## API Security Scanner

### How It Works

The API Scanner analyzes your OpenAPI specification against the **OWASP API Security Top 10**. It checks for:

| Check | What It Finds |
|-------|---------------|
| API1 - BOLA | Endpoints with `{id}` parameters that lack user-scoping |
| API2 - Broken Auth | State-changing endpoints without authentication |
| API3 - Property Auth | Request bodies containing sensitive fields (passwords, secrets) |
| API4 - Resource Abuse | Collection endpoints without pagination |
| API5 - Function Auth | Admin/internal/debug endpoints accessible to regular users |
| API6 - Business Flow | Payment/order endpoints without proper controls |
| API7 - SSRF | URL-type parameters that could enable server-side request forgery |
| API8 - Misconfiguration | Missing security schemes, no global auth requirements |
| API9 - Inventory | Multiple API versions, deprecated endpoints |
| API10 - Unsafe APIs | External URL properties in request bodies |

### Reading Results

Each finding includes:

- **Severity**: Critical, High, Medium, Low, Info
- **Confidence**: How confident the scanner is (40-95%)
- **CWE ID**: Industry-standard weakness identifier
- **OWASP Category**: Maps to OWASP API Security Top 10
- **Endpoint**: Which API endpoint is affected
- **Description**: What the vulnerability is
- **Impact**: What could happen if exploited
- **Remediation**: How to fix it

### Risk Score

Your risk score (0-100) is calculated using:

- **Severity weights**: Critical findings score highest
- **Floor rules**: A single Critical finding always produces a score ≥ 80
- **Normalization**: Scores are scaled to 0-100

| Score | Risk Level | Action |
|-------|-----------|--------|
| 80-100 | Critical | Immediate remediation required |
| 60-79 | High | Address before next deployment |
| 30-59 | Medium | Plan remediation in current sprint |
| 10-29 | Low | Address during maintenance |
| 0-9 | Low Risk | No immediate action needed |

---

## SAST Scanner

### Supported Languages

| Language | File Types | Rules |
|----------|-----------|-------|
| Python | `.py` | SQL injection, command injection, hardcoded secrets, weak crypto, path traversal, unsafe deserialization |
| JavaScript | `.js`, `.jsx`, `.ts`, `.tsx` | XSS, SQL injection, eval usage, hardcoded secrets, prototype pollution |
| Java | `.java` | SQL injection, command injection, deserialization, SSRF, XXE |

### How to Use

1. Click **SAST Analysis** in the sidebar
2. Upload a source code file or drag and drop
3. View line-level findings with exact code locations

### Understanding Findings

Each SAST finding shows:

- **File + Line**: Exact location in your code
- **Line Content**: The actual code that triggered the rule
- **Rule**: Which security rule was matched
- **CWE**: Industry-standard weakness identifier
- **Confidence**: How confident the detection is
- **Remediation**: Specific fix for this vulnerability

---

## Dependency Scanner

### Supported Formats

| Format | File |
|--------|------|
| Python | `requirements.txt`, `Pipfile` |
| JavaScript | `package.json` |
| Java | `pom.xml` |

### What It Checks

Cross-references your dependencies against a curated database of **70+ known CVEs** covering critical packages like:

- Django, Flask, Requests (Python)
- lodash, axios, Express (JavaScript)
- Spring, Apache Commons (Java)

### Reading Results

Each finding shows:

- **Package**: The vulnerable dependency
- **Installed Version**: Your current version
- **Severity**: Critical, High, Medium
- **CVSS Score**: Industry-standard severity score
- **CVE ID**: The specific vulnerability identifier
- **Fixed In**: The version that patches the vulnerability

---

## AI Security Copilot

### What It Does

The AI Copilot is a context-aware security assistant that understands your scan findings. It can:

- Explain vulnerabilities in plain language
- Generate executive summaries for leadership
- Create prioritized remediation plans
- Analyze attack paths and scenarios
- Map findings to compliance frameworks (OWASP, CWE)

### How to Use

1. Click **AI Copilot** in the sidebar
2. Type your question naturally:
   - "What is my highest risk issue?"
   - "How do I fix the BOLA vulnerability?"
   - "Generate an executive summary"
   - "How would an attacker exploit this?"
   - "Map my findings to OWASP Top 10"

### Context-Aware Responses

The copilot loads your actual scan data and provides responses grounded in your findings — not generic security advice.

---

## Dashboard

### Overview

The dashboard shows:

- **Total Scans**: Number of scans performed
- **Total Vulnerabilities**: Sum of all findings
- **Average Risk Score**: Mean risk across all scans
- **Severity Distribution**: Donut chart of Critical/High/Medium/Low/Info
- **Scan Activity**: Bar chart of scans over the last 30 days
- **Risk Trend**: Line chart of risk scores over time
- **OWASP Distribution**: Bar chart of findings by OWASP category
- **Recent Scans**: Table of latest scans with risk scores

### Quick Access

The dashboard provides quick access cards to:

- **New Scan** — Upload an API spec
- **SAST Scan** — Analyze source code
- **Dependency Scan** — Check packages
- **AI Copilot** — Ask security questions

---

## Reports

### PDF Reports

Professional security reports including:

- Cover page with scan metadata
- Executive summary
- Risk score visualization
- Severity distribution
- Detailed findings with CWE mapping
- AI-generated analysis
- Remediation recommendations

### JSON Reports

Machine-readable reports for integration with:

- SIEM systems
- Vulnerability management platforms
- Custom dashboards
- CI/CD pipelines

---

## Settings

### Organization Management

1. Click **Settings** in the sidebar
2. Go to **Organization** tab
3. Click **New Organization**
4. Enter name and slug
5. Invite team members via **Team** tab

### Project Management

1. Go to **Projects** tab in Settings
2. Click **New Project**
3. Select the organization
4. Enter project name and description

### Profile

View and manage your account information under the **Profile** tab.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `⌘K` / `Ctrl+K` | Open command palette |
| `G` then `D` | Go to Dashboard |
| `G` then `N` | Go to New Scan |
| `G` then `S` | Go to SAST Scanner |
| `G` then `V` | Go to Vulnerabilities |
| `G` then `C` | Go to AI Copilot |
| `G` then `R` | Go to Reports |
| `G` then `A` | Go to Audit Center |
| `G` then `H` | Go to System Health |
| `?` | Show keyboard shortcuts |
| `Esc` | Close modals/panels |

---

## FAQ

### Q: Do I need Ollama for the AI features?

**A:** No. When Ollama is unavailable, SentinelAI falls back to rule-based analysis. You'll still get executive summaries, remediation plans, and attack analysis — they just use templates instead of an LLM.

### Q: What OpenAPI versions are supported?

**A:** OpenAPI 3.x and Swagger 2.0 in both JSON and YAML formats.

### Q: Can I scan non-OpenAPI APIs?

**A:** Currently, SentinelAI requires an OpenAPI/Swagger specification. For REST APIs without specs, consider generating one from your code (tools like Swagger Inspector can help).

### Q: How accurate are the findings?

**A:** Each finding has a confidence score (40-95%). Higher confidence means the scanner is more certain. The scanner is designed to minimize false positives — it's better to miss something than to flag a false alarm.

### Q: Is my data secure?

**A:** Yes. All data is stored locally (or in your database). AI analysis via Ollama runs entirely on your machine — no data is sent to external services. If using cloud AI, only the scan findings are sent, not your source code.

### Q: Can I export findings to other tools?

**A:** Yes. JSON exports are compatible with most vulnerability management platforms. PDF reports can be shared with stakeholders.

---

## Troubleshooting

### Scan fails to start

1. Verify the file is a valid OpenAPI/Swagger spec
2. Check the file isn't empty or corrupted
3. Ensure the file is UTF-8 encoded
4. Try uploading a sample spec from `samples/`

### AI Copilot gives generic responses

1. Ensure Ollama is running (`ollama serve`)
2. Verify the model is pulled (`ollama pull mistral`)
3. Check the backend can reach Ollama (`curl http://localhost:11434`)
4. The copilot works without Ollama but uses rule-based fallback

### Charts show "No data"

1. Run at least one scan to generate data
2. Check the `/api/scans/analytics` endpoint returns data
3. Clear browser cache and reload

### Rate limit errors (429)

1. Wait 1 minute before retrying
2. Check if you're making too many concurrent requests
3. In production, rate limits are per-user (not per-IP)

---

## Known Issues

1. **Large specs may timeout** — Specs with 500+ endpoints may exceed the 120s timeout. Use async scan mode for large APIs.
2. **SQLite limitations** — The development database doesn't support concurrent writes. Use PostgreSQL for production.
3. **Ollama cold start** — First AI request may take 10-30 seconds as the model loads into memory.
4. **WebSocket reconnection** — If the WebSocket disconnects during a scan, refresh the page to reconnect.

---

## Future Roadmap

See [ROADMAP.md](ROADMAP.md) for the complete product roadmap.

### Coming Soon

- **Container Security** — Docker image scanning
- **IaC Security** — Terraform/CloudFormation analysis
- **Runtime Protection** — Real-time API monitoring
- **SSO Integration** — SAML/OIDC authentication
- **Compliance Reports** — SOC2, ISO27001, PCI DSS templates
- **API Discovery** — Automatic API inventory from network traffic
- **Predictive Analytics** — ML-based vulnerability forecasting
