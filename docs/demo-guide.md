# Demo Guide

## Interview Demo Workflow

### Step 1: Start the Application
```bash
# Terminal 1 - Backend
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### Step 2: Register and Login
- Open http://localhost:5173
- Click "Register" tab
- Enter username, email, password
- Click "Create Account"
- Redirects to Dashboard

### Step 3: Upload Vulnerable API
- Click "New Scan" in navigation
- Drag and drop `samples/vulnerable_api.yaml`
- Ensure "Live Scan" mode is selected
- Click "Start Live Scan"

### Step 4: Watch Real-Time Progress
- Terminal view shows WebSocket connection
- Progress bar advances through each OWASP check
- Log lines show each security check running
- Completion shows scan ID, vulnerabilities, risk score

### Step 5: Review Findings
- Click "View Full Results"
- Review risk score circle visualization
- Check severity distribution cards
- Expand individual findings to see:
  - CWE mapping
  - Confidence score
  - Detection reason
  - Evidence
  - Impact
  - Remediation

### Step 6: Review AI Analysis
- Scroll to "AI Security Analysis" section
- Review Executive Summary, Technical Analysis, Business Impact
- Note: If Ollama is not running, rule-based fallback analysis is shown

### Step 7: Download Report
- Click "PDF Report" button
- Open downloaded PDF
- Show professional report with cover page, findings, AI analysis

### Step 8: Compare with Secure API
- Return to Dashboard
- Upload `samples/secure_api.yaml` using Instant Scan
- Show dramatically lower risk score
- Demonstrate the before/after comparison

## Key Talking Points

1. **"Every finding has a confidence score"** - Shows sophisticated detection, not just binary matching
2. **"CWE mapping enables integration with vulnerability management platforms"** - Industry standard
3. **"The risk engine uses floor rules"** - A single Critical finding always produces a high score
4. **"Ollama integration means no data leaves the machine"** - Privacy-first AI analysis
5. **"The scanner is modular - each OWASP category is independent"** - Extensible architecture

## Fallback Behavior

If Ollama is not available:
- Scans still complete successfully
- AI analysis uses rule-based templates
- All other features (scoring, reporting, PDF) work normally
- Console shows: "AI analysis unavailable. SentinelAI continues using rule-based security analysis."
