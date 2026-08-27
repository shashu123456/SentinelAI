from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "SentinelAI"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "AI-Powered API & LLM Security Scanner"

    DATABASE_URL: str = "sqlite:///./sentinelai.db"

    SECRET_KEY: str = "sentinelai-dev-secret-key-change-in-production"

    # --- Security hardening ---
    MAX_LOGIN_ATTEMPTS_PER_IP_PER_HOUR: int = 20
    SUSPICIOUS_LOGIN_THRESHOLD: int = 5
    SESSION_TIMEOUT_MINUTES: int = 30
    ALLOWED_UPLOAD_EXTENSIONS: list[str] = [".json", ".yaml", ".yml"]
    MAX_FILE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5MB
    BLOCKED_IPS: list[str] = []
    TRUSTED_PROXIES: list[str] = []
    CSRF_ENFORCE: bool = True
    REFRESH_TOKEN_COOKIE_SECURE: bool = False  # set True in production (HTTPS)

    def validate_secret_key(self) -> bool:
        """Check that SECRET_KEY has been changed from the default."""
        return self.SECRET_KEY != "sentinelai-dev-secret-key-change-in-production"

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- Refresh token / session cookies ---
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_TOKEN_COOKIE_NAME: str = "sentinelai_refresh"
    REFRESH_TOKEN_COOKIE_SECURE: bool = False  # set True in production (HTTPS)
    REFRESH_TOKEN_COOKIE_HTTPONLY: bool = True
    REFRESH_TOKEN_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

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

    # --- Redis ---
    REDIS_URL: str = ""  # e.g. redis://localhost:6379/0

    # --- Caching ---
    DASHBOARD_CACHE_TTL: int = 60  # seconds
    ANALYTICS_CACHE_TTL: int = 30  # seconds
    HEALTH_CACHE_TTL: int = 15  # seconds

    OLLAMA_URL: str = "http://localhost:11434/api/generate"
    OLLAMA_MODEL: str = "mistral"

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
    ]
    CORS_ALLOW_ALL: bool = False

    MAX_UPLOAD_SIZE_MB: int = 5
    RATE_LIMIT_PER_MINUTE: int = 30

    # --- Error Tracking (Sentry) ---
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    SENTINEL_ENV: str = "development"
    SENTINEL_VERSION: str = "1.0.0"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
