# ADR-001: Schema Modularization

## Status

Accepted

## Context

The original `schemas.py` was a monolithic file containing all Pydantic schemas (~200 lines). As the project grew to 183 routes across 15 modules, the single schema file became a maintenance bottleneck. Changes to auth schemas risked accidentally breaking scan schemas, and import paths became inconsistent.

## Decision

Split `schemas.py` into domain-specific modules:

| Module | Responsibility |
|--------|---------------|
| `constants.py` | Shared sort fields, severity levels, parse helpers |
| `auth.py` | User registration, login, tokens, password reset |
| `scan.py` | Scan CRUD, listing, detail response |
| `finding.py` | Finding response, AI analysis, vulnerability items |
| `analytics.py` | Risk scores, OWASP distribution, trends |
| `dashboard.py` | Dashboard overview, stats, report response |

The original `schemas.py` is preserved as a re-export shim for backward compatibility. All existing imports (`from app.schemas.schemas import X`) continue to work unchanged.

## Consequences

**Positive:**
- Each domain schema can evolve independently
- Import paths are explicit and self-documenting
- Reduced merge conflicts when multiple developers work on different domains
- Circular dependencies eliminated via shared `constants.py`

**Negative:**
- One extra `__init__.py` to maintain `model_rebuild()` for cross-module forward references
- Backward-compatibility shim adds a layer of indirection

**Mitigation:**
- New code should import from `app.schemas.scan`, `app.schemas.finding`, etc.
- The shim exists solely for legacy compatibility and can be removed in v2.0
