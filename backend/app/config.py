from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    PROJECT_NAME: str = "SentinelAI"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "AI-Powered API & LLM Security Scanner"

    DATABASE_URL: str = "sqlite:///./sentinelai.db"

    SECRET_KEY: str = "sentinelai-dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- Refresh token / session cookies ---
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_TOKEN_COOKIE_NAME: str = "sentinelai_refresh"
    REFRESH_TOKEN_COOKIE_SECURE: bool = False  # set True in production (HTTPS)
    REFRESH_TOKEN_COOKIE_HTTPONLY: bool = True
    REFRESH_TOKEN_COOKIE_SAMESITE: str = "lax"

    # --- Password policy ---
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPER: bool = False
    PASSWORD_REQUIRE_NUMBER: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = False

    # --- Account lockout ---
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # --- Password reset / email ---
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_USE_TLS: bool = True

    # --- Rate limits ---
    LOGIN_RATE_LIMIT_PER_MINUTE: int = 30
    REGISTER_RATE_LIMIT_PER_MINUTE: int = 30
    AUTH_TOKEN_RATE_LIMIT_PER_MINUTE: int = 60
    COPILOT_RATE_LIMIT_PER_MINUTE: int = 20

    # --- Security headers ---
    ENABLE_SECURITY_HEADERS: bool = True
    HSTS_MAX_AGE: int = 31536000

    OLLAMA_URL: str = "http://localhost:11434/api/generate"
    OLLAMA_MODEL: str = "mistral"

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"]
    CORS_ALLOW_ALL: bool = False

    MAX_UPLOAD_SIZE_MB: int = 5
    RATE_LIMIT_PER_MINUTE: int = 30

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
