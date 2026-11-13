import pathlib
import re
import subprocess
import sys

baseline_path = pathlib.Path("docs/MYPY_BASELINE.md")
m = re.search(r"baseline:\s*(\d+)", baseline_path.read_text())
baseline = int(m.group(1)) if m else 0

out = subprocess.run(
    [sys.executable, "-m", "mypy", "app"],
    capture_output=True, text=True, cwd=pathlib.Path(".").parent,
).stdout

m = re.search(r"Found (\d+) error", out)
count = int(m.group(1)) if m else 0

print(f"mypy errors: {count} (baseline {baseline})")
sys.exit(1 if count > baseline else 0)
