import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(
    tempfile.gettempdir(), f"sentinelai_test_{os.getpid()}.db"
).replace("\\", "/")

# Deterministic test configuration. The per-minute login limit is kept at the
# per-IP failed-login threshold (10) so the rate limiter is the first gate that
# trips; with the production default of 30 the IP reputation block would answer
# 429 first.
# Defence in depth: point Redis at a closed local port so the connect is
# refused instantly. app.utils.token_blacklist now initialises lazily (no
# network I/O at import), so the code no longer *requires* this; it stays so a
# developer with a real redis://localhost:6379 running still gets the in-memory
# backend and deterministic tests.
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"

# Dependency scans merge live OSV.dev data in production. The suite is offline by
# design (no network, deterministic findings), so the live lookup is off here and
# the OSV client is tested against a stubbed HTTP layer instead.
os.environ["OSV_ENABLED"] = "false"

os.environ["LOGIN_RATE_LIMIT_PER_MINUTE"] = "10"


@pytest.fixture()
def client():
    """Fresh API client against an isolated test database (schema rebuilt per test).

    Two deliberate changes for speed, both measured:

    1. The schema is rebuilt with ``Base.metadata.create_all`` directly.
    2. ``TestClient`` is NOT used as a context manager, so the app lifespan does
       not run. Lifespan calls ``init_db()`` -> Alembic on *every* fixture setup,
       which cost ~35-40s for the first test in a process and ~3s for each one
       after; across the suite that made a single run impossible.

    Per-test isolation is unchanged: the schema is dropped and recreated for
    every test exactly as before.
    """
    import app.models.enterprise  # noqa: F401 - register enterprise tables
    import app.models.models  # noqa: F401 - register core tables
    import app.models.plugins  # noqa: F401 - register plugin tables
    import app.models.saas  # noqa: F401 - register SaaS tables
    from app.database.database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    from fastapi.testclient import TestClient

    from app.main import app

    c = TestClient(app)
    try:
        yield c
    finally:
        c.close()


@pytest.fixture()
def async_client():
    """Client that keeps the ASGI lifespan -- and therefore the event loop -- alive.

    ``POST /api/scans/upload/async`` schedules its work with
    ``asyncio.create_task`` on the *request's* loop, so the loop must outlive the
    request. Under uvicorn it does; with the fast ``client`` fixture (no context
    manager) it does not, and the task is cancelled. Use this fixture only for
    tests that exercise asynchronous scheduling.

    Cost: entering the context runs the lifespan (``init_db()``), a few seconds
    per test, which is why the default ``client`` fixture does not.
    """
    import app.models.enterprise  # noqa: F401 - register enterprise tables
    import app.models.models  # noqa: F401 - register core tables
    import app.models.plugins  # noqa: F401 - register plugin tables
    import app.models.saas  # noqa: F401 - register SaaS tables
    from app.database.database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db_session():
    """Direct SQLAlchemy session against the isolated test database.

    Drops and recreates all tables so each test starts from a clean schema.
    """
    import app.models.enterprise  # noqa: F401 - register enterprise tables
    import app.models.models  # noqa: F401 - register tables on Base.metadata
    import app.models.plugins  # noqa: F401 - register plugin tables
    import app.models.saas  # noqa: F401 - register SaaS tables
    from app.database.database import Base, SessionLocal, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def user(db_session):
    """A persisted regular user created through the repository layer."""
    from app.repositories.users import UserRepository
    from app.utils.security import hash_password

    repo = UserRepository(db_session)
    u = repo.create(
        username="repo_user",
        email="repo_user@example.com",
        hashed_password=hash_password("testpass123"),
    )
    db_session.commit()
    return u


@pytest.fixture()
def scan(db_session, user):
    """A persisted scan owned by `user`."""
    from app.repositories.scans import ScanRepository

    repo = ScanRepository(db_session)
    s = repo.create_scan(
        user_id=user.id,
        api_name="Petstore",
        source_spec={"openapi": "3.0.0", "info": {"title": "Petstore"}},
    )
    db_session.commit()
    return s


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Reset slowapi's in-memory counters and the threat-detection stores so
    rate-limit tests never bleed into other tests (all TestClient requests share
    the same source IP)."""
    from app.utils import threat_detection
    from app.utils.ratelimit import limiter

    threat_detection.reset_state()
    yield
    limiter.reset()
    threat_detection.reset_state()


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
def registered_user(client):
    """Register a fresh user through the API and return its session details.

    See ``tests/helpers`` for the underlying builder and other utilities.
    """
    from tests.helpers import register

    return register(client, prefix="fixture")


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
                        {
                            "name": "petId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
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
                        {
                            "name": "petId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                },
                "delete": {
                    "operationId": "deletePet",
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
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
                        {
                            "name": "userId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {"name": "limit", "in": "query", "schema": {"type": "integer"}},
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }
