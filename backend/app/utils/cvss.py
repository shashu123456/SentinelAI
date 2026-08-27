"""CVSS v3.1 scoring helpers.

Provides lightweight scoring for findings based on severity and vulnerability
characteristics without requiring the full CVSS vector calculation library.
"""

# Base scores by severity (CVSS v3.1 ranges)
_SEVERITY_BASE_SCORES: dict[str, tuple[float, float]] = {
    "Critical": (9.0, 10.0),
    "High": (7.0, 8.9),
    "Medium": (4.0, 6.9),
    "Low": (0.1, 3.9),
    "Info": (0.0, 0.0),
}

# OWASP category risk multipliers
_OWASP_RISK_MULTIPLIERS: dict[str, float] = {
    "API1": 1.0,  # Broken Object Level Authorization
    "API2": 0.95,  # Broken Authentication
    "API3": 0.9,  # Broken Object Property Level Authorization
    "API4": 0.85,  # Unrestricted Resource Consumption
    "API5": 0.8,  # Broken Function Level Authorization
    "API6": 0.95,  # Unrestricted Access to Sensitive Business Flows
    "API7": 0.9,  # Server Side Request Forgery
    "API8": 0.85,  # Security Misconfiguration
    "API9": 0.8,  # Improper Inventory Management
    "API10": 0.75,  # Unsafe Consumption of APIs
}


def compute_cvss_score(
    severity: str,
    owasp_category: str | None = None,
    confidence: int | None = None,
    has_exploit: bool = False,
) -> tuple[float, str]:
    """Compute a CVSS-like score for a finding.

    Returns:
        Tuple of (score, vector_string)
    """
    severity = severity or "Medium"
    low, high = _SEVERITY_BASE_SCORES.get(severity, (4.0, 6.9))

    # Start with midpoint of severity range
    score = (low + high) / 2.0

    # Apply OWASP risk multiplier
    if owasp_category:
        prefix = owasp_category.split("-")[0] if "-" in owasp_category else owasp_category
        multiplier = _OWASP_RISK_MULTIPLIERS.get(prefix, 0.8)
        score *= multiplier

    # Confidence adjustment (0-100 scale)
    if confidence is not None:
        confidence_factor = 0.7 + (confidence / 100.0) * 0.3  # 0.7 to 1.0
        score *= confidence_factor

    # Exploit availability increases score
    if has_exploit:
        score = min(10.0, score * 1.15)

    # Clamp to valid range
    score = max(0.0, min(10.0, round(score, 1)))

    # Build simplified vector string
    vector = _build_vector_string(severity, owasp_category, confidence, has_exploit)

    return score, vector


def _build_vector_string(
    severity: str,
    owasp_category: str | None,
    confidence: int | None,
    has_exploit: bool,
) -> str:
    """Build a simplified CVSS v3.1 vector string."""
    av = "N"  # Attack Vector: Network
    ac = "L"  # Attack Complexity: Low
    pr = "N"  # Privileges Required: None
    ui = "R"  # User Interaction: Required

    severity_map = {"Critical": "H", "High": "H", "Medium": "L", "Low": "L", "Info": "N"}
    s = severity_map.get(severity, "L")

    cia_map = {"Critical": "H", "High": "H", "Medium": "L", "Low": "N", "Info": "N"}
    c = cia_map.get(severity, "L")
    i = cia_map.get(severity, "L")
    a = cia_map.get(severity, "N")

    exploit = "P" if has_exploit else "X"
    conf = (
        "R"
        if confidence and confidence >= 80
        else ("U" if confidence and confidence >= 50 else "X")
    )

    return f"CVSS:3.1/AV:{av}/AC:{ac}/PR:{pr}/UI:{ui}/S:{s}/C:{c}/I:{i}/A:{a}/E:{exploit}/CR:{conf}"


def risk_score_from_severity_distribution(dist: dict[str, int]) -> int:
    """Compute an aggregate risk score (0-100) from a severity distribution."""
    if not dist:
        return 0

    weights = {"Critical": 40, "High": 25, "Medium": 10, "Low": 3, "Info": 1}
    total = sum(dist.values())
    if total == 0:
        return 0

    weighted_sum = sum(dist.get(sev, 0) * w for sev, w in weights.items())
    # Normalize to 0-100 scale, capped
    score = min(100, round(weighted_sum / max(total, 1) * 2))
    return score


def security_grade(score: int) -> str:
    """Convert a risk score to a letter grade."""
    if score >= 90:
        return "F"
    elif score >= 80:
        return "D"
    elif score >= 60:
        return "C"
    elif score >= 40:
        return "B"
    elif score >= 20:
        return "B+"
    else:
        return "A"


def severity_rank(severity: str) -> int:
    """Return numeric rank for severity sorting (lower = more severe)."""
    ranks = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
    return ranks.get(severity, 5)
