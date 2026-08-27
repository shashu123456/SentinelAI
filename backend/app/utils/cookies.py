from fastapi import Response

from app.config import get_settings
from app.utils.csrf import generate_csrf_token, hash_csrf_token

settings = get_settings()

REFRESH_COOKIE_PATH = "/api/auth"
CSRF_COOKIE_NAME = "sentinelai_csrf"


def set_refresh_cookie(response: Response, raw_token: str) -> None:
    """Set refresh token cookie paired with a CSRF token.

    The refresh token cookie is HttpOnly (not readable by JS).
    The CSRF token cookie is NOT HttpOnly (readable by JS) and is sent
    as a header on refresh requests to prevent CSRF attacks.
    """
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=raw_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=settings.REFRESH_TOKEN_COOKIE_HTTPONLY,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
        path=REFRESH_COOKIE_PATH,
    )

    # CSRF token: NOT HttpOnly so frontend JS can read it and send as header
    csrf_token = generate_csrf_token()
    csrf_signature = hash_csrf_token(csrf_token, settings.SECRET_KEY)
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=f"{csrf_token}.{csrf_signature}",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=False,  # Frontend needs to read this
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite="strict",  # CSRF cookie must be Strict
        path=REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(settings.REFRESH_TOKEN_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
    response.delete_cookie(CSRF_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
