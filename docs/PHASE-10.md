# Phase 10 — Enterprise Multi-Tenancy & RBAC

## Overview

Transformed SentinelAI from a single-user application into a true enterprise SaaS platform with full multi-tenancy, role-based access control, organization management, teams, invitations, API keys, and billing-ready architecture.

---

## What Was Built

### 1. Database Models (6 new models, 4 enhanced)

| Model | Purpose |
|-------|---------|
| `Organization` | Enhanced with subscription tiers, member limits, project limits, scan quotas, SSO settings, email domain restrictions |
| `OrganizationMember` | Enhanced with `invited_by`, enterprise roles (`owner`, `admin`, `security_engineer`, `developer`, `viewer`) |
| `Project` | Links to organization, supports project-level member management |
| `ProjectMember` | New: project-level RBAC with `admin`, `security_engineer`, `developer`, `viewer` |
| `Team` | New: organizational team grouping within an org |
| `TeamMember` | New: team membership with `admin` and `member` roles |
| `Invitation` | New: email-based user invitations with token, expiry, status tracking |
| `ApiKey` | New: programmatic API access with scopes, expiry, prefix, hash |
| `Scan` | Enhanced with `organization_id` for org-level scan isolation |

### 2. Enterprise RBAC System

**Permission hierarchy:**
```
Global: super_admin
Organization: owner > admin > security_engineer > developer > viewer
Project: admin > security_engineer > developer > viewer
Team: admin > member
```

**Key files:**
- `backend/app/utils/rbac.py` — RBAC dependency factories
- Supports org-level, project-level, and team-level permission checks
- Automatic fallback: org admin → project admin access
- Super admin gets owner-level access everywhere

### 3. New Backend Routes (22+ new endpoints)

| Route | Endpoints | RBAC |
|-------|-----------|------|
| `/api/organizations/{org_id}/teams` | CRUD + member management | admin+ |
| `/api/organizations/{org_id}/invitations` | Send, list, revoke, accept, cleanup | admin+ |
| `/api/organizations/{org_id}/api-keys` | Create, list, revoke | admin+ / viewer (list) |
| `/api/organizations/{org_id}/settings` | Get, update | admin+ / owner (update) |
| `/api/organizations/{org_id}/dashboard` | Org aggregate metrics | viewer+ |
| `/api/organizations/{org_id}/analytics` | Time-series analytics | viewer+ |
| `/api/scans/org/{org_id}` | Org-scoped scan listing | org member |
| `/api/scans/project/{project_id}` | Project-scoped scan listing | org member |

### 4. Backend Services

| Service | Purpose |
|---------|---------|
| `team_service.py` | Create teams, add/remove members, audit logging |
| `invitation_service.py` | Create invitations, accept/revoke, expiry cleanup |
| `api_key_service.py` | Create API keys, validate, revoke, scope management |
| `org_analytics_service.py` | Org-level dashboards, time-series, severity distributions |

### 5. Repositories

| Repository | Methods |
|------------|---------|
| `TeamRepository` | create, list_for_org, get_by_slug, add_member, remove_member, is_member, get_member_role, list_members, count_members |
| `InvitationRepository` | create, get_by_token, get_pending_by_email, list_pending_for_org, accept, revoke, cleanup_expired |
| `ApiKeyRepository` | generate_key, create_key, get_by_hash, validate_key, list_for_org, revoke, count_active_for_org |
| `OrganizationRepository` | Enhanced: count_members, list_members, update_member_role, can_add_member, can_create_project |
| `ProjectRepository` | Enhanced: add_member, remove_member, list_members, count_members |

### 6. Frontend (5 new pages + context)

| Component | Purpose |
|-----------|---------|
| `OrgContext` | Organization and project state management with localStorage persistence |
| `OrgDashboard` | Organization-level metrics dashboard |
| `TeamManagement` | Create teams, manage members, RBAC-aware |
| `Invitations` | Send invitations, track status, revoke |
| `ApiKeys` | Create API keys, copy-once display, revoke |
| `OrgSettings` | Subscription info, security settings, SSO, email domains |

### 7. Navigation Updates

- **Navbar**: Organization switcher dropdown, project switcher dropdown
- **Sidebar**: New "Enterprise" section with Teams, Invitations, API Keys, Org Settings
- **App.jsx**: OrgProvider wraps entire app, 5 new routes

### 8. Tests

**42 enterprise multi-tenancy tests** covering:
- Organization CRUD with RBAC (6 tests)
- Member management with role checks (6 tests)
- Project management with isolation (4 tests)
- Team CRUD with RBAC (5 tests)
- Invitation lifecycle (4 tests)
- API key lifecycle (4 tests)
- Organization settings (3 tests)
- Organization dashboard & analytics (2 tests)
- Scan isolation by organization (3 tests)
- Cross-org data isolation (5 tests)

