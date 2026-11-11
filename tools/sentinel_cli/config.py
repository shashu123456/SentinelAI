"""Persistent CLI configuration (API URL + bearer token).

Stored outside the repository (``~/.sentinelai/config.json``) and written with
``0600`` permissions on POSIX. Environment variables win over the file so CI
never needs credentials on disk:

    SENTINEL_API_URL   e.g. http://localhost:8000
    SENTINEL_TOKEN     bearer token
"""

from __future__ import annotations

import contextlib
import json
import os
import stat
from pathlib import Path

DEFAULT_API_URL = "http://localhost:8000"


def config_path() -> Path:
    """Location of the CLI config file (respects ``SENTINEL_CONFIG``)."""
    override = os.environ.get("SENTINEL_CONFIG")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".sentinelai" / "config.json"


def load() -> dict:
    path = config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save(data: dict) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    # Best effort: the file holds a bearer token, but Windows ACLs do not map
    # onto POSIX modes, so a failure here is not fatal.
    with contextlib.suppress(OSError):
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return path


def api_url() -> str:
    return (os.environ.get("SENTINEL_API_URL") or load().get("api_url") or DEFAULT_API_URL).rstrip(
        "/"
    )


def token() -> str | None:
    return os.environ.get("SENTINEL_TOKEN") or load().get("access_token")


def clear_token() -> None:
    data = load()
    data.pop("access_token", None)
    data.pop("user", None)
    save(data)
