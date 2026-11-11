"""`sentinel` — the SentinelAI developer CLI.

Usage (from the repository root):

    python -m tools.sentinel_cli --help
    make cli ARGS="scan samples/vulnerable_api.yaml"
"""

from __future__ import annotations

import contextlib
import json
import sys
import time
from pathlib import Path

import click

from . import __version__, api, config, fmt
from .fmt import BOLD, DIM, RESET, header, paint, risk_bar, rule, severity, sym, table, truncate

SEVERITIES = ["Critical", "High", "Medium", "Low", "Info"]


def echo(message: str = "", err: bool = False) -> None:
    """Print, transliterating to ASCII on consoles that need it."""
    click.echo(fmt.ascii_safe(message), err=err)


# ── Shared helpers ────────────────────────────────────────────────────


def _fail(message: str, code: int = 1):
    echo(paint(f"{sym('fail')} {message}", "\033[91m"), err=True)
    sys.exit(code)


def _ok(message: str) -> None:
    echo(paint(f"{sym('ok')} {message}", "\033[92m"))


def _warn(message: str) -> None:
    echo(paint(f"{sym('warn')} {message}", "\033[93m"))


def _print_scan_card(result: dict) -> None:
    risk = result["risk"]
    title = result.get("api_title") or result.get("source") or "API"
    echo(header(f"{title}"))
    echo(
        f"  {DIM}source{RESET}   {result.get('source', 'n/a')}\n"
        f"  {DIM}version{RESET}  {result.get('api_version') or 'unversioned'}\n"
        f"  {DIM}routes{RESET}   {result.get('total_endpoints', 0)}\n"
        f"  {DIM}findings{RESET} {risk['total_vulnerabilities']}"
    )
    echo(f"\n  {risk_bar(risk['score'])}  {BOLD}{risk['level']}{RESET}\n")

    counts = [(sev, risk.get(f"{sev.lower()}_count", 0)) for sev in SEVERITIES]
    echo("  " + "  ".join(f"{severity(name)}{count}" for name, count in counts if count))


def _print_findings(result: dict, limit: int | None) -> None:
    findings = sorted(
        result["findings"],
        key=lambda f: (
            SEVERITIES.index(f.get("severity", "Info"))
            if f.get("severity", "Info") in SEVERITIES
            else 9
        ),
    )
    if not findings:
        echo(paint(f"\n  No findings. {sym('party')}\n", "\033[92m"))
        return

    shown = findings if limit is None else findings[:limit]
    echo("")
    rows = []
    for index, finding in enumerate(shown, start=1):
        endpoint = finding.get("affected_endpoint") or "—"
        if finding.get("affected_method"):
            endpoint = f"{finding['affected_method']} {endpoint}"
        rows.append(
            [
                str(index),
                finding.get("severity", "Info"),
                truncate(finding.get("vulnerability_name", "Finding"), 34),
                truncate(endpoint, 28),
                str(finding.get("cvss_score", "—")),
            ]
        )
    echo(table(["#", "Severity", "Finding", "Endpoint", "CVSS"], rows, [3, 8, 34, 28, 5]))

    if limit is not None and len(findings) > limit:
        echo(
            paint(
                f"\n  {sym('ellipsis')} {len(findings) - limit} more (use --all to show everything)",
                "\033[90m",
            )
        )

    ctx = click.get_current_context(silent=True)
    if len(shown) == 1 or (ctx is not None and (ctx.obj or {}).get("verbose")):
        for finding in shown:
            echo(
                f"\n  {severity(finding.get('severity', 'Info'))}"
                f"{BOLD}{finding.get('vulnerability_name')}{RESET}  "
                f"{DIM}{finding.get('owasp_category')} · {finding.get('cwe_id')}{RESET}"
            )
            echo(f"  {finding.get('description', '').strip()}")
            if finding.get("evidence"):
                echo(f"  {DIM}evidence:{RESET} {finding['evidence']}")
            if finding.get("remediation"):
                echo(f"  {DIM}fix:{RESET} {finding['remediation']}")


