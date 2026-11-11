"""Environment diagnostics shared by `sentinel doctor` and `scripts/doctor.sh`.

Checks are fast, read-only, and never install anything. Exit code is 0 when
nothing is *broken* (warnings are fine), 1 when something must be fixed before
the project will run.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

from .fmt import BOLD, DIM, RESET, ascii_safe, header, paint, sym

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"

PASS = ("ok", "\033[92m")
WARN = ("warn", "\033[93m")
FAIL = ("fail", "\033[91m")
INFO = ("info", "\033[90m")


class Report:
    def __init__(self) -> None:
        self.failures = 0
        self.warnings = 0
        self.rows: list[tuple[str, str, str, str]] = []

    def add(self, status: tuple[str, str], name: str, detail: str, fix: str = "") -> None:
        if status is FAIL:
            self.failures += 1
        elif status is WARN:
            self.warnings += 1
        self.rows.append((status[0], name, detail, fix))

    def ok(self, name: str, detail: str = "") -> None:
        self.add(PASS, name, detail)

    def warn(self, name: str, detail: str, fix: str = "") -> None:
        self.add(WARN, name, detail, fix)

    def fail(self, name: str, detail: str, fix: str = "") -> None:
        self.add(FAIL, name, detail, fix)

    def info(self, name: str, detail: str = "") -> None:
        self.add(INFO, name, detail)


def _run(cmd: list[str]) -> tuple[bool, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return False, ""
    output = (proc.stdout or proc.stderr or "").strip().splitlines()
    return proc.returncode == 0, output[0] if output else ""


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def _module_ok(python: Path, module: str) -> bool:
    ok, _ = _run([str(python), "-c", f"import {module}"])
    return ok


def _venv_python() -> Path | None:
    candidates = [
        BACKEND_DIR / "venv" / "Scripts" / "python.exe",
        BACKEND_DIR / "venv" / "bin" / "python",
    ]
    return next((p for p in candidates if p.exists()), None)


def run(verbose: bool = False, stats: bool = False) -> int:
    report = Report()

    if stats:
        return _print_stats()

    # ── Python ───────────────────────────────────────────────────────
    version = sys.version_info
    if version >= (3, 11):
        report.ok("Python", f"{version.major}.{version.minor}.{version.micro} ({sys.executable})")
    else:
        report.fail(
            "Python",
            f"{version.major}.{version.minor} — 3.11+ required",
            "Install Python 3.11 or newer",
        )

    venv_py = _venv_python()
    if venv_py:
        ok, out = _run([str(venv_py), "--version"])
        report.ok("Virtualenv", f"backend/venv ({out or 'ready'})")
    else:
        report.fail(
            "Virtualenv",
            "backend/venv missing",
            "Run `make install-backend` (or `make setup`)",
        )

    # ── Backend dependencies ─────────────────────────────────────────
    runtime_modules = ["fastapi", "sqlalchemy", "jose", "reportlab", "yaml", "click", "alembic"]
    dev_modules = ["pytest", "ruff", "black"]
    if venv_py:
        missing_runtime = [m for m in runtime_modules if not _module_ok(venv_py, m)]
        missing_dev = [m for m in dev_modules if not _module_ok(venv_py, m)]
        if not missing_runtime:
            report.ok("Backend deps", f"{len(runtime_modules)} runtime packages importable")
        else:
            report.fail(
                "Backend deps",
                f"missing: {', '.join(missing_runtime)}",
                "Run `make install-backend` (or `make setup`)",
            )
        if missing_dev:
            report.warn(
                "Dev tools",
                f"missing: {', '.join(missing_dev)}",
                "Run `make install-backend` for lint/test tooling",
            )
        else:
            report.ok("Dev tools", "pytest, ruff, black importable")

    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        report.ok("backend/.env", "present")
    else:
        report.warn(
            "backend/.env",
            "missing — defaults will be used",
            "Run `bash scripts/setup.sh` to generate one",
        )

    db_url = os.environ.get("DATABASE_URL", "")
    db_path = BACKEND_DIR / "sentinelai.db"
    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        report.ok("SQLite database", f"backend/sentinelai.db ({size_mb:.1f} MB)")
    else:
        report.warn(
            "SQLite database",
            "not created yet",
            "Run `make migrate`",
        )
    if db_url.startswith("postgres"):
        report.info("DATABASE_URL", "PostgreSQL configured")

    # ── Node / frontend ──────────────────────────────────────────────
    npm = shutil.which("npm")
    node = shutil.which("node")
    if node:
        ok, out = _run([node, "--version"])
        report.ok("Node.js", out)
    else:
        report.fail("Node.js", "not found", "Install Node.js 18+ from nodejs.org")

    if npm:
        ok, out = _run([npm, "--version"])
        report.ok("npm", out)
    else:
        report.fail("npm", "not found", "Install Node.js 18+ (includes npm)")

    if (FRONTEND_DIR / "node_modules").exists():
        report.ok("Frontend deps", "node_modules present")
    else:
        report.warn("Frontend deps", "node_modules missing", "Run `make install-frontend`")

    # ── Versions in use ──────────────────────────────────────────────
    pkg = FRONTEND_DIR / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            report.info("Frontend stack", f"vite {data.get('devDependencies', {}).get('vite')}")
        except json.JSONDecodeError:
            report.warn("package.json", "could not be parsed")

    # ── Optional services ────────────────────────────────────────────
    if _port_open(8000):
        report.info("Port 8000", "in use (API may already be running)")
    if _port_open(5173):
        report.info("Port 5173", "in use (Vite may already be running)")

    if _port_open(11434):
        report.ok("Ollama", "reachable on :11434")
    else:
        report.info("Ollama", "not running — AI analysis disabled, scans still work")

    if _port_open(6379):
        report.ok("Redis", "reachable on :6379")
    else:
        report.info("Redis", "not running — in-memory cache is used")

    if shutil.which("docker"):
        ok, out = _run(["docker", "--version"])
        report.info("Docker", out)
    else:
        report.info("Docker", "not installed — only needed for `make docker-dev`")

    if shutil.which("git"):
        ok, out = _run(["git", "--version"])
        report.ok("git", out)
    else:
        report.warn("git", "not found", "Install git")

    # ── Report ───────────────────────────────────────────────────────
    click_echo(header("Environment report"))
    for glyph_key, name, detail, fix in report.rows:
        color = next(s[1] for s in (PASS, WARN, FAIL, INFO) if s[0] == glyph_key)
        glyph = sym(glyph_key)
        click_echo(f"  {paint(glyph, color)} {name:<18} {detail}")
        if fix and glyph_key in (WARN[0], FAIL[0]):
            click_echo(f"    {DIM}{sym('arrow')} {fix}{RESET}")

    status = (
        paint(f"{report.failures} problem(s)", "\033[91m")
        if report.failures
        else paint("all good", "\033[92m")
    )
    click_echo(f"\n  {BOLD}{status}{RESET}")
    if report.warnings and not report.failures:
        click_echo(
            paint(f"  {report.warnings} warning(s) — the project will still run.", "\033[93m")
        )
    click_echo("")
    return 1 if report.failures else 0


def click_echo(message: str) -> None:
    sys.stdout.write(ascii_safe(message) + "\n")


def _print_stats() -> int:
    """Quick repository size summary (``make stats``)."""
    click_echo(header("Repository stats"))

    def count(folder: Path, pattern: str, skip: tuple[str, ...] = ("node_modules", "venv")) -> int:
        total = 0
        for path in folder.rglob(pattern):
            if any(part in skip for part in path.parts):
                continue
            total += 1
        return total

    py = count(BACKEND_DIR / "app", "*.py")
    js = count(FRONTEND_DIR / "src", "*.jsx") + count(FRONTEND_DIR / "src", "*.js")
    tests = count(BACKEND_DIR / "tests", "test_*.py") + count(FRONTEND_DIR / "src", "*.test.*")
    docs = count(REPO_ROOT / "docs", "*.md")
    click_echo(f"  backend python   {py}")
    click_echo(f"  frontend source  {js}")
    click_echo(f"  test files       {tests}")
    click_echo(f"  docs             {docs}")
    click_echo("")
    return 0
