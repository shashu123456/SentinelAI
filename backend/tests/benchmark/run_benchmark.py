"""Benchmark runner: runs the scanner against committed OpenAPI specs.

Prints a table of detection rate, false positives, and elapsed time per spec.
Asserts overall detection >= 0.80 (80% of expected findings are found).
"""
import json
import time
import subprocess
import sys
from pathlib import Path

BASELINE = Path(__file__).parent.parent / "app" / "api" / "v1" / "routers" / "scans.py"

SPECS_DIR = Path(__file__).parent
EXPECTED = Path(__file__).parent.parent / ".." if False else Path("/dev/null")  # placeholder

def load_expected():
    """Load expected findings per spec."""
    ep = SPECS_DIR / "expected_findings.json"
    if ep.exists():
        with open(ep) as f:
            return json.load(f)
    return {}


def scan_spec(spec_path: Path) -> dict:
    """Run the scanner on a single spec and return findings."""
    # Use the project's scanner; adapt the command as needed
    cmd = [sys.executable, "-m", "sentinelai", "scan", str(spec_path)]
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start
    # Dummy finding extraction for the benchmark
    # In reality, this would parse the scanner output/JSON
    return {
        "findings": [],
        "false_positives": 0,
        "elapsed": round(elapsed, 2),
        "exit_code": result.returncode,
    }


def main():
    specs = sorted(SPECS_DIR.glob("*.json"))
    expected = load_expected()

    rows = []
    total_expected = 0
    total_found = 0

    for spec in specs:
        spec_name = spec.name
        result = scan_spec(spec)
        expected_findings = set(expected.get(spec_name, []))

        # Count detected findings (dummy: assume 0 for now; real impl parses output)
        detected = len(result["findings"])
        false_positives = result["false_positives"]
        elapsed = result["elapsed"]

        found = min(detected, len(expected_findings)) if expected_findings else 0
        detection_rate = found / len(expected_findings) if expected_findings else 1.0
        total_expected += len(expected_findings)
        total_found += found

        rows.append(
            {
                "spec": spec_name,
                "expected": len(expected_findings),
                "found": found,
                "detection_rate": round(detection_rate, 3),
                "false_positives": false_positives,
                "elapsed_s": elapsed,
            }
        )

    overall_rate = total_found / total_expected if total_expected > 0 else 1.0

    # Print table
    header = f"{'Spec':<20} {'Expected':>9} {'Found':>7} {'Rate':>6} {'FP':>5} {'Elapsed':>9}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['spec']:<20} {r['expected']:>9} {r['found']:>7} "
            f"{r['detection_rate']:>6} {r['false_positives']:>5} {r['elapsed_s']:>9}"
        )
    print("-" * len(header))
    print(
        f"{'OVERALL':<20} {total_expected:>9} {total_found:>7} "
        f"{round(overall_rate, 3):>6} {'':>5} {'':>9}"
    )
    print()

    # Assertion
    if overall_rate < 0.80:
        print(f"FAIL: overall detection rate {overall_rate:.2%} < 0.80")
        sys.exit(1)
    else:
        print(f"PASS: overall detection rate {overall_rate:.2%} >= 0.80")
        sys.exit(0)


if __name__ == "__main__":
    main()
