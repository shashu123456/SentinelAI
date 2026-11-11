# Sample datasets

Real engine output for the specs in [`../`](../), captured with the CLI. Use
them to build fixtures, demo charts, or report exports without running a scan.

| File | Source spec | Endpoints | Findings | Risk |
|------|-------------|-----------|----------|------|
| `vulnerable_api-scan.json` | `samples/vulnerable_api.yaml` | 19 | 63 | 80 · Critical |
| `secure_api-scan.json` | `samples/secure_api.yaml` | 16 | 27 | 80 · Critical |
| `banking_api-scan.json` | `samples/banking_api.yaml` | 11 | 22 | 80 · Critical |
| `ecommerce_api-scan.json` | `samples/ecommerce_api.yaml` | 15 | 19 | 80 · Critical |

Each file is the exact JSON the CLI emits, so the shape matches an API scan:

```json
{
  "api_title": "…",
  "api_version": "…",
  "total_endpoints": 19,
  "findings": [{ "vulnerability_name": "…", "severity": "Critical", "cvss_score": 8.8, … }],
  "risk": { "score": 80, "level": "Critical", "critical_count": 12, … },
  "source": "samples/vulnerable_api.yaml"
}
```

## Regenerate

```bash
make datasets
```

which runs:

```bash
for f in samples/*.yaml; do
  python -m tools.sentinel_cli scan "$f" --format json -o "samples/datasets/$(basename "$f" .yaml)-scan.json"
done
```

## Use in tests

```python
import json
from pathlib import Path

DATASETS = Path(__file__).resolve().parents[2] / "samples" / "datasets"

def load_findings(name: str = "vulnerable_api") -> list[dict]:
    return json.loads((DATASETS / f"{name}-scan.json").read_text())["findings"]
```

> These specs are intentionally insecure. They exist to exercise the scanner —
> never deploy them.
