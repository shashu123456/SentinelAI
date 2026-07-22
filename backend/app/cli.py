#!/usr/bin/env python3
"""
SentinelAI CLI - API Security Scanner Command Line Interface

Usage:
    sentinelai scan <spec_file> [--output json|pdf] [--ai/--no-ai]
    sentinelai history [--server URL]
    sentinelai stats [--server URL]
    sentinelai health [--server URL]
"""

import sys
import json
import os

try:
    import click
except ImportError:
    print("CLI requires 'click'. Install: pip install click")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("CLI requires 'requests'. Install: pip install requests")
    sys.exit(1)


DEFAULT_SERVER = "http://localhost:8000"


def get_server_url(server=None):
    return server or os.environ.get("SENTINELAI_SERVER", DEFAULT_SERVER)


def api_get(url, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def api_post(url, data=None, files=None, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.post(url, data=data, files=files, headers=headers, timeout=300)
    resp.raise_for_status()
    return resp.json()


def api_download(url, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(url, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("content-type", "")


@click.group()
@click.version_option(version="1.0.0", prog_name="sentinelai")
def cli():
    """SentinelAI - AI-Powered API Security Scanner CLI"""
    pass


@cli.command()
@click.argument("spec_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Choice(["json", "pdf"]), default="json", help="Report output format")
@click.option("--server", "-s", default=None, help="Backend server URL")
@click.option("--token", "-t", default=None, help="JWT auth token (or set SENTINELAI_TOKEN env)")
@click.option("--save", is_flag=True, help="Save report to file")
@click.option("--no-ai", is_flag=True, help="Skip AI analysis (faster)")
def scan(spec_file, output, server, token, save, no_ai):
    """Scan an OpenAPI/Swagger specification for security vulnerabilities.

    Examples:
        sentinelai scan petstore.json
        sentinelai scan api.yaml -o pdf --save
        sentinelai scan spec.json -o json -s http://prod:8000
    """
    server = get_server_url(server)
    token = token or os.environ.get("SENTINELAI_TOKEN")

    click.echo(click.style("\n  SentinelAI Security Scanner", fg="cyan", bold=True))
    click.echo(click.style("  " + "=" * 40, fg="cyan"))

    filename = os.path.basename(spec_file)
    click.echo(f"\n  File:     {click.style(filename, fg='white', bold=True)}")
    click.echo(f"  Server:   {server}")

    if not token:
        click.echo(f"\n  {click.style('No auth token. Use --token or set SENTINELAI_TOKEN.', fg='yellow')}")
        click.echo(f"  Register: POST {server}/api/auth/register")
        click.echo(f"  Login:    POST {server}/api/auth/login")
        return

    click.echo(f"  Output:   {output.upper()}")

    with click.progressbar(length=100, label="  Uploading & scanning") as bar:
        bar.update(10)
        try:
            with open(spec_file, "rb") as f:
                files = {"file": (filename, f)}
                data = {"api_name": os.path.splitext(filename)[0]}
                result = api_post(f"{server}/api/scans/upload", data=data, files=files, token=token)
            bar.update(70)
        except requests.exceptions.ConnectionError:
            click.echo(f"\n  {click.style('ERROR: Cannot connect to server at ' + server, fg='red', bold=True)}")
            click.echo(f"  Make sure the backend is running: uvicorn app.main:app --port 8000")
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            click.echo(f"\n  {click.style('ERROR: ' + str(e.response.status_code) + ' ' + e.response.text, fg='red', bold=True)}")
            sys.exit(1)

        bar.update(90)

        scan_id = result.get("id")
        vuln_count = result.get("total_vulnerabilities", 0)
        risk_score = result.get("risk_score", 0)
        risk_level = result.get("risk_level", "Unknown")

        bar.update(100)

    click.echo(f"\n  {click.style('Scan Complete!', fg='green', bold=True)}")
    click.echo(f"  Scan ID:      #{scan_id}")
    click.echo(f"  Endpoints:    {result.get('total_endpoints', 0)}")
    click.echo(f"  Vulnerabilities: {click.style(str(vuln_count), fg=_severity_color(vuln_count), bold=True)}")
    click.echo(f"  Risk Score:   {click.style(f'{risk_score}/100', fg=_risk_color(risk_score), bold=True)} ({risk_level})")

    if save:
        detail = api_get(f"{server}/api/scans/{scan_id}", token=token)
        ext = output
        out_file = f"sentinelai-report-{scan_id}.{ext}"

        if ext == "pdf":
            content, _ = api_download(f"{server}/api/scans/{scan_id}/report/pdf", token=token)
        else:
            content = json.dumps(detail, indent=2, default=str).encode()

        with open(out_file, "wb") as f:
            f.write(content)
        click.echo(f"  Saved:        {click.style(out_file, fg='green')}")

    click.echo(f"  View:         {server}/#/scan/{scan_id}\n")


@cli.command()
@click.option("--server", "-s", default=None, help="Backend server URL")
@click.option("--token", "-t", default=None, help="JWT auth token")
@click.option("--limit", "-n", default=10, help="Number of recent scans")
def history(server, token, limit):
    """Show recent scan history."""
    server = get_server_url(server)
    token = token or os.environ.get("SENTINELAI_TOKEN")

    click.echo(click.style("\n  SentinelAI Scan History", fg="cyan", bold=True))
    click.echo(click.style("  " + "=" * 40, fg="cyan"))

    if not token:
        click.echo(f"\n  {click.style('No auth token. Login first.', fg='yellow')}")
        return

    try:
        scans = api_get(f"{server}/api/scans/", token=token)
    except requests.exceptions.ConnectionError:
        click.echo(f"\n  {click.style('ERROR: Cannot connect to server', fg='red')}")
        return

    if not scans:
        click.echo(f"\n  {click.style('No scans found.', fg='yellow')}")
        click.echo(f"  Run: sentinelai scan <spec_file>\n")
        return

    click.echo(f"\n  {'ID':<6} {'API Name':<30} {'Vulns':<8} {'Risk':<12} {'Date':<12}")
    click.echo("  " + "-" * 68)

    for s in scans[:limit]:
        sid = str(s["id"])
        name = s["api_name"][:28]
        vulns = str(s["total_vulnerabilities"])
        score = f"{s['risk_score']}/100"
        date = s["created_at"][:10] if s.get("created_at") else "N/A"

        click.echo(f"  {sid:<6} {name:<30} {vulns:<8} {score:<12} {date:<12}")

    click.echo(f"\n  Total: {len(scans)} scan(s)\n")


@cli.command()
@click.option("--server", "-s", default=None, help="Backend server URL")
@click.option("--token", "-t", default=None, help="JWT auth token")
def stats(server, token):
    """Show security statistics dashboard."""
    server = get_server_url(server)
    token = token or os.environ.get("SENTINELAI_TOKEN")

    click.echo(click.style("\n  SentinelAI Security Statistics", fg="cyan", bold=True))
    click.echo(click.style("  " + "=" * 40, fg="cyan"))

    if not token:
        click.echo(f"\n  {click.style('No auth token. Login first.', fg='yellow')}")
        return

    try:
        data = api_get(f"{server}/api/scans/dashboard", token=token)
    except requests.exceptions.ConnectionError:
        click.echo(f"\n  {click.style('ERROR: Cannot connect to server', fg='red')}")
        return

    click.echo(f"\n  Total Scans:         {data.get('total_scans', 0)}")
    click.echo(f"  Total Vulnerabilities: {data.get('total_vulnerabilities', 0)}")
    click.echo(f"  Average Risk Score:  {data.get('average_risk_score', 0)}")

    dist = data.get("severity_distribution", {})
    if any(dist.values()):
        click.echo(f"\n  Severity Distribution:")
        for sev in ["Critical", "High", "Medium", "Low", "Info"]:
            count = dist.get(sev, 0)
            if count > 0:
                color = {"Critical": "red", "High": "red", "Medium": "yellow", "Low": "green", "Info": "white"}.get(sev, "white")
                bar = "#" * min(count, 30)
                click.echo(f"    {sev:<10} {click.style(str(count), fg=color, bold=True):<6} {click.style(bar, fg=color)}")

    recent = data.get("recent_scans", [])
    if recent:
        click.echo(f"\n  Recent Scans:")
        for s in recent[:5]:
            name = s["api_name"][:25]
            score = s["risk_score"]
            color = _risk_color(score)
            click.echo(f"    - {name:<28} {click.style(f'{score}/100', fg=color, bold=True)}")

    click.echo("")


@cli.command()
@click.option("--server", "-s", default=None, help="Backend server URL")
def health(server):
    """Check backend server health."""
    server = get_server_url(server)

    click.echo(click.style("\n  SentinelAI Health Check", fg="cyan", bold=True))
    click.echo(click.style("  " + "=" * 40, fg="cyan"))
    click.echo(f"\n  Server: {server}")

    try:
        data = api_get(f"{server}/")
        status = data.get("status", "unknown")
        if status == "operational":
            click.echo(f"  Status: {click.style('OPERATIONAL', fg='green', bold=True)}")
        else:
            click.echo(f"  Status: {click.style(status.upper(), fg='yellow', bold=True)}")
        click.echo(f"  Version: {data.get('version', 'N/A')}")
    except requests.exceptions.ConnectionError:
        click.echo(f"  Status: {click.style('UNREACHABLE', fg='red', bold=True)}")
        click.echo(f"  Start:  uvicorn app.main:app --port 8000")

    click.echo("")


def _risk_color(score):
    if score >= 80:
        return "red"
    elif score >= 60:
        return "yellow"
    elif score >= 30:
        return "yellow"
    return "green"


def _severity_color(count):
    if count > 10:
        return "red"
    elif count > 5:
        return "yellow"
    return "green"


if __name__ == "__main__":
    cli()
