import os
import json
from openai import OpenAI
from pydantic import BaseModel


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

        # Try to parse JSON response
        try:
            vulnerability_data = json.loads(response_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    vulnerability_data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    raise ValueError("Could not parse JSON from OpenAI response")
            else:
                raise ValueError("No JSON found in OpenAI response")

        # Validate required fields
        required_fields = ["name", "severity", "explanation", "impact", "fix"]
        for field in required_fields:
            if field not in vulnerability_data:
                vulnerability_data[field] = f"Missing {field} information"

        # Ensure severity is valid
        valid_severities = ["Low", "Medium", "High", "Critical"]
        if vulnerability_data.get("severity", "").title() not in valid_severities:
            vulnerability_data["severity"] = "Medium"

        return VulnerabilityExplanation(**vulnerability_data)

    except Exception as e:
        # Fallback for any errors
        return VulnerabilityExplanation(
            name="Analysis Error",
            severity="Unknown",
            explanation=f"Could not analyze vulnerability: {issue}",
            impact="Unable to determine potential impact due to analysis error",
            fix="Please review the code manually or try again later"
        )
