"""Public testimonials endpoint.

Returns active testimonials sorted by display_order.
No authentication required — this is public marketing content.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import Testimonial
from app.utils.ratelimit import limiter

router = APIRouter(tags=["Public"])


class TestimonialResponse(BaseModel):
    id: int
    quote: str
    author_name: str
    author_role: str
    author_company: str
    avatar_letter: str

    class Config:
        from_attributes = True


@router.get("/api/testimonials", response_model=list[TestimonialResponse])
@limiter.exempt
def list_testimonials(db: Session = Depends(get_db)):
    """Get all active testimonials for the landing page."""
    testimonials = (
        db.query(Testimonial)
        .filter(Testimonial.is_active == True)
        .order_by(Testimonial.display_order, Testimonial.id)
        .all()
    )
    return [
        TestimonialResponse(
            id=t.id,
            quote=t.quote,
            author_name=t.author_name,
            author_role=t.author_role,
            author_company=t.author_company,
            avatar_letter=t.avatar_letter,
        )
        for t in testimonials
    ]
