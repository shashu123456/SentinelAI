"""Shared schema constants used across multiple schema modules."""

SCAN_STATUSES = ("pending", "running", "completed", "failed")
RISK_LEVELS = ("Critical", "High", "Medium", "Low", "Info")
SEVERITIES = ("Critical", "High", "Medium", "Low", "Info")
SCAN_SORT_FIELDS = ("created_at", "risk_score", "api_name", "total_vulnerabilities", "status")
FINDING_SORT_FIELDS = (
    "severity",
    "vulnerability_name",
    "confidence",
    "cvss_score",
    "affected_endpoint",
)
SORT_DIRECTIONS = ("asc", "desc")


def parse_sort_fields(sort_by: str, default_desc: bool = False) -> list[tuple[str, bool]]:
    """Parse a comma-separated sort spec into ``(field, descending)`` pairs.

    A leading ``-`` on a field marks it as descending (overriding the caller's
    default direction); unprefixed fields use ``default_desc``.
    """
    result: list[tuple[str, bool]] = []
    for part in sort_by.split(","):
        part = part.strip()
        if not part:
            continue
        if part.startswith("-"):
            result.append((part[1:], True))
        else:
            result.append((part, default_desc))
    return result
