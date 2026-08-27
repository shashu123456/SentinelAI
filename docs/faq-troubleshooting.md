# SentinelAI — FAQ & Troubleshooting

## Frequently Asked Questions

### General

**Q: What is SentinelAI?**
A: SentinelAI is an AI-powered application security platform that scans APIs, source code, and dependencies for security vulnerabilities. It combines API security testing (OWASP Top 10), static analysis (SAST), dependency scanning (CVE detection), and an AI security copilot.

**Q: Is this a production-ready product?**
A: SentinelAI is a production-inspired platform built with enterprise-grade architecture. It uses PostgreSQL, Redis, structured logging, Prometheus metrics, Kubernetes health checks, and follows clean architecture principles. It's designed to demonstrate real-world engineering quality.

**Q: What programming languages does SentinelAI support?**
A: Backend: Python 3.11. Frontend: React 18 + JavaScript. The SAST engine analyzes Python, JavaScript/TypeScript, and Java source code. The API scanner works with any OpenAPI 3.x or Swagger 2.0 specification regardless of the target language.

---

### Installation & Setup

**Q: How do I install SentinelAI?**
A: Three options:
1. **Docker (recommended):** `cp .env.example .env && docker compose up --build`
2. **Manual:** Set up backend (Python + PostgreSQL + Redis) and frontend (Node.js)
3. **Cloud:** Deploy to Render, Railway, or any Docker-compatible platform

**Q: Do I need Redis?**
A: Redis is recommended for production (token blacklist, dashboard caching) but not required for development. The system falls back to in-memory stores when Redis is unavailable.

**Q: Do I need PostgreSQL?**
A: SQLite works for development. PostgreSQL is recommended for production due to better concurrency, reliability, and performance.

**Q: How do I set up the AI features?**
A: Install Ollama, pull the Mistral model: `ollama pull mistral`, then start the server: `ollama serve`. SentinelAI works without Ollama using rule-based fallback.

**Q: What ports does SentinelAI use?**
A: Backend: 8000, Frontend: 5173 (dev) or 80 (Docker), PostgreSQL: 5432, Redis: 6379, Prometheus: 9090, Grafana: 3001.

---

### Scanning

**Q: What file formats can I scan?**
A: API Scanner: OpenAPI 3.x / Swagger 2.0 (.json, .yaml, .yml). SAST: .py, .js, .jsx, .ts, .tsx, .java, .zip. Dependency Scanner: requirements.txt, package.json, pom.xml.

**Q: How many findings can a single scan produce?**
A: No hard limit. The API scanner checks 10 OWASP categories against all endpoints. A spec with 100 endpoints might produce 50-200 findings depending on the security posture.

**Q: Can I scan non-OpenAPI APIs?**
A: Currently, SentinelAI requires an OpenAPI/Swagger specification. You can generate one from existing APIs using tools like Swagger Inspector, Postman, or code annotations (e.g., FastAPI auto-generates OpenAPI).

**Q: What's the difference between Live Scan and Instant Scan?**
A: Live Scan uses WebSocket for real-time progress updates (you see each OWASP check running). Instant Scan runs silently and returns results when complete. Both produce identical results.

**Q: How accurate are the vulnerability findings?**
A: Each finding includes a confidence score (40-95%). Higher confidence means the scanner is more certain. The scanner is designed to minimize false positives. It's better to miss something than to raise false alarms.

**Q: Can I scan multiple APIs at once?**
A: Yes, you can run multiple scans concurrently. Each scan is independent. Use the async scan endpoint (`/api/scans/upload/async`) for background processing.

---

### AI Copilot

**Q: Does the AI Copilot send data to external services?**
A: When using Ollama (local AI), no data leaves your machine. When Ollama is unavailable, the copilot uses rule-based templates — no external calls. If you configure a cloud AI provider, only scan findings are sent (not source code).

**Q: What can I ask the AI Copilot?**
A: Natural language questions about your security findings:
- "What is my highest risk issue?"
- "How do I fix the BOLA vulnerability?"
- "Generate an executive summary"
- "How would an attacker exploit this?"
- "Map my findings to OWASP Top 10"
- "Compare my last two scans"

**Q: Why does the AI sometimes give generic responses?**
A: The copilot loads your actual scan data for context-aware responses. If no scans exist, responses are necessarily generic. Run a scan first, then ask the copilot about your findings.

---

### Reports

**Q: What's included in the PDF report?**
A: Cover page, executive summary, risk score visualization, severity distribution, detailed findings with CWE mapping, AI-generated analysis, and remediation recommendations.

**Q: Can I customize the report?**
A: Currently, reports use a fixed professional template. Custom branding and templates are on the roadmap.

---

### Deployment

