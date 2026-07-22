import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


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