---

## RBAC Permission Matrix

| Action | Viewer | Developer | Security Eng | Admin | Owner |
|--------|--------|-----------|-------------|-------|-------|
| View org | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create project | ❌ | ✅ | ✅ | ✅ | ✅ |
| Run scans | ✅ | ✅ | ✅ | ✅ | ✅ |
| View audit logs | ✅ | ✅ | ✅ | ✅ | ✅ |
| Invite members | ❌ | ❌ | ❌ | ✅ | ✅ |
| Manage teams | ❌ | ❌ | ❌ | ✅ | ✅ |
| Create API keys | ❌ | ❌ | ❌ | ✅ | ✅ |
| Update org settings | ❌ | ❌ | ❌ | ❌ | ✅ |
| Change member roles | ❌ | ❌ | ❌ | ❌ | ✅ |
| Delete org | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## Data Isolation Guarantees

1. **Organization isolation**: Users can only see data for orgs they belong to
2. **Project isolation**: Projects are scoped to their parent organization
3. **Scan isolation**: Scans are linked to organizations; cross-org access is blocked
4. **API key isolation**: API keys are scoped to organizations
5. **Audit log isolation**: Audit events are scoped to the acting user

---

## Billing-Ready Architecture

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `subscription_tier` | String | `free` | `free`, `starter`, `professional`, `enterprise` |
| `max_members` | Integer | `10` | Organization member limit |
| `max_projects` | Integer | `5` | Project creation limit |
| `max_scans_per_month` | Integer | `50` | Monthly scan quota |
| `scans_used_this_month` | Integer | `0` | Current month usage |

---

## Files Created

| File | Purpose |
|------|---------|
| `backend/app/utils/rbac.py` | Enterprise RBAC dependency system |
| `backend/app/repositories/teams.py` | Team & TeamMember repository |
| `backend/app/repositories/invitations.py` | Invitation repository |
| `backend/app/repositories/api_keys.py` | API key repository with secure key management |
| `backend/app/services/team_service.py` | Team management service |
| `backend/app/services/invitation_service.py` | Invitation lifecycle service |
| `backend/app/services/api_key_service.py` | API key management service |
| `backend/app/services/org_analytics_service.py` | Organization analytics service |
| `backend/app/api/routes/teams.py` | Teams API routes |
| `backend/app/api/routes/invitations.py` | Invitations API routes |
| `backend/app/api/routes/api_keys.py` | API keys API routes |
| `backend/alembic/versions/a1b2c3d4e5f6_enterprise_multi_tenancy.py` | Database migration |
| `backend/tests/test_enterprise_multitenancy.py` | 42 comprehensive tests |
| `frontend/src/context/OrgContext.jsx` | Organization state management |
| `frontend/src/pages/OrgDashboard.jsx` | Organization dashboard |
| `frontend/src/pages/TeamManagement.jsx` | Team management page |
| `frontend/src/pages/Invitations.jsx` | Invitation management page |
| `frontend/src/pages/ApiKeys.jsx` | API key management page |
| `frontend/src/pages/OrgSettings.jsx` | Organization settings page |

## Files Modified

| File | Changes |
|------|---------|
| `backend/app/models/models.py` | 6 new models, enhanced Organization, Scan, OrganizationMember, Project |
| `backend/app/repositories/organizations.py` | Enhanced with member management, capacity checks |
| `backend/app/api/routes/organizations.py` | Full rewrite with enterprise RBAC, settings, dashboard, analytics |
| `backend/app/api/routes/scans.py` | Added org/project association on upload, org-scoped listing |
| `backend/app/schemas/schemas.py` | Added `organization_id`, `project_id` to ScanResponse |
| `backend/app/main.py` | Registered teams, invitations, api_keys routers |
| `backend/app/services/invitation_service.py` | Fixed datetime comparison for SQLite compatibility |
| `backend/tests/test_organizations.py` | Updated to match new MemberInvite schema |
| `frontend/src/App.jsx` | Added OrgProvider, 5 new lazy routes |
| `frontend/src/components/Navbar.jsx` | Org/project switchers, Enterprise nav section |
| `frontend/src/App.css` | Org/project switcher CSS |
| `frontend/src/services/api.js` | Added teams, invitations, apiKeys service methods |

---

## Test Results

- **Enterprise multi-tenancy tests:** 42/42 passed ✅
- **Organization tests:** 10/10 passed ✅
- **Scanner tests:** 18/18 passed ✅
- **Frontend build:** Clean ✅
