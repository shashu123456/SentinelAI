# API Flow

## Authentication Flow

### Registration
```
POST /api/auth/register
Body: { username, email, password }
Response: { access_token, token_type, user }
```

### Login
```
POST /api/auth/login
Body: { username, password }
Response: { access_token, token_type, user }
```

### Authenticated Requests
```
Header: Authorization: Bearer <token>
Token expiry: 60 minutes
```

## Scan Flows

### Synchronous Scan
```
Client → POST /api/scans/upload (multipart: file, api_name)
Server → Parse file → Run scan → Calculate risk → AI analysis → Save to DB
Client ← ScanResponse with all results
```

### Asynchronous (Live) Scan
```
Client → POST /api/scans/upload/async (multipart: file, api_name)
Server → Create ScanTask → Spawn asyncio task → Return task_id
Client ← { task_id }

Client → WS /ws/scan/{task_id}
Server → Streams progress JSON at each stage:
  - Parsing specification (15%)
  - Each OWASP check (35-72%)
  - Risk scoring (75%)
  - AI analysis (85%)
  - Complete (100%)
Client receives: { task_id, status, progress, message, scan_id }

Client → GET /api/scans/{scan_id} (with findings + AI analysis)
```

## Dashboard Flow
```
GET /api/scans/dashboard
Response: {
  total_scans,
  total_vulnerabilities,
  average_risk_score,
  recent_scans[],
  severity_distribution: { Critical, High, Medium, Low, Info }
}
```

## Report Generation
```
GET /api/scans/{id}/report/pdf
→ Returns PDF with: Cover page, Executive summary, Findings, AI analysis

GET /api/scans/{id}/report/json
→ Returns JSON with all scan data
```

## Rate Limiting
- 30 requests per minute per IP address
- Exceeding returns 429 Too Many Requests
