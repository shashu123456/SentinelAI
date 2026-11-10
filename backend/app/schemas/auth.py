"""Authentication and user schemas."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.config import get_settings

_settings = get_settings()


class Role(StrEnum):
    user = "user"
    analyst = "analyst"
    viewer = "viewer"
    admin = "admin"


def validate_password_strength(password: str) -> str:
    """Validate password meets minimum requirements."""
    if len(password) < _settings.PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {_settings.PASSWORD_MIN_LENGTH} characters"
        )
    if _settings.PASSWORD_REQUIRE_UPPER and not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")
    if _settings.PASSWORD_REQUIRE_NUMBER and not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one number")
    if _settings.PASSWORD_REQUIRE_SPECIAL and not any(
        c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password
    ):
        raise ValueError("Password must contain at least one special character")
    return password


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        return validate_password_strength(v)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        return validate_password_strength(v)


class MessageResponse(BaseModel):
    detail: str


class RoleUpdateRequest(BaseModel):
    role: Role


class SessionInfo(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    ip_address: str | None
    created_at: datetime
    expires_at: datetime
    is_current: bool = False
