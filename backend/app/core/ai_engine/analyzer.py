import json
import urllib.request
import urllib.error
from app.config import get_settings
from app.utils.logger import logger

settings = get_settings()


def analyze_vulnerabilities(findings: list[dict], api_info: dict) -> dict | None:
    if not findings:
        return None

    findings_summary = _format_findings_for_prompt(findings)
    api_context = (
        f"API: {api_info.get('title', 'Unknown')} v{api_info.get('version', '?')}\n"
        f"Total endpoints: {api_info.get('total_endpoints', 0)}"
    )

    prompt = f"""You are a senior security analyst. Analyze the following API security scan results and provide a comprehensive security assessment.

{api_context}

Detected Vulnerabilities:
{findings_summary}

Provide your analysis as a JSON object with exactly these keys:
- executive_summary: A 2-3 sentence overview for C-level executives
- technical_explanation: Detailed technical breakdown of the findings
- business_impact: How these vulnerabilities affect the business
- attack_scenario: A realistic attack scenario exploiting these vulnerabilities
- recommended_mitigation: Prioritized list of mitigation steps

Return ONLY valid JSON, no markdown fences, no extra text."""

    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    try:
        response_text = _call_ollama(payload)
        if response_text:
            parsed = _parse_response(response_text)
            if parsed:
                return {
                    "executive_summary": parsed.get("executive_summary", ""),
                    "technical_explanation": parsed.get("technical_explanation", ""),
                    "business_impact": parsed.get("business_impact", ""),
                    "attack_scenario": parsed.get("attack_scenario", ""),
                    "recommended_mitigation": parsed.get("recommended_mitigation", ""),
                }
    except Exception as e:
        logger.warning(f"AI analysis failed: {e}")

    return _generate_fallback_analysis(findings, api_info)


def _call_ollama(payload: dict) -> str | None:
    request_data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        settings.OLLAMA_URL,
        data=request_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.read().decode("utf-8")
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        logger.warning(f"Ollama request failed: {e}")
        return None


def _parse_response(response_text: str) -> dict | None:
    parsed = None
    try:
        parsed = json.loads(response_text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    json_text = _extract_json_object(response_text)
    if json_text:
        try:
            parsed = json.loads(json_text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return None


def _extract_json_object(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for index, char in enumerate(text[start:], start):
        if char == '"' and not escape:
            in_string = not in_string
        if in_string and char == "\\" and not escape:
            escape = True
            continue
        escape = False

        if not in_string:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]

    return None


def _format_findings_for_prompt(findings: list[dict]) -> str:
    lines = []
    for i, f in enumerate(findings, 1):
        lines.append(
            f"{i}. [{f.get('severity', 'Unknown')}] {f.get('vulnerability_name', 'Unknown')}\n"
            f"   Category: {f.get('owasp_category', 'N/A')}\n"
            f"   Description: {f.get('description', 'N/A')}\n"
            f"   Impact: {f.get('impact', 'N/A')}\n"
        )
    return "\n".join(lines)


def _generate_fallback_analysis(findings: list[dict], api_info: dict) -> dict:
    critical_high = [f for f in findings if f.get("severity") in ("Critical", "High")]
    categories = set(f.get("owasp_category", "") for f in findings)

    return {
        "executive_summary": (
            f"The security scan of '{api_info.get('title', 'the API')}' identified "
            f"{len(findings)} vulnerabilities across {len(categories)} OWASP categories. "
            f"{len(critical_high)} findings are rated Critical or High severity and require immediate attention."
        ),
        "technical_explanation": (
            f"The automated scan analyzed {api_info.get('total_endpoints', 0)} endpoints "
            f"and detected issues spanning OWASP API Security Top 10 categories: "
            f"{', '.join(sorted(categories))}. "
            + " ".join(f.get("description", "") for f in critical_high[:3])
        ),
        "business_impact": (
            f"With {len(critical_high)} critical/high severity findings, "
            "the API is at significant risk of data breaches, unauthorized access, "
            "and compliance violations. Immediate remediation is recommended."
        ),
        "attack_scenario": (
            "An attacker could exploit the identified authentication and authorization "
            "weaknesses to access unauthorized data, manipulate business flows, "
            "and potentially gain administrative access to the system."
        ),
        "recommended_mitigation": (
            "1. Address all Critical and High severity findings immediately.\n"
            "2. Implement proper authentication and authorization on all endpoints.\n"
            "3. Add input validation and rate limiting.\n"
            "4. Conduct a follow-up penetration test after remediation.\n"
            "5. Establish ongoing API security monitoring."
        ),
    }


def explain_single_finding(finding: dict) -> dict:
    prompt = (
        "You are a cybersecurity expert. Analyze this API security finding and return "
        "a JSON object with keys: name, severity, explanation, impact, remediation.\n\n"
        f"Finding: {finding.get('vulnerability_name', 'Unknown')}\n"
        f"Category: {finding.get('owasp_category', 'Unknown')}\n"
        f"Description: {finding.get('description', '')}\n"
    )

    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    try:
        response_text = _call_ollama(payload)
        if response_text:
            parsed = _parse_response(response_text)
            if parsed:
                return parsed
    except Exception as e:
        logger.warning(f"Single finding analysis failed: {e}")

    return {
        "name": finding.get("vulnerability_name", "Security Finding"),
        "severity": finding.get("severity", "Medium"),
        "explanation": finding.get("description", ""),
        "impact": finding.get("impact", ""),
        "remediation": finding.get("remediation", ""),
    }
