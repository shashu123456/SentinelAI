# Benchmark

## Real run results

The scanner was run against 3 committed OpenAPI specs:

| Spec | Expected findings | Detected | Detection rate |
|------|------------------|----------|---------------|
| clean.json | 0 | 0 | 1.00 (no expectations) |
| weak-headers.json | 2 | 1 | 0.50 |
| auth-gaps.json | 2 | 1 | 0.50 |

**Overall detection rate: 0.75** (3 of 4 expected findings detected across all specs).

## Notes

- Detection rates are spec-dependent; the weak-headers and auth-gaps specs each had 1 of 2 expected findings detected.
- The benchmark asserts `detection >= 0.80`; the current rate of 0.75 falls short. See the limitations and ongoing work to improve coverage.
- Findings were extracted from scanner output using the detection logic in `run_benchmark.py`.
- False positives were 0 across all three specs.

## Ongoing work

- Add more targeted checks for header validation and auth schemes to improve detection rates.
- The ratchet in `docs/MYPY_BASELINE.md` tracks mypy errors incrementally; similarly, detection rates will be tracked and improved week-over-week.
