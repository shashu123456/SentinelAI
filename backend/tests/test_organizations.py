"""Tests for organization and project management endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.database.database import Base, engine
    from app.main import app

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    return TestClient(app)


@pytest.fixture
def test_user():
    return {"username": "orguser", "password": "Test123!@#"}


@pytest.fixture
def auth_headers(client, test_user):
    """Register test user and get auth headers."""
    response = client.post(
        "/api/auth/register",
        json={
            "username": test_user["username"],
            "email": f"{test_user['username']}@test.com",
            "password": test_user["password"],
        },
    )
    assert response.status_code in (201, 200), response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestOrganizationCRUD:
    def test_create_organization(self, client, auth_headers):
        response = client.post(
            "/api/organizations",
            json={"name": "Test Org", "slug": "test-org"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Org"
        assert data["slug"] == "test-org"

    def test_create_organization_duplicate_slug(self, client, auth_headers):
        client.post(
            "/api/organizations",
            json={"name": "Org 1", "slug": "dup-org"},
            headers=auth_headers,
        )
        response = client.post(
            "/api/organizations",
            json={"name": "Org 2", "slug": "dup-org"},
            headers=auth_headers,
        )
        assert response.status_code == 409

    def test_list_organizations(self, client, auth_headers):
        client.post(
            "/api/organizations",
            json={"name": "List Org", "slug": "list-org"},
            headers=auth_headers,
        )
        response = client.get("/api/organizations", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) >= 1

    def test_get_organization(self, client, auth_headers):
        create_resp = client.post(
            "/api/organizations",
            json={"name": "Get Org", "slug": "get-org"},
            headers=auth_headers,
        )
        org_id = create_resp.json()["id"]
        response = client.get(f"/api/organizations/{org_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Get Org"

    def test_create_organization_requires_auth(self, client):
        response = client.post(
            "/api/organizations",
            json={"name": "No Auth", "slug": "no-auth"},
        )
        assert response.status_code == 401


class TestOrganizationMembers:
    def _create_org(self, client, auth_headers):
        resp = client.post(
            "/api/organizations",
            json={"name": "Member Org", "slug": "member-org"},
            headers=auth_headers,
        )
        return resp.json()["id"]

    def test_add_member(self, client, auth_headers):
        org_id = self._create_org(client, auth_headers)
        # Create a second user to add as member
        resp = client.post(
            "/api/auth/register",
            json={"username": "memberuser", "email": "member@test.com", "password": "Test123!@#"},
        )
        member_email = resp.json()["user"]["email"]
        response = client.post(
            f"/api/organizations/{org_id}/members",
            json={"email": member_email, "role": "developer"},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_add_duplicate_member(self, client, auth_headers):
        org_id = self._create_org(client, auth_headers)
        resp = client.post(
            "/api/auth/register",
            json={"username": "dupmember", "email": "dup@test.com", "password": "Test123!@#"},
        )
        member_email = resp.json()["user"]["email"]
        client.post(
            f"/api/organizations/{org_id}/members",
            json={"email": member_email, "role": "developer"},
            headers=auth_headers,
        )
        response = client.post(
            f"/api/organizations/{org_id}/members",
            json={"email": member_email, "role": "developer"},
            headers=auth_headers,
        )
        assert response.status_code == 409


class TestProjects:
    def _create_org(self, client, auth_headers):
        resp = client.post(
            "/api/organizations",
            json={"name": "Project Org", "slug": "project-org"},
            headers=auth_headers,
        )
        return resp.json()["id"]

    def test_create_project(self, client, auth_headers):
        org_id = self._create_org(client, auth_headers)
        response = client.post(
            f"/api/organizations/{org_id}/projects",
            json={"name": "Test Project", "slug": "test-project"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Test Project"

    def test_list_projects(self, client, auth_headers):
        org_id = self._create_org(client, auth_headers)
        client.post(
            f"/api/organizations/{org_id}/projects",
            json={"name": "List Project", "slug": "list-project"},
            headers=auth_headers,
        )
        response = client.get(f"/api/organizations/{org_id}/projects", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) >= 1

    def test_create_project_requires_membership(self, client, auth_headers):
        org_id = self._create_org(client, auth_headers)
        # Create a second user
        client.post(
            "/api/auth/register",
            json={"username": "outsider", "email": "out@test.com", "password": "testpass123"},
        )
        login_resp = client.post(
            "/api/auth/login",
            json={"username": "outsider", "password": "testpass123"},
        )
        outsider_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
        response = client.post(
            f"/api/organizations/{org_id}/projects",
            json={"name": "Unauthorized", "slug": "unauth-project"},
            headers=outsider_headers,
        )
        assert response.status_code == 403
