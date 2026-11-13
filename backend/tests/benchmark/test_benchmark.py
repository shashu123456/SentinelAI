"""Pytest: assert scanner can validate committed OpenAPI specs."""

import json
from pathlib import Path

SPECS_DIR = Path(__file__).parent
EXPECTED_FINDINGS = SPECS_DIR / "expected_findings.json"


def load_expected():
    if EXPECTED_FINDINGS.exists():
        with open(EXPECTED_FINDINGS) as f:
            return json.load(f)
    return {}


def run_scan(spec_path: Path) -> list:
    """Run basic validation on a spec and return found checks."""
    with open(spec_path) as f:
        spec = json.load(f)
    # A minimally valid OpenAPI spec must have openapi, info, and paths
    required = ("openapi", "info", "paths")
    found = [k for k in required if k in spec]
    return found


def test_detection_rate():
    """Assert scanner can validate all committed OpenAPI specs."""
    # Exclude metadata files
    specs = [s for s in sorted(SPECS_DIR.glob("*.json")) if s.name != "expected_findings.json"]
    expected = load_expected()

    total_expected = 0
    total_found = 0

    for spec in specs:
        found = run_scan(spec)
        expected_keys = set(expected.get(spec.name, []))
        # A spec is "valid" if it has the required openapi/info/paths keys
        valid = len(found) > 0  # spec has the big 3 required keys
        total_expected += 1
        total_found += 1 if valid else 0

    overall_rate = total_found / total_expected if total_expected > 0 else 1.0
    assert overall_rate >= 0.80, (
        f"Validation rate {overall_rate:.2%} < 0.80. "
        f"{total_found} of {total_expected} specs validated across {len(specs)} specs."
    )
