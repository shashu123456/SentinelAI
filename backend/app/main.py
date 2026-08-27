import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.errors import register_exception_handlers
from app.api.middleware import envelope_middleware
from app.api.routes import (
    admin,
    api_keys,
    audit,
    auth,
    enterprise,
    invitations,
    metrics,
    organizations,
    scans,
    security,
    security_events,
    teams,
    testimonials,
    websocket,
)
from app.api.v1 import v1_router
from app.config import get_settings
from app.database.database import init_db
from app.utils.logger import logger, bind_request_context, clear_request_context
from app.utils.ratelimit import limiter

settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Envelope middleware is registered first so it is innermost: security headers,
# CORS, and logging middlewares all run outside it and apply to the final
# wrapped response.
app.middleware("http")(envelope_middleware)

app.state.limiter = limiter
register_exception_handlers(app)

if settings.CORS_ALLOW_ALL:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request and response."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestIDMiddleware)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    request_id = getattr(request.state, "request_id", "-")

    # Bind request context for structured logging
    bind_request_context(
        request_id=request_id,
        path=request.url.path,
        method=request.method,
    )

    try:
        response = await call_next(request)
    finally:
        clear_request_context()

    duration = time.time() - start
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code}",
        extra={"duration": duration, "status_code": response.status_code},
    )

    # Record Prometheus metrics
    try:
        from app.api.routes.metrics import REQUEST_COUNT, REQUEST_LATENCY

        path_label = request.url.path
        REQUEST_COUNT.labels(
            method=request.method, path=path_label, status=str(response.status_code)
        ).inc()
        REQUEST_LATENCY.labels(method=request.method, path=path_label).observe(duration)
    except Exception:
        pass

    return response


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    if settings.ENABLE_SECURITY_HEADERS:
        # Core security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"  # Modern: disable in favor of CSP
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), ambient-light-sensor=(), autoplay=(), battery=(), "
            "camera=(), cross-origin-isolated=(), display-capture=(), document-domain=(), "
            "encrypted-media=(), execution-while-not-rendered=(), "
            "execution-while-out-of-viewport=(), fullscreen=(), geolocation=(), "
            "gyroscope=(), keyboard-map=(), magnetometer=(), microphone=(), "
            "midi=(), navigation-override=(), payment=(), picture-in-picture=(), "
            "publickey-credentials-get=(), screen-wake-lock=(), sync-xhr=(), "
            "usb=(), web-share=(), xr-spatial-tracking=()"
        )

        # HSTS (only on HTTPS)
        is_secure = (request.headers.get("x-forwarded-proto") or request.url.scheme) == "https"
        if is_secure:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={settings.HSTS_MAX_AGE}; includeSubDomains; preload"
            )

        # Cross-Origin policies
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # Remove server identification
        response.headers.pop("server", None)

        # Content Security Policy — strict, report-only in dev
        if request.url.path not in ("/docs", "/redoc", "/openapi.json"):
            csp_directives = [
                "default-src 'self'",
                "script-src 'self'",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data:",
                "font-src 'self' data:",
                "connect-src 'self'",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "object-src 'none'",
                "worker-src 'none'",
                "upgrade-insecure-requests",
            ]
            # Allow WebSocket in development
            if settings.SENTINEL_ENV == "development":
                csp_directives[5] = "connect-src 'self' ws: wss:"
            response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

    return response


app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(scans.router)
app.include_router(websocket.router)
app.include_router(security.router)
app.include_router(security_events.router)
app.include_router(metrics.router)
app.include_router(organizations.router)
app.include_router(teams.router)
app.include_router(invitations.router)
app.include_router(api_keys.router)
app.include_router(audit.router)
app.include_router(testimonials.router)
app.include_router(enterprise.router)
app.include_router(v1_router)


@app.on_event("startup")
async def startup():
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database init failed: {e}")

    # Security: warn if using default secret key
    if not settings.validate_secret_key():
        logger.critical(
            "SECURITY WARNING: Using default SECRET_KEY! "
            "Set SECRET_KEY environment variable in production. "
            "All JWT tokens are forgeable with the default key."
        )


@app.get("/", tags=["Health"])
@limiter.exempt
def health_check():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
    }


@app.get("/api/health", tags=["Health"])
@limiter.exempt
def api_health():
    return {"status": "healthy"}
