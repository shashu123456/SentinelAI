from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.database import get_db
from app.models.models import User
from app.repositories.refresh_tokens import RefreshTokenRepository
from app.repositories.users import UserRepository
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
    return UserRepository(db).list(order_by=User.id)


@router.patch("/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    data: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    user = UserRepository(db).get_or_404(user_id, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Admins cannot change their own role")

    user.role = data.role.value
    db.commit()
    db.refresh(user)
    logger.info(
        f"Admin {current_user.username} changed role of {user.username} to {data.role.value}"
    )
    return user


@router.post("/{user_id}/lock", response_model=MessageResponse)
def lock_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    user_repo = UserRepository(db)
    user = user_repo.get_or_404(user_id, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Admins cannot lock their own account")

    user_repo.lock(user, datetime.now(UTC) + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES))
    db.commit()
    logger.info(f"Admin {current_user.username} locked account of {user.username}")
    return MessageResponse(detail="User locked")


@router.post("/{user_id}/unlock", response_model=MessageResponse)
def unlock_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    user_repo = UserRepository(db)
    user = user_repo.get_or_404(user_id, detail="User not found")

    user_repo.unlock(user)
    db.commit()
    logger.info(f"Admin {current_user.username} unlocked account of {user.username}")
    return MessageResponse(detail="User unlocked")


@router.get("/{user_id}/sessions", response_model=list[SessionInfo])
def list_user_sessions(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    UserRepository(db).get_or_404(user_id, detail="User not found")

    return RefreshTokenRepository(db).list_for_user(user_id)
