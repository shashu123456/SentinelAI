"""Terminal formatting helpers with zero dependencies.

Color is emitted only when stdout is a TTY and ``NO_COLOR`` is unset, so piping
into a file or a CI log stays clean. When the active console encoding cannot
represent box-drawing characters (legacy Windows code pages), the CLI falls back
to ASCII so output never crashes mid-report.
"""

from __future__ import annotations

import os
import sys
import unicodedata


def _detect_unicode() -> bool:
    encoding = (getattr(sys.stdout, "encoding", "") or "").lower()
    if "utf" in encoding:
        return True
    if os.name != "nt":
        # POSIX terminals are UTF-8 in practice even when LANG is unset.
        return True
    try:  # Windows: remember the real code page instead of trusting `encoding`
        return sys.stdout.fileno() == -1
    except (AttributeError, OSError):
        return False


UNICODE = _detect_unicode()
_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")

RESET = "\033[0m" if _COLOR else ""
BOLD = "\033[1m" if _COLOR else ""
DIM = "\033[2m" if _COLOR else ""

_SEVERITY_COLORS = {
    "critical": "\033[1;91m",
    "high": "\033[91m",
    "medium": "\033[93m",
    "low": "\033[94m",
    "info": "\033[90m",
}

# Unicode glyphs with an ASCII twin used when the console cannot encode them.
GLYPHS = {
    "ok": ("✔", "OK"),
    "warn": ("!", "!"),
    "fail": ("✖", "x"),
    "info": ("·", "-"),
    "arrow": ("→", "->"),
    "ellipsis": ("…", "..."),
    "bar_full": ("█", "#"),
    "bar_empty": ("░", "."),
    "rule": ("─", "-"),
    "party": ("🎉", ""),
}


def sym(name: str) -> str:
    """Return a glyph, downgraded to ASCII when the console cannot encode it."""
    unicode_form, ascii_form = GLYPHS[name]
    return unicode_form if UNICODE else ascii_form


def ascii_safe(text: str) -> str:
    """Transliterate text to ASCII for consoles that cannot encode it."""
    if not isinstance(text, str) or UNICODE:
        return text
    normalized = unicodedata.normalize("NFKD", text)
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
        "\u00a0": " ",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized.encode("ascii", "replace").decode("ascii")


def paint(text: str, color: str) -> str:
    """Wrap ``text`` in an ANSI color when color output is enabled."""
    if not _COLOR or not color:
        return text
    return f"{color}{text}{RESET}"


def severity(value: str) -> str:
    """Colorize a severity label, padded to a stable width."""
    return paint(f"{value:<8}", _SEVERITY_COLORS.get(str(value).lower(), "")) + " "


def header(text: str) -> str:
    return f"\n{BOLD}{text}{RESET}"


def rule(width: int = 68) -> str:
    return paint(sym("rule") * width, "\033[90m")


def risk_bar(score: int, width: int = 30) -> str:
    """Render a 0-100 risk score as a colored bar."""
    score = max(0, min(100, int(score)))
    filled = round(score / 100 * width)
    color = (
        _SEVERITY_COLORS["critical"]
        if score >= 80
        else _SEVERITY_COLORS["high"]
        if score >= 60
        else _SEVERITY_COLORS["medium"]
        if score >= 30
        else "\033[92m"
    )
    bar = sym("bar_full") * filled + paint(sym("bar_empty") * (width - filled), "\033[90m")
    return f"{paint(bar, color)} {score}/100"


def truncate(text: str, width: int) -> str:
    """Truncate to ``width`` characters, adding an ellipsis when cut."""
    if not text:
        return ""
    text = str(text).replace("\n", " ")
    return text if len(text) <= width else text[: width - 1] + sym("ellipsis")


def table(headers: list[str], rows: list[list[str]], widths: list[int] | None = None) -> str:
    """Render a plain-text table sized to its content."""
    rows = [[str(cell) for cell in row] for row in rows]
    widths = widths or [
        min(
            max([len(headers[i])] + [len(row[i]) for row in rows]) if rows else len(headers[i]),
            60,
        )
        for i in range(len(headers))
    ]
    lines = ["  ".join(h.upper().ljust(widths[i]) for i, h in enumerate(headers))]
    lines.append(paint("  ".join(sym("rule") * w for w in widths), "\033[90m"))
    for row in rows:
        lines.append("  ".join(row[i].ljust(widths[i]) for i in range(len(headers))))
    return "\n".join(lines)
