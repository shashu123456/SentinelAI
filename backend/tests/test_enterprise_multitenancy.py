"""Comprehensive tests for Enterprise Multi-Tenancy features.

Tests cover:
- Organization CRUD with RBAC
- Member management with role checks
- Team CRUD with RBAC
- Invitation lifecycle
- API key lifecycle
- Organization analytics
- Scan isolation by organization/project
- Cross-org data isolation
"""

import secrets
import time

import pytest

# ── Helpers ────────────────────────────────────────────────────────────


def _register_user(client, username=None):
    """Register a user and return (user_data, token)."""
    username = username or f"user_{secrets.token_hex(4)}"
    resp = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@test.example.com",
            "password": "TestPass123!",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return data["user"], data["access_token"]


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _create_org(client, headers, name=None, slug=None):
    name = name or f"Org {secrets.token_hex(4)}"
    slug = slug or f"org-{secrets.token_hex(4)}"
    resp = client.post(
        "/api/organizations",
        json={"name": name, "slug": slug},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Organization Tests ─────────────────────────────────────────────────


class TestOrganizationCRUD:
    def test_create_organization(self, client):
        user, token = _register_user(client)
        headers = _auth_header(token)
        org = _create_org(client, headers, "Acme Corp", "acme-corp")
        assert org["name"] == "Acme Corp"
        assert org["slug"] == "acme-corp"
        assert org["subscription_tier"] == "free"
        assert org["max_members"] == 10

    def test_create_duplicate_slug(self, client):
        user, token = _register_user(client)
        headers = _auth_header(token)
        _create_org(client, headers, "Org1", "my-org")
        resp = client.post(
            "/api/organizations",
            json={"name": "Org2", "slug": "my-org"},
            headers=headers,
        )
        assert resp.status_code == 409

    def test_list_organizations(self, client):
        user, token = _register_user(client)
        headers = _auth_header(token)
        _create_org(client, headers, "Org1", "org-1")
        _create_org(client, headers, "Org2", "org-2")
        resp = client.get("/api/organizations", headers=headers)
        assert resp.status_code == 200
        orgs = resp.json()
        assert len(orgs) >= 2

    def test_get_organization(self, client):
        user, token = _register_user(client)
        headers = _auth_header(token)
        org = _create_org(client, headers)
        resp = client.get(f"/api/organizations/{org['id']}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == org["name"]

    def test_get_organization_not_member(self, client):
        user1, token1 = _register_user(client, "user_a")
        user2, token2 = _register_user(client, "user_b")
        org = _create_org(client, _auth_header(token1))
        resp = client.get(f"/api/organizations/{org['id']}", headers=_auth_header(token2))
        assert resp.status_code == 403

    def test_update_organization(self, client):
        user, token = _register_user(client)
        headers = _auth_header(token)
        org = _create_org(client, headers)
        resp = client.patch(
            f"/api/organizations/{org['id']}",
            json={"name": "Updated Corp"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Corp"


# ── Member Management Tests ───────────────────────────────────────────


class TestMemberManagement:
    def test_add_member(self, client):
        user1, token1 = _register_user(client, "owner_user")
        user2, token2 = _register_user(client, "member_user")
        org = _create_org(client, _auth_header(token1))
        resp = client.post(
            f"/api/organizations/{org['id']}/members",
            json={"email": f"{user2['username']}@test.example.com", "role": "developer"},
            headers=_auth_header(token1),
        )
        assert resp.status_code == 200

    def test_add_member_not_admin(self, client):
        user1, token1 = _register_user(client, "owner_user")
        user2, token2 = _register_user(client, "regular_user")
        user3, token3 = _register_user(client, "viewer_user")
        org = _create_org(client, _auth_header(token1))

        # Add user2 as viewer
        client.post(
            f"/api/organizations/{org['id']}/members",
            json={"email": f"{user2['username']}@test.example.com", "role": "viewer"},
            headers=_auth_header(token1),
        )

        # viewer tries to add member — should fail
        resp = client.post(
            f"/api/organizations/{org['id']}/members",
            json={"email": f"{user3['username']}@test.example.com", "role": "viewer"},
            headers=_auth_header(token2),
        )
        assert resp.status_code == 403

    def test_list_members(self, client):
        user, token = _register_user(client)
        headers = _auth_header(token)
        org = _create_org(client, headers)
        resp = client.get(f"/api/organizations/{org['id']}/members", headers=headers)
        assert resp.status_code == 200
        members = resp.json()
        assert len(members) >= 1  # Owner is always a member

    def test_remove_member(self, client):
        user1, token1 = _register_user(client, "owner_user")
        user2, token2 = _register_user(client, "member_user")
        org = _create_org(client, _auth_header(token1))

        client.post(
            f"/api/organizations/{org['id']}/members",
            json={"email": f"{user2['username']}@test.example.com", "role": "developer"},
            headers=_auth_header(token1),
        )
        resp = client.delete(
            f"/api/organizations/{org['id']}/members/{user2['id']}",
            headers=_auth_header(token1),
        )
        assert resp.status_code == 200

    def test_cannot_remove_owner(self, client):
        user, token = _register_user(client)
        org = _create_org(client, _auth_header(token))
        resp = client.delete(
            f"/api/organizations/{org['id']}/members/{user['id']}",
            headers=_auth_header(token),
        )
        assert resp.status_code == 400

    def test_update_member_role(self, client):
        user1, token1 = _register_user(client, "owner_user")
        user2, token2 = _register_user(client, "member_user")
        org = _create_org(client, _auth_header(token1))

        client.post(
            f"/api/organizations/{org['id']}/members",
            json={"email": f"{user2['username']}@test.example.com", "role": "viewer"},
            headers=_auth_header(token1),
        )
        resp = client.patch(
            f"/api/organizations/{org['id']}/members/{user2['id']}/role",
            json={"role": "admin"},
            headers=_auth_header(token1),
        )
        assert resp.status_code == 200


# ── Project Tests ──────────────────────────────────────────────────────


class TestProjectManagement:
    def test_create_project(self, client):
        user, token = _register_user(client)
        headers = _auth_header(token)
        org = _create_org(client, headers)
        resp = client.post(
            f"/api/organizations/{org['id']}/projects",
            json={"name": "API Project", "slug": "api-project"},
            headers=headers,
        )
        assert resp.status_code == 201
        proj = resp.json()
        assert proj["name"] == "API Project"
        assert proj["organization_id"] == org["id"]

    def test_list_projects(self, client):
        user, token = _register_user(client)
        headers = _auth_header(token)
        org = _create_org(client, headers)
        client.post(
            f"/api/organizations/{org['id']}/projects",
            json={"name": "Proj1", "slug": "proj-1"},
            headers=headers,
        )
        resp = client.get(f"/api/organizations/{org['id']}/projects", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_project_not_member(self, client):
        user1, token1 = _register_user(client, "owner")
        user2, token2 = _register_user(client, "outsider")
        org = _create_org(client, _auth_header(token1))
        client.post(
            f"/api/organizations/{org['id']}/projects",
            json={"name": "Proj", "slug": "proj"},
            headers=_auth_header(token1),
        )
        resp = client.get(f"/api/organizations/{org['id']}/projects", headers=_auth_header(token2))
        assert resp.status_code == 403

    def test_project_member_management(self, client):
        user1, token1 = _register_user(client, "owner")
        user2, token2 = _register_user(client, "dev")
        org = _create_org(client, _auth_header(token1))
        resp = client.post(
            f"/api/organizations/{org['id']}/projects",
            json={"name": "Proj", "slug": "proj"},
            headers=_auth_header(token1),
        )
        project_id = resp.json()["id"]

        # Add member to project
        resp = client.post(
            f"/api/organizations/{org['id']}/projects/{project_id}/members",
            json={"user_id": user2["id"], "role": "developer"},
            headers=_auth_header(token1),
        )
        assert resp.status_code == 200

        # Get project with members
        resp = client.get(
            f"/api/organizations/{org['id']}/projects/{project_id}",
            headers=_auth_header(token1),
        )
        assert resp.status_code == 200
        assert len(resp.json()["members"]) >= 1


# ── Team Tests ─────────────────────────────────────────────────────────


class TestTeamManagement:
    def test_create_team(self, client):
        user, token = _register_user(client)
        headers = _auth_header(token)
        org = _create_org(client, headers)
        resp = client.post(
            f"/api/organizations/{org['id']}/teams",
            json={"name": "Security Team", "slug": "security"},
            headers=headers,
        )
        assert resp.status_code == 201
        team = resp.json()
        assert team["name"] == "Security Team"

    def test_list_teams(self, client):
        user, token = _register_user(client)
        headers = _auth_header(token)
        org = _create_org(client, headers)
        client.post(
            f"/api/organizations/{org['id']}/teams",
            json={"name": "Team1", "slug": "team-1"},
            headers=headers,
        )
        resp = client.get(f"/api/organizations/{org['id']}/teams", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_team_member_management(self, client):
        user1, token1 = _register_user(client, "admin")
        user2, token2 = _register_user(client, "member")
        org = _create_org(client, _auth_header(token1))

        # Add user2 as org member
        client.post(
            f"/api/organizations/{org['id']}/members",
            json={"email": f"{user2['username']}@test.example.com", "role": "developer"},
            headers=_auth_header(token1),
        )

        # Create team
        resp = client.post(
            f"/api/organizations/{org['id']}/teams",
            json={"name": "Team", "slug": "team"},
            headers=_auth_header(token1),
        )
        team_id = resp.json()["id"]

        # Add member to team
        resp = client.post(
            f"/api/organizations/{org['id']}/teams/{team_id}/members",
            json={"user_id": user2["id"], "role": "member"},
            headers=_auth_header(token1),
        )
        assert resp.status_code == 200

        # Get team detail
        resp = client.get(
            f"/api/organizations/{org['id']}/teams/{team_id}",
            headers=_auth_header(token1),
        )
        assert resp.status_code == 200
        assert len(resp.json()["members"]) >= 1

    def test_delete_team(self, client):
        user, token = _register_user(client)
        org = _create_org(client, _auth_header(token))
        resp = client.post(
            f"/api/organizations/{org['id']}/teams",
            json={"name": "Temp Team", "slug": "temp"},
            headers=_auth_header(token),
        )
        team_id = resp.json()["id"]
        resp = client.delete(
            f"/api/organizations/{org['id']}/teams/{team_id}",
            headers=_auth_header(token),
        )
        assert resp.status_code == 200

    def test_viewer_cannot_create_team(self, client):
        user1, token1 = _register_user(client, "owner")
        user2, token2 = _register_user(client, "viewer")
        org = _create_org(client, _auth_header(token1))
        client.post(
            f"/api/organizations/{org['id']}/members",
            json={"email": f"{user2['username']}@test.example.com", "role": "viewer"},
            headers=_auth_header(token1),
        )
        resp = client.post(
            f"/api/organizations/{org['id']}/teams",
            json={"name": "Team", "slug": "team"},
            headers=_auth_header(token2),
        )
        assert resp.status_code == 403


# ── Invitation Tests ───────────────────────────────────────────────────


class TestInvitationManagement:
    def test_send_invitation(self, client):
        user1, token1 = _register_user(client, "admin")
        user2, token2 = _register_user(client, "invitee")
        org = _create_org(client, _auth_header(token1))

        resp = client.post(
            f"/api/organizations/{org['id']}/invitations",
            json={"email": f"{user2['username']}@test.example.com", "role": "developer"},
            headers=_auth_header(token1),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == f"{user2['username']}@test.example.com"
        assert data["status"] == "pending"
        assert "token" in data

    def test_list_invitations(self, client):
        user1, token1 = _register_user(client, "admin")
        user2, token2 = _register_user(client, "invitee")
        org = _create_org(client, _auth_header(token1))

        client.post(
            f"/api/organizations/{org['id']}/invitations",
            json={"email": f"{user2['username']}@test.example.com", "role": "viewer"},
            headers=_auth_header(token1),
        )

        resp = client.get(
            f"/api/organizations/{org['id']}/invitations", headers=_auth_header(token1)
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_accept_invitation(self, client):
        user1, token1 = _register_user(client, "admin")
        user2, token2 = _register_user(client, "invitee")
        org = _create_org(client, _auth_header(token1))

        resp = client.post(
            f"/api/organizations/{org['id']}/invitations",
            json={"email": f"{user2['username']}@test.example.com", "role": "developer"},
            headers=_auth_header(token1),
        )
        token = resp.json()["token"]

        resp = client.post(
            f"/api/organizations/{org['id']}/invitations/accept",
            json={"token": token},
            headers=_auth_header(token2),
        )
        assert resp.status_code == 200

    def test_revoke_invitation(self, client):
        user1, token1 = _register_user(client, "admin")
        user2, token2 = _register_user(client, "invitee")
        org = _create_org(client, _auth_header(token1))

        resp = client.post(
            f"/api/organizations/{org['id']}/invitations",
            json={"email": f"{user2['username']}@test.example.com", "role": "viewer"},
            headers=_auth_header(token1),
        )
        invite_id = resp.json()["id"]

        resp = client.delete(
            f"/api/organizations/{org['id']}/invitations/{invite_id}",
            headers=_auth_header(token1),
        )
        assert resp.status_code == 200


# ── API Key Tests ──────────────────────────────────────────────────────


class TestApiKeyManagement:
    def test_create_api_key(self, client):
        user, token = _register_user(client)
        headers = _auth_header(token)
        org = _create_org(client, headers)

        resp = client.post(
            f"/api/organizations/{org['id']}/api-keys",
            json={"name": "CI/CD Key"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "CI/CD Key"
        assert data["key_prefix"].startswith("sai_")
        assert "raw_key" in data  # Only shown at creation

    def test_list_api_keys(self, client):
        user, token = _register_user(client)
        headers = _auth_header(token)
        org = _create_org(client, headers)

        client.post(
            f"/api/organizations/{org['id']}/api-keys",
            json={"name": "Key1"},
            headers=headers,
        )
        resp = client.get(f"/api/organizations/{org['id']}/api-keys", headers=headers)
        assert resp.status_code == 200
        keys = resp.json()
        assert len(keys) >= 1
        # raw_key should NOT be in list response
        assert "raw_key" not in keys[0]

    def test_revoke_api_key(self, client):
        user, token = _register_user(client)
        headers = _auth_header(token)
        org = _create_org(client, headers)

        resp = client.post(
            f"/api/organizations/{org['id']}/api-keys",
            json={"name": "Revoke Me"},
            headers=headers,
        )
        key_id = resp.json()["id"]

        resp = client.delete(
            f"/api/organizations/{org['id']}/api-keys/{key_id}",
            headers=headers,
        )
        assert resp.status_code == 200

    def test_viewer_cannot_create_key(self, client):
        user1, token1 = _register_user(client, "owner")
        user2, token2 = _register_user(client, "viewer")
        org = _create_org(client, _auth_header(token1))
        client.post(
            f"/api/organizations/{org['id']}/members",
            json={"email": f"{user2['username']}@test.example.com", "role": "viewer"},
            headers=_auth_header(token1),
        )
        resp = client.post(
            f"/api/organizations/{org['id']}/api-keys",
            json={"name": "Fail"},
            headers=_auth_header(token2),
        )
        assert resp.status_code == 403


# ── Organization Settings Tests ────────────────────────────────────────


class TestOrgSettings:
    def test_get_settings(self, client):
        user, token = _register_user(client)
        org = _create_org(client, _auth_header(token))
        resp = client.get(
            f"/api/organizations/{org['id']}/settings",
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        settings = resp.json()
        assert settings["subscription_tier"] == "free"
        assert settings["default_project_visibility"] == "private"

    def test_update_settings(self, client):
        user, token = _register_user(client)
        org = _create_org(client, _auth_header(token))
        resp = client.patch(
            f"/api/organizations/{org['id']}/settings",
            json={"default_project_visibility": "public"},
            headers=_auth_header(token),
        )
        assert resp.status_code == 200

    def test_viewer_cannot_update_settings(self, client):
        user1, token1 = _register_user(client, "owner")
        user2, token2 = _register_user(client, "viewer")
        org = _create_org(client, _auth_header(token1))
        client.post(
            f"/api/organizations/{org['id']}/members",
            json={"email": f"{user2['username']}@test.example.com", "role": "viewer"},
            headers=_auth_header(token1),
        )
        resp = client.patch(
            f"/api/organizations/{org['id']}/settings",
            json={"enforce_sso": True},
            headers=_auth_header(token2),
        )
        assert resp.status_code == 403


# ── Organization Dashboard & Analytics Tests ───────────────────────────


class TestOrgDashboard:
    def test_get_dashboard(self, client):
        user, token = _register_user(client)
        org = _create_org(client, _auth_header(token))
        resp = client.get(
            f"/api/organizations/{org['id']}/dashboard",
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        dashboard = resp.json()
        assert "total_scans" in dashboard
        assert "total_projects" in dashboard
        assert "total_members" in dashboard
        assert "severity_distribution" in dashboard

    def test_get_analytics(self, client):
        user, token = _register_user(client)
        org = _create_org(client, _auth_header(token))
        resp = client.get(
            f"/api/organizations/{org['id']}/analytics",
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        analytics = resp.json()
        assert "scan_activity" in analytics
        assert "risk_trend" in analytics
        assert "owasp_distribution" in analytics


# ── Scan Isolation Tests ──────────────────────────────────────────────


class TestScanIsolation:
    def test_upload_scan_with_org(self, client):
        user, token = _register_user(client)
        org = _create_org(client, _auth_header(token))

        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/test": {
                    "get": {
                        "operationId": "test",
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        import io
        import json

        content = json.dumps(spec).encode()
        resp = client.post(
            "/api/scans/upload",
            files={"file": ("test.json", io.BytesIO(content), "application/json")},
            data={"api_name": "Test API", "organization_id": str(org["id"])},
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        scan = resp.json()
        assert scan["organization_id"] == org["id"]

    def test_list_scans_by_org(self, client):
        user, token = _register_user(client)
        org = _create_org(client, _auth_header(token))

        # Upload a scan with org
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {},
        }
        import io, json

        content = json.dumps(spec).encode()
        client.post(
            "/api/scans/upload",
            files={"file": ("test.json", io.BytesIO(content), "application/json")},
            data={"api_name": "Org Scan", "organization_id": str(org["id"])},
            headers=_auth_header(token),
        )

        resp = client.get(
            f"/api/scans/org/{org['id']}",
            headers=_auth_header(token),
        )
        assert resp.status_code == 200

    def test_org_scan_isolation(self, client):
        """Verify user in org1 cannot see org2's scans."""
        user1, token1 = _register_user(client, "org1_user")
        user2, token2 = _register_user(client, "org2_user")
        org1 = _create_org(client, _auth_header(token1), "Org1", "org-1")
        org2 = _create_org(client, _auth_header(token2), "Org2", "org-2")

        # user2 tries to access org1's scans
        resp = client.get(
            f"/api/scans/org/{org1['id']}",
            headers=_auth_header(token2),
        )
        assert resp.status_code == 403


# ── Cross-Org Data Isolation Tests ────────────────────────────────────


class TestCrossOrgIsolation:
    def test_cannot_access_other_org_settings(self, client):
        user1, token1 = _register_user(client, "org1_admin")
        user2, token2 = _register_user(client, "org2_admin")
        org1 = _create_org(client, _auth_header(token1), "Org1", "org-1")
        org2 = _create_org(client, _auth_header(token2), "Org2", "org-2")

        resp = client.get(
            f"/api/organizations/{org1['id']}/settings",
            headers=_auth_header(token2),
        )
        assert resp.status_code == 403

    def test_cannot_access_other_org_teams(self, client):
        user1, token1 = _register_user(client, "org1_admin")
        user2, token2 = _register_user(client, "org2_admin")
        org1 = _create_org(client, _auth_header(token1), "Org1", "org-1")
        org2 = _create_org(client, _auth_header(token2), "Org2", "org-2")

        # user2 tries to list org1's teams
        resp = client.get(
            f"/api/organizations/{org1['id']}/teams",
            headers=_auth_header(token2),
        )
        assert resp.status_code == 403

    def test_cannot_access_other_org_api_keys(self, client):
        user1, token1 = _register_user(client, "org1_admin")
        user2, token2 = _register_user(client, "org2_admin")
        org1 = _create_org(client, _auth_header(token1), "Org1", "org-1")

        resp = client.get(
            f"/api/organizations/{org1['id']}/api-keys",
            headers=_auth_header(token2),
        )
        assert resp.status_code == 403

    def test_cannot_access_other_org_invitations(self, client):
        user1, token1 = _register_user(client, "org1_admin")
        user2, token2 = _register_user(client, "org2_admin")
        org1 = _create_org(client, _auth_header(token1), "Org1", "org-1")

        resp = client.get(
            f"/api/organizations/{org1['id']}/invitations",
            headers=_auth_header(token2),
        )
        assert resp.status_code == 403

    def test_cannot_access_other_org_dashboard(self, client):
        user1, token1 = _register_user(client, "org1_admin")
        user2, token2 = _register_user(client, "org2_admin")
        org1 = _create_org(client, _auth_header(token1), "Org1", "org-1")

        resp = client.get(
            f"/api/organizations/{org1['id']}/dashboard",
            headers=_auth_header(token2),
        )
        assert resp.status_code == 403