**Q: How do I deploy to production?**
A: See the [Developer Guide](developer-guide.md#deployment) for detailed instructions. Quick version:
```bash
cp .env.example .env  # Set SECRET_KEY, POSTGRES_PASSWORD
docker compose up -d --build
./scripts/smoke-test.sh
```

**Q: How do I enable HTTPS?**
A: Place a reverse proxy (nginx, Cloudflare, AWS ALB) in front of SentinelAI. Set `REFRESH_TOKEN_COOKIE_SECURE=true` and configure HSTS headers.

**Q: How do I set up monitoring?**
A: Enable the observability profile: `docker compose --profile observability up -d`. This starts Prometheus (scraping `/metrics`) and Grafana (pre-configured datasource).

---

## Troubleshooting

### Installation Issues

**Problem:** `pip install -r requirements.txt` fails
```
error: Microsoft Visual C++ 14.0 is required
```
**Solution:** Install Microsoft C++ Build Tools, or use `--only-binary=:all:` to skip source builds:
```bash
pip install --only-binary=:all: -r requirements.txt
```

**Problem:** `npm install` fails with peer dependency errors
```
npm ERR! ERESOLVE unable to resolve dependency tree
```
**Solution:** Use `--legacy-peer-deps` or `npm install --force`:
```bash
npm install --legacy-peer-deps
```

**Problem:** Alembic migration fails
```
alembic.util.exc.CommandError: Can't locate revision identified by 'abc123'
```
**Solution:** Stamp to head and re-run:
```bash
alembic stamp head
alembic upgrade head
```

---

### Runtime Issues

**Problem:** `database is locked` error
```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) database is locked
```
**Solution:** Only one process can write to SQLite at a time. Either:
1. Stop other processes using the database
2. Switch to PostgreSQL for production
3. Enable WAL mode: `PRAGMA journal_mode=WAL;`

**Problem:** CORS error in browser console
```
Access to XMLHttpRequest blocked by CORS policy
```
**Solution:** Ensure `CORS_ORIGINS` in `.env` includes your frontend URL:
```bash
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

**Problem:** Token expired immediately after login
**Solution:** Check that `ACCESS_TOKEN_EXPIRE_MINUTES` is set correctly (default: 60). Ensure the frontend is handling token refresh properly.

**Problem:** `Redis unavailable` warning in logs
**Solution:** Start Redis: `docker compose up -d redis`. Without Redis, the token blacklist uses in-memory storage (doesn't survive restarts).

**Problem:** WebSocket connection fails
**Solution:** Ensure nginx is configured to proxy WebSocket connections:
```nginx
location /ws/ {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

---

### Scanner Issues

**Problem:** Scan returns 0 findings for a clearly vulnerable API
**Solution:** The scanner checks the OpenAPI *specification*, not the running API. Ensure your spec accurately describes your endpoints, parameters, and security schemes.

**Problem:** "Invalid specification format" error
**Solution:** Ensure:
1. File is valid JSON or YAML
2. Contains `openapi: "3.x.x"` or `swagger: "2.0"` at the root
3. File is UTF-8 encoded
4. File size is under 5MB

**Problem:** SAST scan doesn't detect expected vulnerabilities
**Solution:** The SAST engine uses pattern-based rules. Check that:
1. The code matches the rule patterns (regex-based)
2. The file extension is supported (.py, .js, .java)
3. The vulnerability isn't behind complex control flow

---

### AI Issues

**Problem:** AI analysis shows "Rule-based fallback" instead of AI-generated content
**Solution:** Ollama isn't running or unreachable. Start it:
```bash
ollama serve  # Default: http://localhost:11434
```

**Problem:** AI responses are slow (10+ seconds)
**Solution:** First request is slow as the model loads. Subsequent requests are faster. Consider:
1. Using a smaller model (e.g., `tinyllama`)
2. Increasing Ollama's context window
3. Running on a machine with more RAM/GPU

**Problem:** AI gives irrelevant responses
**Solution:** The AI copilot needs scan context. Run a scan first, then ask questions. The copilot loads your actual findings for context-aware responses.

---

### Performance Issues

**Problem:** Dashboard loads slowly
**Solution:** 
1. Enable Redis caching: `REDIS_URL=redis://localhost:6379/0`
2. Add database indexes (already included in migrations)
3. Reduce `page_size` for large datasets

**Problem:** Scan takes too long
**Solution:**
1. Use async scan mode (`/api/scans/upload/async`)
2. Check Ollama response time (AI analysis is the slowest step)
3. Reduce the size of the OpenAPI spec

**Problem:** High memory usage
**Solution:**
1. Check for memory leaks in long-running processes
2. Set `--workers 2` for uvicorn (not too many)
3. Use Docker resource limits: `deploy.resources.limits.memory: 512M`

---

### Docker Issues

**Problem:** `docker compose up` fails to build
**Solution:**
1. Ensure Docker is running
2. Check disk space: `docker system df`
3. Clean old images: `docker system prune`
4. Check build logs for specific errors

**Problem:** Services can't communicate
**Solution:** Ensure all services are on the same Docker network. The `docker-compose.yml` defines a `sentinelai` network for inter-service communication.

**Problem:** PostgreSQL refuses connections
**Solution:** Wait for the health check to pass (10-15 seconds). If persistent, check:
1. `POSTGRES_PASSWORD` matches between backend and postgres service
2. Database volume has correct permissions
3. No other process is using port 5432

---

### Deployment Issues

**Problem:** Render deployment fails health check
**Solution:** Ensure `alembic upgrade head` runs during build. Check that `DATABASE_URL` is set correctly in Render environment.

**Problem:** Railway deployment can't connect to database
**Solution:** Use Railway's PostgreSQL plugin and reference it via `fromDatabase` in the environment variables.

**Problem:** Vercel frontend can't reach backend API
**Solution:** Update `vercel.json` rewrites to point to your actual backend URL. Set `VITE_API_URL` environment variable in Vercel.

---

## Getting Help

1. Check this FAQ and troubleshooting guide
2. Review the [Architecture Documentation](architecture.md)
3. Check the [Developer Guide](developer-guide.md)
4. Search existing GitHub Issues
5. Open a new GitHub Issue with:
   - SentinelAI version
   - Python/Node.js version
   - OS
   - Steps to reproduce
   - Error logs
