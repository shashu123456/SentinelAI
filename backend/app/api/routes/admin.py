from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.database import get_db
from app.models.models import RefreshToken, User
from app.schemas.schemas import (
    MessageResponse,
    Role,
    RoleUpdateRequest,
    SessionInfo,
    UserResponse,
)
from app.utils.logger import logger
from app.utils.security import require_roles

router = APIRouter(prefix="/api/auth/users", tags=["Admin"])
settings = get_settings()

admin_required = require_roles(Role.admin)


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    return db.query(User).order_by(User.id).all()


@router.patch("/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    data: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Admins cannot change their own role")

    user.role = data.role.value
    db.commit()
    db.refresh(user)
    logger.info(f"Admin {current_user.username} changed role of {user.username} to {data.role.value}")
    return user


@router.post("/{user_id}/lock", response_model=MessageResponse)
def lock_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Admins cannot lock their own account")

    user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
    db.commit()
    logger.info(f"Admin {current_user.username} locked account of {user.username}")
    return MessageResponse(detail="User locked")


@router.post("/{user_id}/unlock", response_model=MessageResponse)
def unlock_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.locked_until = None
    user.failed_login_attempts = 0
    db.commit()
    logger.info(f"Admin {current_user.username} unlocked account of {user.username}")
    return MessageResponse(detail="User unlocked")


@router.get("/{user_id}/sessions", response_model=list[SessionInfo])
def list_user_sessions(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id)
        .order_by(RefreshToken.created_at.desc())
        .all()
    )