def _write_output(payload: dict | str, destination: Path | None, label: str) -> None:
    if destination is None:
        return
    text = payload if isinstance(payload, str) else json.dumps(payload, indent=2)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    _ok(f"{label} written to {destination}")


# ── Root group ───────────────────────────────────────────────────────


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="sentinel")
@click.option("-v", "--verbose", is_flag=True, help="Show full finding details.")
@click.pass_context
def cli(ctx, verbose: bool):
    """SentinelAI developer CLI — scan specs locally or drive a running API.

    \b
    Fastest path:
      sentinel scan samples/vulnerable_api.yaml
      sentinel demo          # seed a demo workspace
      sentinel login         # then: upload / scans / report
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


# ── Local scanning ───────────────────────────────────────────────────


@cli.command()
@click.argument("specs", nargs=-1, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "markdown", "sarif"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format.",
)
@click.option(
    "-o", "--output", type=click.Path(dir_okay=False, path_type=Path), help="Write to a file."
)
@click.option("--all", "show_all", is_flag=True, help="List every finding, not just the top 10.")
@click.option(
    "--fail-on",
    type=click.Choice(["none"] + [s.lower() for s in SEVERITIES], case_sensitive=False),
    default="none",
    show_default=True,
    help="Exit non-zero when a finding at or above this severity exists (for CI).",
)
def scan(specs, output_format, output, show_all, fail_on):
    """Scan OpenAPI specs locally — no server, database, or network needed.

    SPECS may be any number of .json/.yaml OpenAPI files.
    """
    if not specs:
        _fail("No spec given. Try: sentinel scan samples/vulnerable_api.yaml")

    from .local import scan_file, to_markdown, to_sarif

    results = []
    for path in specs:
        started = time.perf_counter()
        try:
            result = scan_file(path)
        except Exception as exc:
            _fail(f"{path}: {exc}")
        result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
        results.append(result)

    if output_format == "json":
        payload = results if len(results) > 1 else results[0]
        if output:
            _write_output(payload, output, "JSON report")
        else:
            echo(json.dumps(payload, indent=2))
    elif output_format == "markdown":
        _write_output(to_markdown(results), output or Path("sentinel-report.md"), "Markdown report")
        if not output:
            echo(to_markdown(results))
    elif output_format == "sarif":
        destination = output or Path("sentinel-results.sarif")
        _write_output(to_sarif(results), destination, "SARIF report")
    else:
        for index, result in enumerate(results):
            if index:
                echo(rule())
            _print_scan_card(result)
            _print_findings(result, None if show_all else 10)
        echo(
            paint(
                f"\n  {sum(r['risk']['total_vulnerabilities'] for r in results)} findings across "
                f"{len(results)} spec(s) in "
                f"{sum(r['elapsed_ms'] for r in results):.0f}ms\n",
                "\033[90m",
            )
        )

    threshold = SEVERITIES.index(fail_on.capitalize()) if fail_on.lower() != "none" else None
    if threshold is not None:
        worst = min(
            (
                SEVERITIES.index(f.get("severity", "Info"))
                for r in results
                for f in r["findings"]
                if f.get("severity", "Info") in SEVERITIES
            ),
            default=99,
        )
        if worst <= threshold:
            echo(
                paint(f"{sym('fail')} failing: findings at or above {fail_on}", "\033[91m"),
                err=True,
            )
            sys.exit(1)


@cli.command()
@click.option("--reset", is_flag=True, help="Recreate the demo workspace scans from scratch.")
def demo(reset: bool):
    """Seed a demo user, organization, project, and scans (idempotent)."""
    from .seed import seed_demo

    if reset:
        _warn("--reset is a no-op for now; scans are already de-duplicated by name.")

    started = time.perf_counter()
    try:
        summary = seed_demo()
    except Exception as exc:
        _fail(f"Seeding failed: {exc}")

    echo(header("Demo workspace ready"))
    echo(
        f"  {DIM}login{RESET}    {summary['username']} / {summary['password']}\n"
        f"  {DIM}email{RESET}    {summary['email']}\n"
        f"  {DIM}org{RESET}      #{summary['organization_id']}  project #{summary['project_id']}"
    )
    if summary["scans"]:
        echo(header("New scans"))
        echo(
            table(
                ["ID", "API", "Risk", "Level", "Findings"],
                [
                    [
                        str(s["id"]),
                        truncate(s["api_name"], 30),
                        f"{s['risk_score']}/100",
                        s["risk_level"],
                        str(s["vulnerabilities"]),
                    ]
                    for s in summary["scans"]
                ],
            )
        )
    else:
        echo(paint("\n  Demo scans already present — nothing to do.", "\033[90m"))
    echo(
        paint(f"\n  Seeded in {time.perf_counter() - started:.1f}s", "\033[90m")
        + "\n  Next: `make dev` then open http://localhost:"
        + str(5173)
        + "\n"
    )


@cli.command()
@click.option("--stats", is_flag=True, help="Print repository statistics instead of diagnostics.")
def doctor(stats: bool):
    """Check the local environment for missing tools or configuration."""
    from .doctor import run

    sys.exit(run(stats=stats))


# ── Remote commands ──────────────────────────────────────────────────


@cli.command()
@click.option("--url", help=f"API base URL (default: {config.DEFAULT_API_URL}).")
@click.option("--username", prompt=True, help="Username or email.")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    help="Password (or set SENTINEL_PASSWORD to skip the prompt).",
)
def login(url, username, password):
    """Log in and store a bearer token for later commands."""
    base = (url or config.api_url()).rstrip("/")
    try:
        payload = api.login(username, password, base_url=base)
    except api.APIError as exc:
        _fail(exc.message)

    data = config.load()
    data.update(
        {
            "api_url": base,
            "access_token": payload.get("access_token"),
            "user": payload.get("user"),
        }
    )
    path = config.save(data)
    user = payload.get("user") or {}
    _ok(f"Logged in as {user.get('username', username)} → {path}")


@cli.command()
@click.option("--url", help="API base URL.")
def whoami(url):
    """Show the account the stored token belongs to."""
    try:
        payload = api.get_json("/api/auth/me", base_url=url)
    except api.APIError as exc:
        _fail(exc.message)
    echo(
        f"{BOLD}{payload.get('username')}{RESET} <{payload.get('email')}>  "
        + paint(f"role={payload.get('role')} id={payload.get('id')}", "\033[90m")
    )


@cli.command()
def logout():
    """Forget the stored token."""
    config.clear_token()
    _ok("Logged out")


@cli.command(name="health")
@click.option("--url", help="API base URL.")
@click.option("--json", "as_json", is_flag=True, help="Print raw JSON.")
def health_cmd(url, as_json):
    """Show API health for every dependency."""
    try:
        payload = api.health(base_url=url)
    except api.APIError as exc:
        _fail(exc.message)

    if as_json:
        echo(json.dumps(payload, indent=2))
        return

    status = payload.get("status", "unknown")
    color = "\033[92m" if status == "healthy" else "\033[93m"
    echo(header(f"API status: {paint(status.upper(), color)}"))
    details = payload.get("details") or {}
    rows = []
    for name, info in details.items():
        if isinstance(info, dict):
            check = info.get("status", "unknown")
            rows.append(
                [
                    name,
                    check,
                    str(info.get("latency_ms", info.get("used_percent", "—"))),
                    truncate(info.get("error") or info.get("detail") or "", 40),
                ]
            )
    if rows:
        echo(table(["Component", "Status", "Value", "Detail"], rows))
    echo(
        paint(
            f"\n  version {payload.get('version')} · uptime {payload.get('uptime_human')}\n",
            "\033[90m",
        )
    )


@cli.command()
@click.argument("spec", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--name", default="", help="Display name for the scan.")
@click.option("--org", "organization_id", type=int, help="Organization to file the scan under.")
def upload(spec, name, organization_id):
    """Upload a spec to a running API and run a server-side scan."""
    try:
        scan_row = api.upload_spec(spec, api_name=name, organization_id=organization_id)
    except api.APIError as exc:
        _fail(exc.message)

    echo(header(f"Scan #{scan_row.get('id')} · {scan_row.get('api_name')}"))
    echo(
        f"  risk {risk_bar(scan_row.get('risk_score', 0))}  {scan_row.get('risk_level')}\n"
        f"  findings {scan_row.get('total_vulnerabilities')} · "
        f"endpoints {scan_row.get('total_endpoints')}"
    )
    echo(paint(f"\n  View: {config.api_url()}/api/scans/{scan_row.get('id')}\n", "\033[90m"))


@cli.command()
@click.option("--limit", default=20, show_default=True, help="Rows to show.")
@click.option("--json", "as_json", is_flag=True, help="Print raw JSON.")
def scans(limit, as_json):
    """List scans from the API."""
    try:
        rows = api.get_json("/api/scans/")
    except api.APIError as exc:
        _fail(exc.message)

    if as_json:
        echo(json.dumps(rows, indent=2))
        return
    if not rows:
        echo("No scans yet. Run `sentinel upload <spec>` or `sentinel demo`.")
        return

    echo(
        table(
            ["ID", "API", "Status", "Risk", "Level", "Findings", "Created"],
            [
                [
                    str(row["id"]),
                    truncate(row["api_name"], 26),
                    row["status"],
                    f"{row['risk_score']}/100",
                    row["risk_level"],
                    str(row["total_vulnerabilities"]),
                    (row.get("created_at") or "")[:19].replace("T", " "),
                ]
                for row in rows[:limit]
            ],
            [4, 26, 10, 8, 11, 8, 19],
        )
    )


@cli.command()
@click.argument("scan_id", type=int)
@click.option("--json", "as_json", is_flag=True, help="Print raw JSON.")
@click.option("--all", "show_all", is_flag=True, help="Show every finding.")
def show(scan_id, as_json, show_all):
    """Show one scan and its findings."""
    try:
        detail = api.get_json(f"/api/scans/{scan_id}")
    except api.APIError as exc:
        _fail(exc.message)

    if as_json:
        echo(json.dumps(detail, indent=2))
        return

    _print_scan_card(
        {
            "api_title": detail.get("api_name"),
            "api_version": detail.get("api_version"),
            "total_endpoints": detail.get("total_endpoints", 0),
            "risk": {
                "score": detail.get("risk_score", 0),
                "level": detail.get("risk_level", "—"),
                "total_vulnerabilities": detail.get("total_vulnerabilities", 0),
                **{
                    f"{sev.lower()}_count": detail.get(f"{sev.lower()}_count", 0)
                    for sev in SEVERITIES
                },
            },
            "findings": detail.get("vulnerabilities") or detail.get("findings") or [],
        }
    )
    findings = detail.get("vulnerabilities") or detail.get("findings") or []
    if findings:
        _print_findings({"findings": findings}, None if show_all else 10)


@cli.command()
@click.argument("scan_id", type=int)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "pdf"], case_sensitive=False),
    default="json",
    show_default=True,
)
@click.option(
    "-o", "--output", type=click.Path(dir_okay=False, path_type=Path), help="Destination file."
)
def report(scan_id, output_format, output):
    """Download the JSON or PDF report for a scan."""
    suffix = "pdf" if output_format.lower() == "pdf" else "json"
    destination = output or Path(f"scan-{scan_id}-report.{suffix}")
    try:
        api.download(f"/api/scans/{scan_id}/report/{suffix}", destination)
    except api.APIError as exc:
        _fail(exc.message)
    _ok(f"Saved {destination} ({destination.stat().st_size:,} bytes)")


@cli.command()
@click.option("--url", help="API base URL.")
def open_playground(url):  # noqa: A001 - click exposes it as `playground`
    """Print the path to the offline API playground."""
    path = Path(__file__).resolve().parents[2] / "docs" / "api-playground.html"
    echo(f"{path.as_uri()}?api={url or config.api_url()}")


def _configure_streams() -> None:
    """Never crash on a console that cannot encode a glyph."""
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, ValueError):
            stream.reconfigure(errors="replace")


def main() -> None:
    _configure_streams()
    cli(obj={})


if __name__ == "__main__":  # pragma: no cover
    main()
