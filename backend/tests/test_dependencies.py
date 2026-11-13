"""Keep pyproject.toml `[project].dependencies` in sync with requirements.txt.

Vercel's Python builder installs dependencies from pyproject.toml when it is
present. During the git-build incident `backend/pyproject.toml` carried only
[tool.*] sections, so nothing was installed and the function failed at import
with `ModuleNotFoundError: No module named 'fastapi'`. This test fails the
moment the two files disagree again.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = BACKEND_ROOT / "pyproject.toml"
REQUIREMENTS = BACKEND_ROOT / "requirements.txt"


def _package_name(requirement_line: str) -> str:
    """Return the normalized distribution name for one requirement line."""
    line = requirement_line.strip()
    if not line or line.startswith("#"):
        return ""
    # Drop environment markers and inline comments.
    line = line.split(";")[0].split(" #")[0].strip()
    # Strip extras, then any version specifier.
    line = line.split("[")[0]
    name = re.split(r"[<>=!~ ]", line, maxsplit=1)[0]
    return name.strip().lower()


def _requirement_names(path: Path) -> set[str]:
    names: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip().startswith("-r "):
            continue
        name = _package_name(raw)
        if name:
            names.add(name)
    return names


def test_pyproject_declares_project_dependencies() -> None:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    assert "project" in data, "pyproject.toml needs a [project] table for Vercel"
    assert data["project"].get("dependencies"), "[project].dependencies must not be empty"


def test_pyproject_declares_fastapi() -> None:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    declared = {_package_name(dep) for dep in data["project"]["dependencies"]}
    assert "fastapi" in declared


def test_every_requirement_is_declared_in_pyproject() -> None:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    declared = {_package_name(dep) for dep in data["project"]["dependencies"]}
    missing = sorted(_requirement_names(REQUIREMENTS) - declared)
    assert not missing, f"requirements.txt packages missing from pyproject.toml: {missing}"
