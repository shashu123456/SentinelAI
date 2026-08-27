"""Tests for the public testimonials endpoint."""

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
def seed_testimonials():
    """Seed test testimonials into the database."""
    from app.database.database import SessionLocal
    from app.models.models import Testimonial

    db = SessionLocal()
    try:
        # Check if testimonials exist
        existing = db.query(Testimonial).count()
        if existing == 0:
            db.add(
                Testimonial(
                    quote="Test quote for unit testing",
                    author_name="Test Author",
                    author_role="Tester",
                    author_company="TestCo",
                    avatar_letter="T",
                    is_active=True,
                    display_order=1,
                )
            )
            db.add(
                Testimonial(
                    quote="Inactive testimonial",
                    author_name="Inactive Author",
                    author_role="Inactive",
                    author_company="InactiveCo",
                    avatar_letter="I",
                    is_active=False,
                    display_order=2,
                )
            )
            db.commit()
    finally:
        db.close()


class TestTestimonialsEndpoint:
    def test_list_testimonials_returns_list(self, client, seed_testimonials):
        response = client.get("/api/testimonials")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_testimonials_only_active(self, client, seed_testimonials):
        response = client.get("/api/testimonials")
        data = response.json()
        # Should only return active testimonials
        for t in data:
            assert "author_name" in t
            assert "quote" in t
            assert "avatar_letter" in t

    def test_list_testimonials_no_auth_required(self, client, seed_testimonials):
        # This endpoint should work without authentication
        response = client.get("/api/testimonials")
        assert response.status_code == 200

    def test_list_testimonials_returns_correct_fields(self, client, seed_testimonials):
        response = client.get("/api/testimonials")
        data = response.json()
        if len(data) > 0:
            testimonial = data[0]
            assert "id" in testimonial
            assert "quote" in testimonial
            assert "author_name" in testimonial
            assert "author_role" in testimonial
            assert "author_company" in testimonial
            assert "avatar_letter" in testimonial
