from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from scanner import run_scanner
from ai_engine import explain_vulnerability

app = FastAPI()

# Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all (simple for now)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodeInput(BaseModel):
    code: str

@app.get("/")
def read_root():
    return {"message": "Backend API running successfully"}

@app.post("/scan")
def scan_code(input_data: CodeInput):
    code = input_data.code.strip()

    # Empty input check
    if not code:
        return {
            "error": "No code provided",
            "vulnerabilities": []
        }

    issues = run_scanner(code)

    # No issues found
    if not issues:
        return {
            "message": "No vulnerabilities found ✅",
            "vulnerabilities": []
        }

    results = []
    seen = set()

    for issue in issues:
        try:
            result = explain_vulnerability(issue)

            # remove duplicates
            if result["name"] not in seen:
                seen.add(result["name"])
                results.append(result)

        except Exception:
            results.append({
                "name": "Error",
                "severity": "Low",
                "explanation": issue,
                "impact": "AI failed",
                "fix": "Review manually"
            })

    return {
        "vulnerabilities": results
    }