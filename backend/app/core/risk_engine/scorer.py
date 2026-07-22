SEVERITY_WEIGHTS = {
    "Critical": 25,
    "High": 15,
    "Medium": 8,
    "Low": 3,
    "Info": 1,
}

SEVERITY_THRESHOLDS = {
    "Critical": (80, 100),
    "High": (60, 79),
    "Medium": (30, 59),
    "Low": (10, 29),
    "Low Risk": (0, 9),
}


def calculate_risk_score(findings: list[dict]) -> dict:
    if not findings:
        return {
            "score": 0,
            "level": "Low Risk",
            "total_vulnerabilities": 0,
            "critical_count": 0,
            "high_count": 0,
            "medium_count": 0,
            "low_count": 0,
            "info_count": 0,
        }

    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
    for f in findings:
        severity = f.get("severity", "Info")
        if severity in counts:
            counts[severity] += 1

    raw_score = sum(
        counts[sev] * SEVERITY_WEIGHTS[sev]
        for sev in counts
    )

    max_possible = max(len(findings) * SEVERITY_WEIGHTS["Critical"], 1)
    normalized_score = min(int((raw_score / max_possible) * 100), 100)

    if counts["Critical"] > 0:
        normalized_score = max(normalized_score, 80)
    if counts["High"] > 0:
        normalized_score = max(normalized_score, 60)
    if counts["Medium"] > 0 and normalized_score < 30:
        normalized_score = 30

    level = _determine_risk_level(normalized_score)

    return {
        "score": normalized_score,
        "level": level,
        "total_vulnerabilities": len(findings),
        "critical_count": counts["Critical"],
        "high_count": counts["High"],
        "medium_count": counts["Medium"],
        "low_count": counts["Low"],
        "info_count": counts["Info"],
    }


def _determine_risk_level(score: int) -> str:
    for level, (low, high) in SEVERITY_THRESHOLDS.items():
        if low <= score <= high:
            return level
    return "Low Risk"


def get_severity_distribution(findings: list[dict]) -> dict:
    dist = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
    for f in findings:
        sev = f.get("severity", "Info")
        if sev in dist:
            dist[sev] += 1
    return dist
