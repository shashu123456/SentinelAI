"""In-document ``$ref`` resolution for OpenAPI/Swagger specifications."""

from __future__ import annotations

from typing import Any

from app.core.security_engine.errors import WarningSink


def is_internal_ref(ref: Any) -> bool:
    """Return True when ``ref`` is an in-document JSON pointer (``#/...``)."""
    return isinstance(ref, str) and ref.startswith("#/")


def decode_json_pointer(ref: str) -> list[str]:
    """Decode a JSON pointer fragment into its path segments.

    Handles the ``~1`` (``/``) and ``~0`` (``~``) escapes mandated by
    RFC 6901 as well as percent-encoded segments.
    """
    fragment = ref[2:] if ref.startswith("#/") else ref.lstrip("#/")
    if not fragment:
        return []
    return [segment.replace("~1", "/").replace("~0", "~") for segment in fragment.split("/")]


class RefResolver:
    """Resolves ``#/...`` JSON pointers against a single document.

    The resolver is bound to one (normalized) specification and a
    :class:`WarningSink`. Lookups are memoized; unresolved pointers return
    ``None`` and are reported once through the sink.
    """

    def __init__(self, document: dict, warnings: WarningSink) -> None:
        self._document = document
        self._warnings = warnings
        self._cache: dict[str, Any] = {}
        self._reported: set[str] = set()

    def get(self, ref: str, *, location: str | None = None) -> Any:
        """Resolve ``ref`` to its target, or ``None`` when unresolvable."""
        if not is_internal_ref(ref):
            if ref not in self._reported:
                self._reported.add(ref)
                self._warnings.add(
                    "external_ref",
                    f"Cannot resolve external reference '{ref}'; external documents are not loaded.",
                    location=location,
                    detail=ref,
                )
            return None

        if ref in self._cache:
            return self._cache[ref]

        current: Any = self._document
        for segment in decode_json_pointer(ref):
            if isinstance(current, dict) and segment in current:
                current = current[segment]
            else:
                if ref not in self._reported:
                    self._reported.add(ref)
                    self._warnings.add(
                        "unresolved_ref",
                        f"Reference '{ref}' does not resolve in the specification.",
                        location=location,
                        detail=ref,
                    )
                self._cache[ref] = None
                return None

        self._cache[ref] = current
        return current
