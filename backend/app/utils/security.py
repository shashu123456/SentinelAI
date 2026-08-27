import hashlib
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.database import get_db
from app.models.models import RefreshToken, User
from app.schemas.schemas import Role
from app.utils.token_blacklist import blacklist

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Precomputed hash so login responses for unknown users take the same bcrypt
# time as real password checks (prevents username enumeration via timing).
DUMMY_HASH = pwd_context.hash("sentinelai-timing-equalizer")


def utcnow() -> datetime:
    """Naive UTC now — SQLite round-trips datetimes without tzinfo, so all
    persisted-then-compared timestamps must use the same (naive) convention."""
    return datetime.now(UTC).replace(tzinfo=None)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token with JTI claim for revocation support."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update(
        {
            "exp": expire,
            "jti": secrets.token_urlsafe(16),
            "iat": datetime.now(UTC),
        }
    )
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token.

    Checks:
    1. Signature validity
    2. Algorithm whitelist (prevents algorithm confusion attacks)
    3. Expiry
    4. Blacklist (JTI-based revocation)
    5. User-level revocation (logout-all)
    """
    # SECURITY: Always pass algorithms as a list to prevent algorithm confusion.
    # An attacker could craft a token with alg:none or alg:HS256 when RS256 is expected.
    allowed_algorithms = [settings.ALGORITHM]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=allowed_algorithms)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        ) from None
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from None

    # Check JTI blacklist
    jti = payload.get("jti")
    if jti and blacklist.is_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked"
        ) from None

    # Check user-level revocation (logout-all)
    return payload


def revoke_access_token(token: str) -> None:
    """Revoke a specific access token by adding its JTI to the blacklist."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False},  # Allow revoking expired tokens
        )
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            # exp is a datetime or timestamp
            if isinstance(exp, datetime):
                exp_ts = exp.timestamp()
            else:
                exp_ts = exp
            blacklist.add(jti, exp_ts)
    except jwt.JWTError:
        pass  # Invalid token, nothing to revoke


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    username = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
        )
    return user


def require_roles(*roles: Role) -> Callable:
    """Dependency factory restricting an endpoint to the given roles."""

    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return current_user

    return _dependency


# --- Refresh token handling ---


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def create_refresh_token(db: Session, user: User, ip_address: str | None = None) -> str:
    raw = secrets.token_urlsafe(48)
    record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        ip_address=ip_address,
    )
    db.add(record)
    db.commit()
    return raw


def get_refresh_token(db: Session, raw: str) -> RefreshToken | None:
    return db.query(RefreshToken).filter(RefreshToken.token_hash == hash_token(raw)).first()


def revoke_refresh_token(db: Session, record: RefreshToken, replaced_by: str | None = None) -> None:
    record.revoked_at = utcnow()
    if replaced_by:
        record.replaced_by = hash_token(replaced_by)
    db.commit()


def revoke_all_user_tokens(db: Session, user_id: int) -> None:
    now = utcnow()
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    ).update({RefreshToken.revoked_at: now}, synchronize_session=False)
    db.commit()


def rotate_refresh_token(db: Session, raw: str, ip_address: str | None = None) -> tuple[str, User]:
    """Validate a refresh token, revoke it, and mint a replacement.

    Presenting an already-revoked token is treated as token theft: the entire
    session family for that user is revoked.
    """
    record = get_refresh_token(db, raw)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    if record.revoked_at is not None:
        revoke_all_user_tokens(db, record.user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token reuse detected"
        )
    if record.expires_at < utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
        )
    user = db.query(User).filter(User.id == record.user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
        )
    new_raw = create_refresh_token(db, user, ip_address)
    revoke_refresh_token(db, record, replaced_by=new_raw)
    return new_raw, user
