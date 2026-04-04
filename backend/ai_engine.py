import os
import json
import re
from openai import OpenAI
from pydantic import BaseModel, ValidationError


class VulnerabilityExplanation(BaseModel):
    """Structured output for vulnerability explanation"""
    name: str
    severity: str  # Low, Medium, High, Critical
    explanation: str
    impact: str
    fix: str


# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def explain_vulnerability(issue: str) -> VulnerabilityExplanation:
    """
    Use OpenAI to analyze and explain a security vulnerability.

    Args:
        issue: A string describing the discovered security issue

    Returns:
        VulnerabilityExplanation: Structured output with name, severity,
                                  explanation, impact, and recommended fix
    """

    prompt = f"""Analyze this security vulnerability and provide a detailed explanation in JSON format.

Vulnerability Description: {issue}

Please respond with a valid JSON object containing exactly these fields:
- name: A short, descriptive name for the vulnerability type
- severity: One of "Low", "Medium", "High", or "Critical"
- explanation: A clear explanation of what this vulnerability is and how it works
- impact: The potential consequences and damage this vulnerability could cause
- fix: Specific, actionable steps to fix or prevent this vulnerability

Respond ONLY with the JSON object, no additional text or formatting."""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a cybersecurity expert. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=1000
        )

        # Extract the response content
        response_text = response.choices[0].message.content.strip()

        # Parse JSON with multiple fallback strategies
        vulnerability_data = _parse_json_response(response_text)

        # Validate and sanitize the data
        vulnerability_data = _validate_vulnerability_data(vulnerability_data)

        # Create and return the validated model
        return VulnerabilityExplanation(**vulnerability_data)

    except Exception as e:
        # Fallback for any errors
        print(f"Error analyzing vulnerability: {str(e)}")
        return VulnerabilityExplanation(
            name="Analysis Error",
            severity="Unknown",
            explanation=f"Could not analyze vulnerability: {issue}",
            impact="Unable to determine potential impact due to analysis error",
            fix="Please review the code manually or try again later"
        )


def _parse_json_response(response_text: str) -> dict:
    """
    Parse JSON from OpenAI response with multiple fallback strategies.

    Args:
        response_text: The raw text response from OpenAI

    Returns:
        dict: Parsed JSON data

    Raises:
        ValueError: If JSON cannot be parsed
    """
    def try_load_json(text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def clean_json_string(json_str: str) -> str:
        json_str = json_str.strip()
        json_str = json_str.replace('\r\n', '\n').replace('\r', '\n')
        json_str = re.sub(r'```json\s*|```\s*|```', '', json_str, flags=re.IGNORECASE)
        return json_str.strip()

    # Strategy 1: Direct JSON parsing
    parsed = try_load_json(response_text)
    if parsed is not None:
        return parsed

    # Strategy 2: Extract JSON from fenced code blocks or raw text
    json_patterns = [
        r'```json\s*(\{[\s\S]*?\})\s*```',  # JSON fenced code block
        r'```\s*(\{[\s\S]*?\})\s*```',       # Generic fenced code block
        r'(\{[\s\S]*\})',                     # Raw JSON object
    ]

    for pattern in json_patterns:
        match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
        if match:
            json_str = clean_json_string(match.group(1))
            parsed = try_load_json(json_str)
            if parsed is not None:
                return parsed

            # Try a simple cleanup for trailing commas and duplicate whitespace
            repaired = re.sub(r',\s*([}\]])', r'\1', json_str)
            parsed = try_load_json(repaired)
            if parsed is not None:
                return parsed

    # Strategy 3: Fallback content cleanup and raw extraction
    cleaned = response_text.replace('\n', ' ').replace('\r', ' ')
    match = re.search(r'(\{[\s\S]*\})', cleaned)
    if match:
        json_str = clean_json_string(match.group(1))
        parsed = try_load_json(json_str)
        if parsed is not None:
            return parsed

        repaired = re.sub(r',\s*([}\]])', r'\1', json_str)
        parsed = try_load_json(repaired)
        if parsed is not None:
            return parsed

    raise ValueError(f"Could not parse valid JSON from response: {response_text[:200]}")


def _validate_vulnerability_data(data: dict) -> dict:
    """
    Validate and sanitize vulnerability data, filling in defaults.

    Args:
        data: The parsed JSON data

    Returns:
        dict: Validated and sanitized data
    """
    # Ensure it's a dictionary
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict, got {type(data).__name__}")

    # Define defaults
    defaults = {
        "name": "Security Issue",
        "severity": "Medium",
        "explanation": "A security vulnerability was detected.",
        "impact": "This vulnerability may compromise system security.",
        "fix": "Review and update the affected code."
    }

    # Validate and sanitize each required field
    for field, default_value in defaults.items():
        if field not in data or not isinstance(data[field], str) or not data[field].strip():
            data[field] = default_value
        else:
            # Ensure it's a string and strip whitespace
            data[field] = str(data[field]).strip()

    # Validate severity field specifically
    valid_severities = ["Low", "Medium", "High", "Critical", "Unknown"]
    severity = data.get("severity", "").title()
    if severity not in valid_severities:
        data["severity"] = "Medium"
    else:
        data["severity"] = severity

    return data

