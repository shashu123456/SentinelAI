"""User onboarding wizard management."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.saas import OnboardingProgress
from app.utils.logger import logger

ONBOARDING_STEPS = [
    "welcome",
    "profile",
    "first_project",
    "first_scan",
    "invite_team",
    "completed",
]


def get_onboarding_progress(db: Session, user_id: int) -> OnboardingProgress:
    """Get or create onboarding progress for a user."""
    progress = db.query(OnboardingProgress).filter(OnboardingProgress.user_id == user_id).first()
    if not progress:
        progress = OnboardingProgress(user_id=user_id, completed_steps=[], current_step="welcome")
        db.add(progress)
        db.commit()
        db.refresh(progress)
    return progress


def complete_onboarding_step(
    db: Session,
    *,
    user_id: int,
    step: str,
    role: str | None = None,
    use_case: str | None = None,
) -> OnboardingProgress:
    """Mark an onboarding step as complete."""
    progress = get_onboarding_progress(db, user_id)

    if step not in ONBOARDING_STEPS:
        raise ValueError(f"Invalid onboarding step: {step}")

    if step not in progress.completed_steps:
        progress.completed_steps = progress.completed_steps + [step]

    current_idx = ONBOARDING_STEPS.index(step)
    if current_idx + 1 < len(ONBOARDING_STEPS):
        progress.current_step = ONBOARDING_STEPS[current_idx + 1]
    else:
        progress.current_step = "completed"
        progress.is_complete = True

    if role:
        progress.role = role
    if use_case:
        progress.use_case = use_case

    progress.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(progress)
    logger.info("Onboarding step completed: user=%s step=%s", user_id, step)
    return progress
