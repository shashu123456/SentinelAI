# Contributing to SentinelAI

> Guide for contributors, code reviewers, and maintainers.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Branch Strategy](#branch-strategy)
- [Commit Conventions](#commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Code Review Checklist](#code-review-checklist)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Architecture Guidelines](#architecture-guidelines)

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 16+ (or SQLite for development)
- Redis 7+ (optional for development)
- Git 2.40+

### Setup

```bash
# Fork the repository on GitHub

# Clone your fork
git clone https://github.com/your-username/sentinelai.git
cd sentinelai

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
python -m alembic upgrade head

# Frontend setup
cd ../frontend
npm install

# Run tests to verify setup
cd ../backend
python -m pytest tests/ -v --tb=short
```

---

## Development Workflow

### For New Features

```bash
# 1. Create feature branch
git checkout -b feat/my-new-feature

# 2. Make changes
# ... implement feature ...

# 3. Write tests
# ... add test file or extend existing ...

# 4. Run quality checks
cd backend && python -m black app/ tests/ && python -m ruff check app/
cd frontend && npm run build

# 5. Run tests
cd backend && python -m pytest tests/ -v

# 6. Commit with conventional message
git add .
git commit -m "feat(module): add new feature description"

# 7. Push and create PR
git push origin feat/my-new-feature
```

### For Bug Fixes

```bash
git checkout -b fix/issue-description
# ... fix the bug ...
# ... add a failing test first, then fix it ...
git commit -m "fix(module): resolve issue description"
```

### For Documentation

```bash
git checkout -b docs/update-description
# ... update docs ...
git commit -m "docs: update description"
```

---

## Branch Strategy

```
main                    Production-ready code
  ├── develop           Active integration branch
  │   ├── feat/feature  Feature development
  │   ├── fix/issue     Bug fixes
  │   └── refactor/*    Code refactoring
  └── release/v1.x      Release preparation
```

### Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feat/<name>` | `feat/api-key-management` |
| Fix | `fix/<issue>` | `fix/refresh-token-rotation` |
| Refactor | `refactor/<area>` | `refactor/scanner-engine` |
| Docs | `docs/<topic>` | `docs/api-documentation` |
| Test | `test/<area>` | `test/enterprise-rbac` |
| Hotfix | `hotfix/<issue>` | `hotfix/security-vulnerability` |

### Rules

- `main` is always deployable — never commit directly
- Feature branches merge into `develop` via PR
- `release/*` branches are for stabilization only
- Delete branches after merge

---

## Commit Conventions

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(copilot): add threat modeling intent` |
| `fix` | Bug fix | `fix(auth): prevent token reuse attack` |
| `perf` | Performance improvement | `perf(db): add composite index for scans` |
| `refactor` | Code refactoring | `refactor(scanner): extract rule registry` |
| `docs` | Documentation | `docs: add security architecture guide` |
| `test` | Tests | `test(enterprise): add RBAC permission tests` |
| `ci` | CI/CD | `ci(github): add CodeQL security scanning` |
| `build` | Build system | `build(docker): optimize multi-stage image` |
| `chore` | Maintenance | `chore(deps): update security dependencies` |
| `fix(security)` | Security fix | `fix(security): patch SSRF vulnerability` |

### Rules

- Use imperative mood: "add feature" not "added feature"
- Keep subject line under 72 characters
- Reference issues: `fix(auth): resolve #42 login timeout`
- Break commits into logical units
- Never commit: broken builds, failing tests, debug code, secrets

### Examples

```
feat(enterprise): add organization RBAC with 6-tier permissions

Implements complete multi-tenancy with organization isolation,
team management, and role-based access control.

- Add Organization, Team, Invitation, ApiKey models
- Implement RBAC dependency with permission matrix
- Create team and invitation services
- Add 42 enterprise tests

Closes #156
```

```
fix(scanner): prevent BOLA false positives on read-only endpoints

The OWASP scanner was flagging GET endpoints without auth as BOLA
vulnerabilities. Updated check SA-01 to only flag endpoints that
access individual resources by ID parameter.

- Modify check_sa_01 to filter on path parameters
- Add test case for read-only endpoints
- Update scanner documentation
```

---

## Pull Request Process

### Before Creating a PR

1. ✅ All tests pass (`python -m pytest tests/ -v`)
2. ✅ Code is formatted (`python -m black app/`)
3. ✅ No lint warnings (`python -m ruff check app/`)
4. ✅ Frontend builds (`npm run build`)
5. ✅ Documentation updated (if applicable)
6. ✅ No debug code or console.logs
7. ✅ No secrets or credentials committed

### PR Template

```markdown
## Description

Brief description of what this PR does.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring
- [ ] Documentation
- [ ] Tests

## Changes

- Change 1
- Change 2
- Change 3

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Screenshots (if UI change)

[Before] → [After]

## Checklist

- [ ] Code follows project conventions
- [ ] Self-review completed
- [ ] Tests pass locally
- [ ] No breaking changes (or documented)
- [ ] Documentation updated
```

### Review Process

1. **Automated checks** must pass (CI/CD pipeline)
2. **At least 1 approval** from maintainer
3. **All review comments** resolved
4. **Squash and merge** into `develop`

---

## Code Review Checklist

### Functionality

- [ ] Does the code do what the PR description says?
- [ ] Are edge cases handled?
- [ ] Are error cases handled?
- [ ] Is the feature complete?

### Code Quality

- [ ] Is the code readable and well-organized?
- [ ] Are variable/function names descriptive?
- [ ] Is there any duplicate logic?
- [ ] Are there any dead code paths?
- [ ] Is the complexity appropriate?

### Security

- [ ] Is user input validated?
- [ ] Are authorization checks in place?
- [ ] Are there any injection vulnerabilities?
- [ ] Are secrets properly handled?
- [ ] Are audit logs generated for sensitive actions?

### Testing

- [ ] Are there adequate tests?
- [ ] Do tests cover edge cases?
- [ ] Do tests cover error cases?
- [ ] Are tests independent (no shared state)?

### Performance

- [ ] Are database queries efficient?
- [ ] Is there N+1 query risk?
- [ ] Are there unnecessary computations?
- [ ] Is caching appropriate?

### Documentation

- [ ] Is the API documented?
- [ ] Are complex algorithms explained?
- [ ] Is the CHANGELOG updated?

---

## Coding Standards

### Python

```bash
# Format
python -m black app/ tests/

# Lint
python -m ruff check app/ tests/

# Type check (optional but recommended)
python -m mypy app/
```

### JavaScript/JSX

```bash
# Build check
cd frontend && npm run build

# No ESLint currently configured — follow existing patterns
```

### General Rules

| Rule | Standard |
|------|----------|
| Max line length | 88 (Python), 120 (JS) |
| Indentation | 4 spaces (Python), 2 spaces (JS) |
| Trailing commas | Yes (Python, JS) |
| Semicolons | Yes (JS) |
| Quotes | Double (Python), Single (JS) |

---

## Testing Requirements

### For Every PR

1. **New features** must include tests
2. **Bug fixes** must include a regression test
3. **All existing tests** must continue to pass
4. **Minimum coverage** — no decrease in overall coverage

### Test Naming Convention

```python
# Pattern: test_<action>_<scenario>_<expected>
def test_login_valid_credentials_returns_token():
def test_login_locked_account_returns_403():
def test_scan_upload_empty_file_returns_413():
def test_org_member_insufficient_permissions_returns_403():
```

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific module
python -m pytest tests/test_scanner.py -v

# With coverage
python -m pytest tests/ --cov=app --cov-report=term-missing

# Failed tests only
python -m pytest tests/ --lf
```

---

## Architecture Guidelines

### Before Adding a New Module

Ask yourself:

1. Can this extend an existing module?
2. Does this create a new domain?
3. What are the dependencies?
4. What is the testing strategy?

### Adding to Existing Modules

```
✅ Add a new check to security_engine/check_registry.py
✅ Add a new route to existing router
✅ Add a new method to existing repository
✅ Extend existing schema with new fields
```

### Creating New Modules

```
✅ New scanner type (e.g., container security)
✅ New integration (e.g., Jira, Slack)
✅ New domain (e.g., compliance management)

Always:
- Create model → migration → repository → service → route
- Add tests for every layer
- Register in main.py
- Update documentation
```

### File Organization

```
# When adding a feature:
1. Model: backend/app/models/models.py (extend existing file)
2. Schema: backend/app/schemas/schemas.py (extend existing file)
3. Repository: backend/app/repositories/<module>.py (new file if needed)
4. Service: backend/app/services/<module>.py (new file if needed)
5. Route: backend/app/api/routes/<module>.py (new file if needed)
6. Tests: backend/tests/test_<module>.py (new file)
7. Frontend page: frontend/src/pages/<Page>.jsx (new file)
8. Frontend API: frontend/src/services/api.js (extend existing)
```

---

## Getting Help

- **Issues** — Use GitHub Issues for bugs and feature requests
- **Discussions** — Use GitHub Discussions for questions
- **Security** — Email security@sentinelai.example.com

---

## License

By contributing to SentinelAI, you agree that your contributions will be licensed under the same license as the project.
