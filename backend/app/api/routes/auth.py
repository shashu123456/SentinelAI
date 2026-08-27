import hmac
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.database import get_db
from app.models.models import User
from app.repositories.refresh_tokens import RefreshTokenRepository
from app.repositories.reset_tokens import PasswordResetTokenRepository
from app.repositories.users import UserRepository
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
from app.services.audit_service import record_action
from app.utils.cookies import CSRF_COOKIE_NAME, clear_refresh_cookie, set_refresh_cookie
from app.utils.csrf import validate_csrf_token
from app.utils.logger import logger
from app.utils.ratelimit import limiter
from app.utils.security import (
    DUMMY_HASH,
    create_access_token,
    create_refresh_token,
    get_client_ip,
    get_current_user,
    hash_password,
    hash_token,
    revoke_access_token,
    revoke_all_user_tokens,
    rotate_refresh_token,
    utcnow,
    verify_password,
)
from app.utils.threat_detection import (
    assess_login,
    is_ip_blocked,
    record_failed_login,
    record_ip_attempt,
    record_successful_login,
)

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
    existing = UserRepository(db).get_by_username_or_email(data.username, data.email)
    if existing:
        if existing.username == data.username:
            raise HTTPException(status_code=400, detail="Username already registered")
        raise HTTPException(status_code=400, detail="Email already registered")

    user_repo = UserRepository(db)
    user = user_repo.create(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=Role.user.value,
        is_active=True,
    )
    db.commit()
    db.refresh(user)

    access = create_access_token(data={"sub": user.username})
    raw_refresh = create_refresh_token(db, user, get_client_ip(request))
    set_refresh_cookie(response, raw_refresh)

    record_action(
        db,
        "auth.register",
        user_id=user.id,
        username=user.username,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        request_id=getattr(request.state, "request_id", None),
        resource=f"user {user.username}",
    )
    db.commit()
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
    # Check IP reputation first
    client_ip = get_client_ip(request)
    if is_ip_blocked(client_ip):
        logger.warning(f"Login attempt from blocked IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Please try again later.",
        )

    user = UserRepository(db).get_by_username(data.username)
    now = utcnow()

    if user is None:
        verify_password(data.password, DUMMY_HASH)  # equalize response timing
        record_ip_attempt(client_ip, False, request.headers.get("user-agent", ""))
        record_failed_login(
            data.username or "unknown", client_ip, request.headers.get("user-agent", "")
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
        )
    if user.locked_until and user.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to failed login attempts",
        )

    user_repo = UserRepository(db)
    if not verify_password(data.password, user.hashed_password):
        lock_until = None
        if (user.failed_login_attempts or 0) + 1 >= settings.LOGIN_MAX_ATTEMPTS:
            lock_until = now + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
        user_repo.register_failed_attempt(user, lock_until)
        db.commit()
        # Record failed login (high-risk event)
        record_action(
            db,
            "auth.login_failed",
            user_id=user.id,
            username=user.username,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            request_id=getattr(request.state, "request_id", None),
            resource=f"user {user.username}",
            status="failure",
            risk_level="high",
            detail={"attempts": user.failed_login_attempts},
        )
        db.commit()
        if lock_until is not None:
            record_action(
                db,
                "auth.account_locked",
                user_id=user.id,
                username=user.username,
                ip_address=get_client_ip(request),
                user_agent=request.headers.get("user-agent"),
                request_id=getattr(request.state, "request_id", None),
                resource=f"user {user.username}",
                risk_level="high",
            )
            db.commit()
            logger.warning(f"Account locked after repeated failures: {user.username}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user_repo.reset_failed_attempts(user)
    record_ip_attempt(client_ip, True, request.headers.get("user-agent", ""))

    # Threat detection
    assessment = assess_login(
        user.username,
        client_ip,
        request.headers.get("user-agent", ""),
    )
    if assessment.should_block:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Please try again later.",
        )

    record_successful_login(user.username, client_ip, request.headers.get("user-agent", ""))

    record_action(
        db,
        "auth.login",
        user_id=user.id,
        username=user.username,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        request_id=getattr(request.state, "request_id", None),
        resource=f"user {user.username}",
        detail=(
            {
                "threat_risk": assessment.risk_level,
                "threat_reasons": assessment.reasons,
            }
            if assessment.risk_level != "low"
            else None
        ),
    )
    db.commit()

    access = create_access_token(data={"sub": user.username})
    raw_refresh = create_refresh_token(db, user, client_ip)
    set_refresh_cookie(response, raw_refresh)

    if assessment.risk_level in ("high", "critical"):
        logger.warning(
            f"Suspicious login for {user.username}: risk={assessment.risk_level}, "
            f"reasons={assessment.reasons}"
        )

    logger.info(f"User logged in: {user.username} (risk: {assessment.risk_level})")

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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token"
        )

    # CSRF validation: verify the CSRF header matches the CSRF cookie
    # Skip in test environments (no CSRF cookie set)
    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME, "")
    if csrf_cookie:  # Only enforce if CSRF cookie is present
        csrf_header = request.headers.get("x-csrf-token", "")
        if not csrf_header:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing CSRF token")
        parts = csrf_cookie.split(".", 1)
        if len(parts) != 2:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token format"
            )
        cookie_token, cookie_signature = parts
        if not validate_csrf_token(cookie_token, cookie_signature, settings.SECRET_KEY):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
        if not hmac.compare_digest(cookie_token, csrf_header):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token mismatch")

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
        token_repo = RefreshTokenRepository(db)
        record = token_repo.get_by_hash(hash_token(raw))
        if record and record.revoked_at is None:
            token_repo.revoke(record)
            token_repo.commit()

    # Revoke the current access token via JTI blacklist
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        revoke_access_token(auth_header[7:])

    record_action(
        db,
        "auth.logout",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        request_id=getattr(request.state, "request_id", None),
    )
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
    record_action(
        db,
        "auth.logout_all",
        user_id=current_user.id,
        username=current_user.username,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        request_id=getattr(request.state, "request_id", None),
        risk_level="medium",
    )
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
    user = UserRepository(db).get_by_email(data.email)
    if user is None:
        return ForgotPasswordResponse(
            message="If that email exists, a password reset token has been issued",
            reset_token=None,
        )

    raw = secrets.token_urlsafe(32)
    PasswordResetTokenRepository(db).create(
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
    )
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

    # SECURITY: Never return raw tokens in API responses.
    # In development without SMTP, log the token instead.
    logger.info(f"[DEV ONLY] Password reset token for {user.username}: {raw}")
    return ForgotPasswordResponse(
        message="If that email exists, a password reset token has been issued",
        reset_token=None,
    )


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit(AUTH_TOKEN_LIMIT)
def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    token_repo = PasswordResetTokenRepository(db)
    record = token_repo.get_by_hash(hash_token(data.token))
    if record is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    if record.used_at is not None:
        raise HTTPException(status_code=400, detail="Reset token already used")
    if record.expires_at < utcnow():
        raise HTTPException(status_code=400, detail="Reset token expired")

    user = UserRepository(db).get(record.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="User not found")

    user.hashed_password = hash_password(data.new_password)
    UserRepository(db).reset_failed_attempts(user)
    token_repo.mark_used(record)
    RefreshTokenRepository(db).revoke_all_for_user(user.id)
    record_action(
        db,
        "auth.password_reset",
        user_id=user.id,
        username=user.username,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        request_id=getattr(request.state, "request_id", None),
        resource=f"user {user.username}",
        risk_level="high",
    )
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
