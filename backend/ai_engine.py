import os
import json
import re
from openai import OpenAI
from pydantic import BaseModel


class VulnerabilityExplanation(BaseModel):
    """Structured output for vulnerability explanation"""
    name: str
    severity: str  # Low, Medium, High, Critical
    explanation: str
    impact: str
    fix: str


# 🔥 FIX 1: Safe API key handling
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ OPENAI_API_KEY is missing")

client = OpenAI(api_key=api_key)


def explain_vulnerability(issue: str) -> VulnerabilityExplanation:
    """
    Use OpenAI to analyze and explain a security vulnerability.
    """

    prompt = f"""Analyze this security vulnerability and provide a detailed explanation in JSON format.

Vulnerability Description: {issue}

Please respond with a valid JSON object containing exactly these fields:
- name
- severity (Low, Medium, High, Critical)
- explanation
- impact
- fix

Respond ONLY with the JSON object, no extra text.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a cybersecurity expert. Always return valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=800
        )

        # Extract response
        response_text = response.choices[0].message.content.strip()

        # 🔥 FIX 2: Check empty response
        if not response_text:
            raise ValueError("Empty response from OpenAI")

        # Parse JSON safely
        vulnerability_data = _parse_json_response(response_text)

        # Validate structure
        vulnerability_data = _validate_vulnerability_data(vulnerability_data)

        return VulnerabilityExplanation(**vulnerability_data)

    except Exception as e:
        # 🔥 FIX 3: Show real error in logs
        print("🔥 FULL AI ERROR:", repr(e))

        return VulnerabilityExplanation(
            name="AI Error",
            severity="Low",
            explanation=f"Failed to analyze: {issue}",
            impact="AI processing failed",
            fix="Check backend logs or API configuration"
        )


def _parse_json_response(response_text: str) -> dict:
    """Parse JSON from OpenAI response safely"""

    def try_load_json(text: str):
        try:
            return json.loads(text)
        except:
            return None

    # Try direct parse
    parsed = try_load_json(response_text)
    if parsed:
        return parsed

    # Remove markdown ```json ```
    cleaned = re.sub(r'```json|```', '', response_text, flags=re.IGNORECASE).strip()

    parsed = try_load_json(cleaned)
    if parsed:
        return parsed

    # Extract JSON manually
    match = re.search(r'(\{[\s\S]*\})', cleaned)
    if match:
        parsed = try_load_json(match.group(1))
        if parsed:
            return parsed

    raise ValueError("Could not parse JSON")


def _validate_vulnerability_data(data: dict) -> dict:
    """Validate and sanitize output"""

    defaults = {
        "name": "Security Issue",
        "severity": "Medium",
        "explanation": "A vulnerability was detected.",
        "impact": "Potential risk to system",
        "fix": "Review code"
    }

    for key in defaults:
        if key not in data or not isinstance(data[key], str):
            data[key] = defaults[key]
        else:
            data[key] = data[key].strip()

    valid_severity = ["Low", "Medium", "High", "Critical"]
    if data["severity"] not in valid_severity:
        data["severity"] = "Medium"

    return data