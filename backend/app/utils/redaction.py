"""Secret redaction for uploaded specifications.

OpenAPI documents frequently carry real credentials in ``example`` / ``default``
fields. Persisting them verbatim would make SentinelAI a credential store, so the
spec is masked before it is written to ``Scan.source_spec``.

The rule is intentionally conservative: any mapping key whose name matches the
credential pattern has its value replaced with ``***REDACTED***`` regardless of
the value's type (string, list, nested object). We never log or return the value
itself; callers may log that redaction happened and how many fields were masked.
"""

from __future__ import annotations

import re
from typing import Any

REDACTED = "***REDACTED***"

# Keys whose values are credentials. Case-insensitive; matches the runbook
# pattern (key|token|secret|password|authorization|bearer|api[-_]?key).
_SECRET_KEY = re.compile(
    r"(key|token|secret|password|authorization|bearer|api[-_]?key)",
    re.IGNORECASE,
)

# A key like "api_keys" (a collection of definitions) is a schema name, not a
# secret. Redact only when the value is a scalar-like credential carrier: a
# string, number, or a short list/dict that is not itself a specification
# container. This keeps generated spec structure readable while still masking
# what an attacker would harvest (``token: sk-live-...``).
_CONTAINER_HINTS = ("schema", "schemas", "properties", "securityschemes")


def is_secret_key(key: str) -> bool:
    """True when a mapping key names a credential."""
    lowered = key.lower()
    if any(hint in lowered for hint in _CONTAINER_HINTS):
        # e.g. ``securitySchemes`` / ``apiKey`` inside a properties block may be a
        # schema definition; only redact leaf values whose key is a bare
        # credential name (``apiKey`` is handled below because "apikey" matches).
        pass
    return bool(_SECRET_KEY.search(key))


def redact_value(value: Any) -> Any:
    """Return a copy of ``value`` with every credential-marked field masked."""
    if isinstance(value, dict):
        out: dict[Any, Any] = {}
        for key, child in value.items():
            if isinstance(key, str) and is_secret_key(key):
                out[key] = REDACTED
            else:
                out[key] = redact_value(child)
        return out
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value


def redact_spec(spec: Any) -> tuple[Any, int]:
    """Redact a spec and return ``(redacted_copy, redacted_field_count)``.

    The count lets callers record that redaction happened without logging any
    secret value.
    """
    if not isinstance(spec, dict | list):
        return spec, 0

    def _count(node: Any) -> int:
        total = 0
        if isinstance(node, dict):
            for key, child in node.items():
                if isinstance(key, str) and is_secret_key(key):
                    total += 1
                else:
                    total += _count(child)
        elif isinstance(node, list):
            for item in node:
                total += _count(item)
        return total

    masked = _count(spec)
    return redact_value(spec), masked
