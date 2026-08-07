import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["DATABASE_URL"] = (
    "sqlite:///" + os.path.join(tempfile.gettempdir(), f"sentinelai_test_{os.getpid()}.db").replace("\\", "/")
)


@pytest.fixture()
def client():
    """Fresh API client against an isolated test database (dropped per test)."""
    from app.database.database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def user_token(client):
    """Register a fresh user and return (username, access_token)."""
    import uuid

    username = f"user_{uuid.uuid4().hex[:8]}"
    resp = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpass123",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return username, data["access_token"]


@pytest.fixture()
def auth_headers(user_token):
    """Authorization headers for an authenticated user."""
    _, token = user_token
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def wait_for_task(client):
    """Poll an async scan task until it reaches a terminal state."""

    def _wait(task_id: str, timeout: float = 20.0, headers: dict | None = None) -> dict:
        import time

        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = client.get(f"/api/scans/task/{task_id}", headers=headers or {})
            assert resp.status_code == 200, resp.text
            data = resp.json()
            if data["status"] in ("completed", "failed"):
                return data
            time.sleep(0.25)
        raise AssertionError(f"Task {task_id} did not finish within {timeout}s")

    return _wait


def _petstore_spec() -> dict:
    """A deliberately vulnerable OpenAPI spec for scan tests."""
    return {
        "openapi": "3.0.3",
        "info": {"title": "Petstore", "version": "1.0.0"},
        "paths": {
            "/pets": {
                "get": {
                    "operationId": "listPets",
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "operationId": "createPet",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "password": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {"201": {"description": "Created"}},
                },
            },
            "/pets/{petId}": {
                "get": {
                    "operationId": "getPet",
                    "parameters": [
                        {"name": "petId", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/admin/users": {
                "get": {
                    "operationId": "adminList",
                    "responses": {"200": {"description": "OK"}},
                }
            },
        },
    }


@pytest.fixture()
def petstore_spec():
    return _petstore_spec()


@pytest.fixture
def sample_petstore_spec():
    return {
        "openapi": "3.0.3",
        "info": {"title": "Petstore", "version": "1.0.0"},
        "paths": {
            "/pets": {
                "get": {
                    "operationId": "listPets",
                    "summary": "List pets",
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "operationId": "createPet",
                    "summary": "Create pet",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "password": {"type": "string"},
                                        "admin_role": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {"201": {"description": "Created"}},
                },
            },
            "/pets/{petId}": {
                "get": {
                    "operationId": "getPet",
                    "parameters": [
                        {"name": "petId", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "OK"}},
                },
                "delete": {
                    "operationId": "deletePet",
                    "parameters": [
                        {"name": "petId", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {"204": {"description": "Deleted"}},
                },
            },
            "/admin/users": {
                "get": {
                    "operationId": "adminList",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/users": {
                "post": {
                    "operationId": "createUser",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "username": {"type": "string"},
                                        "password": {"type": "string"},
                                        "email": {"type": "string"},
                                        "api_key": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {"201": {"description": "Created"}},
                }
            },
            "/store/orders": {
                "post": {
                    "operationId": "placeOrder",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "petId": {"type": "string"},
                                        "webhook_url": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {"201": {"description": "Created"}},
                }
            },
        },
    }


@pytest.fixture
def minimal_spec():
    return {
        "openapi": "3.0.0",
        "info": {"title": "Minimal API", "version": "1.0.0"},
        "paths": {},
    }


@pytest.fixture
def secure_spec():
    return {
        "openapi": "3.0.0",
        "info": {"title": "Secure API", "version": "1.0.0"},
        "security": [{"bearerAuth": []}],
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
            }
        },
        "paths": {
            "/users": {
                "get": {
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {"name": "userId", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "limit", "in": "query", "schema": {"type": "integer"}},
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }
