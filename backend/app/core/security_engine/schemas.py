"""Schema resolution and traversal utilities for API specifications.

``resolve_schema`` deep-resolves every ``$ref`` reachable from a schema,
flattens ``allOf`` compositions, and guards against runaway recursion in
recursive schemas. ``iter_schema_properties`` walks a resolved schema and
yields every property path (including nested objects, array items, and
``additionalProperties``) for downstream rule analysis.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from app.core.security_engine.errors import WarningSink
from app.core.security_engine.ref_resolver import RefResolver

MAX_SCHEMA_DEPTH = 100

_REF_KEY = "$ref"
_COMPOSITION_KEYS = ("allOf", "oneOf", "anyOf")


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge ``overlay`` into ``base`` and return a new dict.

    Dictionaries are merged key-by-key, ``required`` lists are unioned, and
    conflicting ``type`` values collapse into a list of unique types.
    """
    result = dict(base)
    for key, value in overlay.items():
        if key not in result:
            result[key] = value
        elif isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        elif key == "required" and isinstance(result[key], list) and isinstance(value, list):
            seen = set(result[key])
            for item in value:
                if item not in seen:
                    result[key].append(item)
                    seen.add(item)
        elif key == "type" and result[key] != value:
            existing = result[key] if isinstance(result[key], list) else [result[key]]
            incoming = value if isinstance(value, list) else [value]
            combined: list[Any] = []
            for candidate in existing + incoming:
                if candidate not in combined:
                    combined.append(candidate)
            result[key] = combined[0] if len(combined) == 1 else combined
        elif result[key] != value:
            result[key] = value
    return result


def merge_all_of(schema: dict) -> dict:
    """Merge all ``allOf`` members into a single schema object."""
    if not isinstance(schema.get("allOf"), list):
        return schema
    merged = {key: value for key, value in schema.items() if key != "allOf"}
    for member in schema["allOf"]:
        if isinstance(member, dict):
            merged = _deep_merge(merged, member)
    return merged


def resolve_schema(
    schema: Any,
    resolver: RefResolver,
    warnings: WarningSink,
    *,
    location: str | None = None,
    _active: set[str] | None = None,
    _depth: int = 0,
) -> Any:
    """Deep-resolve ``$ref`` references in ``schema`` and flatten ``allOf``.

    Recursive references are truncated to a ``{"$ref": ...}`` leaf marker so
    that self-referential schemas (e.g. a ``Node`` containing ``children``)
    resolve without infinite recursion.
    """
    if _active is None:
        _active = set()

    if _depth > MAX_SCHEMA_DEPTH:
        warnings.add(
            "schema_depth",
            "Schema nesting exceeds the maximum depth; truncated during resolution.",
            location=location,
        )
        return {}

    if isinstance(schema, list):
        return [
            resolve_schema(
                item, resolver, warnings, location=location, _active=_active, _depth=_depth + 1
            )
            for item in schema
        ]
    if not isinstance(schema, dict):
        return schema

    if _REF_KEY in schema:
        ref = schema[_REF_KEY]
        if ref in _active:
            return {_REF_KEY: ref}
        target = resolver.get(ref, location=location)
        if target is None:
            return {}
        if not isinstance(target, dict):
            return target
        return resolve_schema(
            target,
            resolver,
            warnings,
            location=location,
            _active=_active | {ref},
            _depth=_depth + 1,
        )

    result: dict[str, Any] = {}
    for key, value in schema.items():
        if key in ("properties", "patternProperties", "definitions"):
            if isinstance(value, dict):
                result[key] = {
                    name: resolve_schema(
                        child,
                        resolver,
                        warnings,
                        location=location,
                        _active=_active,
                        _depth=_depth + 1,
                    )
                    for name, child in value.items()
                }
            else:
                result[key] = value
        elif key in ("items", "additionalProperties", "not", "contains"):
            result[key] = resolve_schema(
                value, resolver, warnings, location=location, _active=_active, _depth=_depth + 1
            )
        elif key in (*_COMPOSITION_KEYS, "prefixItems"):
            if isinstance(value, list):
                result[key] = [
                    resolve_schema(
                        item,
                        resolver,
                        warnings,
                        location=location,
                        _active=_active,
                        _depth=_depth + 1,
                    )
                    for item in value
                ]
            else:
                result[key] = value
        else:
            result[key] = value

    return merge_all_of(result)


def iter_schema_properties(schema: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    """Yield ``(path, property_schema)`` for every property in ``schema``.

    Traverses nested objects (``address.city``), array items (``items[]``),
    ``additionalProperties`` schemas, and ``allOf``/``oneOf``/``anyOf``
    branches. Paths are relative to the schema root.
    """
    if not isinstance(schema, dict):
        return
    seen: set[int] = set()

    def _walk(node: Any, path: str) -> Iterator[tuple[str, Any]]:
        if not isinstance(node, dict) or id(node) in seen:
            return
        seen.add(id(node))

        for key in _COMPOSITION_KEYS:
            for member in node.get(key, []) or []:
                yield from _walk(member, path)

        properties = node.get("properties")
        if isinstance(properties, dict):
            for name, prop in properties.items():
                full = f"{path}.{name}" if path else name
                yield full, prop
                yield from _walk(prop, full)

        items = node.get("items")
        if isinstance(items, dict):
            child = f"{path}[]" if path else "[]"
            yield from _walk(items, child)

        additional = node.get("additionalProperties")
        if isinstance(additional, dict):
            yield from _walk(additional, path)

    yield from _walk(schema, prefix)
