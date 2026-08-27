"""Seed testimonials table with sample data.

Run: python -m scripts.seed_testimonials
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import SessionLocal, init_db
from app.models.models import Testimonial


SAMPLE_TESTIMONIALS = [
    {
        "quote": "SentinelAI caught critical SSRF vulnerabilities that our previous scanner missed entirely. The AI explanations made it easy to prioritize fixes.",
        "author_name": "Sarah Chen",
        "author_role": "Security Lead",
        "author_company": "TechCorp",
        "avatar_letter": "S",
        "display_order": 1,
    },
    {
        "quote": "We integrated SentinelAI into our CI/CD pipeline and reduced our vulnerability remediation time from weeks to hours. The SAST scanner is incredibly accurate.",
        "author_name": "Marcus Rodriguez",
        "author_role": "DevSecOps Engineer",
        "author_company": "ScaleUp",
        "avatar_letter": "M",
        "display_order": 2,
    },
    {
        "quote": "The dependency scanning alone saved us from deploying a package with a known CVE. Real-time threat intelligence that actually works.",
        "author_name": "Aisha Patel",
        "author_role": "Backend Engineer",
        "author_company": "CloudFirst",
        "avatar_letter": "A",
        "display_order": 3,
    },
    {
        "quote": "Finally, a security tool that speaks developer. The AI copilot explains vulnerabilities in context and generates fix suggestions I can actually use.",
        "author_name": "James Wilson",
        "author_role": "Full Stack Developer",
        "author_company": "DevHouse",
        "avatar_letter": "J",
        "display_order": 4,
    },
    {
        "quote": "Our compliance team loves the PDF reports. Professional, detailed, and exactly what auditors need to see. Saved us weeks of manual documentation.",
        "author_name": "Elena Kowalski",
        "author_role": "Compliance Manager",
        "author_company": "FinSecure",
        "avatar_letter": "E",
        "display_order": 5,
    },
]


def seed():
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(Testimonial).count()
        if existing > 0:
            print(f"Testimonials table already has {existing} records. Skipping seed.")
            return

        for data in SAMPLE_TESTIMONIALS:
            testimonial = Testimonial(**data)
            db.add(testimonial)

        db.commit()
        print(f"Seeded {len(SAMPLE_TESTIMONIALS)} testimonials.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
