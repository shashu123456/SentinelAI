from datetime import timedelta
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.database import get_db
from app.models.models import User, PasswordResetToken
from app.schemas.schemas import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    MessageResponse,
    ResetPasswordRequest,
    Role,
    Token,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.utils.cookies import clear_refresh_cookie, set_refresh_cookie
from app.utils.ratelimit import limiter
from app.utils.security import (
    DUMMY_HASH,
    create_access_token,
    create_refresh_token,
    get_client_ip,
    get_current_user,
    get_refresh_token,
    hash_password,
    hash_token,
    revoke_all_user_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
    utcnow,
    verify_password,
)
from app.utils.logger import logger

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
settings = get_settings()

REGISTER_LIMIT = f"{settings.REGISTER_RATE_LIMIT_PER_MINUTE}/minute"
LOGIN_LIMIT = f"{settings.LOGIN_RATE_LIMIT_PER_MINUTE}/minute"
AUTH_TOKEN_LIMIT = f"{settings.AUTH_TOKEN_RATE_LIMIT_PER_MINUTE}/minute"


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit(REGISTER_LIMIT)
def register(
    request: Request,
    response: Response,
    data: UserRegister,
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(
        (User.username == data.username) | (User.email == data.email)
    ).first()
    if existing:
        if existing.username == data.username:
            raise HTTPException(status_code=400, detail="Username already registered")
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=Role.user.value,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access = create_access_token(data={"sub": user.username})
    raw_refresh = create_refresh_token(db, user, get_client_ip(request))
    set_refresh_cookie(response, raw_refresh)

    logger.info(f"New user registered: {user.username}")

    return Token(
        access_token=access,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=Token)
@limiter.limit(LOGIN_LIMIT)
def login(
    request: Request,
    response: Response,
    data: UserLogin,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == data.username).first()
    now = utcnow()

    if user is None:
        verify_password(data.password, DUMMY_HASH)  # equalize response timing
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")
    if user.locked_until and user.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to failed login attempts",
        )

    if not verify_password(data.password, user.hashed_password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= settings.LOGIN_MAX_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
            logger.warning(f"Account locked after repeated failures: {user.username}")
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    access = create_access_token(data={"sub": user.username})
    raw_refresh = create_refresh_token(db, user, get_client_ip(request))
    set_refresh_cookie(response, raw_refresh)

    logger.info(f"User logged in: {user.username}")

    return Token(
        access_token=access,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.post("/refresh", response_model=Token)
@limiter.limit(AUTH_TOKEN_LIMIT)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    raw = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    new_raw, user = rotate_refresh_token(db, raw, get_client_ip(request))
    set_refresh_cookie(response, new_raw)

    access = create_access_token(data={"sub": user.username})
    return Token(
        access_token=access,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    raw = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    if raw:
        record = get_refresh_token(db, raw)
        if record and record.revoked_at is None:
            revoke_refresh_token(db, record)
    clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/logout-all")
def logout_all(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    revoke_all_user_tokens(db, current_user.id)
    clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    logger.info(f"All sessions revoked for user: {current_user.username}")
    return response


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
@limiter.limit(AUTH_TOKEN_LIMIT)
def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == data.email).first()
    if user is None:
        return ForgotPasswordResponse(
            message="If that email exists, a password reset token has been issued",
            reset_token=None,
        )

    raw = secrets.token_urlsafe(32)
    record = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
    )
    db.add(record)
    db.commit()
    logger.info(f"Password reset requested for: {user.username}")

    if settings.SMTP_HOST:
        try:
            _send_reset_email(user.email, raw)
            return ForgotPasswordResponse(
                message="If that email exists, a password reset token has been issued",
                reset_token=None,
            )
        except Exception as exc:  # pragma: no cover - SMTP path not exercised in tests
            logger.error(f"Failed to send reset email: {exc}")

    return ForgotPasswordResponse(
        message="Password reset token generated (SMTP not configured)",
        reset_token=raw,
    )


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit(AUTH_TOKEN_LIMIT)
def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == hash_token(data.token)
    ).first()
    if record is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    if record.used_at is not None:
        raise HTTPException(status_code=400, detail="Reset token already used")
    if record.expires_at < utcnow():
        raise HTTPException(status_code=400, detail="Reset token expired")

    user = db.query(User).filter(User.id == record.user_id).first()
    if user is None:
        raise HTTPException(status_code=400, detail="User not found")

    user.hashed_password = hash_password(data.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    record.used_at = utcnow()
    revoke_all_user_tokens(db, user.id)
    db.commit()

    logger.info(f"Password reset completed for: {user.username}")
    return MessageResponse(detail="Password reset successful")


def _send_reset_email(recipient: str, token: str) -> None:  # pragma: no cover - needs real SMTP
    import smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["Subject"] = "SentinelAI password reset"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = recipient
    msg.set_content(
        f"Use this token to reset your password (valid for "
        f"{settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes):\n\n{token}"
    )
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(msg)
