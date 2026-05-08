"""
Urban Resilience Platform — Middleware Stack
Part 1: Logging, Error Handling, Rate Limiting, CORS, Security Headers
"""

import time
import uuid
import json
import traceback
from typing import Callable
from datetime import datetime

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from loguru import logger
import sys

from app.core.config import settings
from app.core.database import cache_service

# ══════════════════════════════════════════════════════════════════
# LOGURU SETUP
# ══════════════════════════════════════════════════════════════════

def setup_logging():
    """Configure Loguru structured logging"""
    logger.remove()

    # Console output
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True,
    )

    # File output (JSON for production)
    logger.add(
        settings.LOG_FILE_PATH,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        level=settings.LOG_LEVEL,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="gz",
        serialize=True,  # JSON format
    )

    # Critical errors to separate file
    logger.add(
        "logs/errors.log",
        level="ERROR",
        rotation="1 day",
        retention="90 days",
        compression="gz",
        serialize=True,
        backtrace=True,
        diagnose=True,
    )

    logger.info("✅ Loguru logging initialized")


# ══════════════════════════════════════════════════════════════════
# REQUEST CONTEXT MIDDLEWARE
# ══════════════════════════════════════════════════════════════════

class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request ID and timing to every request"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        request.state.start_time = time.time()

        # Inject request ID into logging context
        with logger.contextualize(request_id=request_id):
            logger.info(
                f"→ {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": str(request.url.path),
                    "query": str(request.url.query),
                    "client_ip": request.client.host if request.client else "unknown",
                }
            )

            response = await call_next(request)
            duration = (time.time() - request.state.start_time) * 1000

            logger.info(
                f"← {request.method} {request.url.path} [{response.status_code}] {duration:.1f}ms",
                extra={
                    "status_code": response.status_code,
                    "duration_ms": round(duration, 2),
                }
            )

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.2f}ms"

        return response


# ══════════════════════════════════════════════════════════════════
# SECURITY HEADERS MIDDLEWARE
# ══════════════════════════════════════════════════════════════════

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers (Helmet equivalent)"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' wss:;"
        )
        response.headers["X-API-Version"] = settings.APP_VERSION

        # Remove server disclosure
        if "server" in response.headers:
            del response.headers["server"]

        return response


# ══════════════════════════════════════════════════════════════════
# RATE LIMITING MIDDLEWARE
# ══════════════════════════════════════════════════════════════════

RATE_LIMIT_ROUTES = {
    "/api/v1/auth": (10, 60),          # 10 req / 60 sec
    "/api/v1/gps": (300, 60),          # 300 req / 60 sec (high frequency)
    "/api/v1/voice": (30, 60),         # 30 req / 60 sec
    "/api/v1/simulation": (20, 60),    # 20 req / 60 sec
    "default": (100, 60),              # 100 req / 60 sec
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed sliding window rate limiter"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting in tests
        if settings.APP_ENV == "test":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # Find applicable rate limit
        limit, window = RATE_LIMIT_ROUTES.get("default", (100, 60))
        for route_prefix, (r_limit, r_window) in RATE_LIMIT_ROUTES.items():
            if route_prefix != "default" and path.startswith(route_prefix):
                limit, window = r_limit, r_window
                break

        key = f"rl:{client_ip}:{path.split('/')[3] if path.count('/') >= 3 else 'api'}"

        try:
            r = await cache_service._get_redis()
            current = await r.incr(key)
            if current == 1:
                await r.expire(key, window)

            remaining = max(0, limit - current)
            reset_ttl = await r.ttl(key)

            if current > limit:
                return JSONResponse(
                    status_code=HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "limit": limit,
                        "window_seconds": window,
                        "retry_after": reset_ttl,
                    },
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_ttl),
                        "Retry-After": str(reset_ttl),
                    }
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_ttl)
            return response

        except Exception:
            # If Redis is down, allow the request (fail open)
            return await call_next(request)


# ══════════════════════════════════════════════════════════════════
# AUDIT LOG MIDDLEWARE
# ══════════════════════════════════════════════════════════════════

AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
AUDIT_SKIP_PATHS = {"/api/v1/health", "/api/v1/gps/batch", "/metrics"}


class AuditMiddleware(BaseHTTPMiddleware):
    """Log all mutating API calls for audit trail"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if (
            request.method not in AUDIT_METHODS
            or request.url.path in AUDIT_SKIP_PATHS
        ):
            return await call_next(request)

        start = time.time()
        body = None

        try:
            body_bytes = await request.body()
            body = json.loads(body_bytes) if body_bytes else None
        except Exception:
            pass

        response = await call_next(request)
        duration = int((time.time() - start) * 1000)

        # Async audit log write (fire-and-forget via Redis queue)
        audit_data = {
            "method": request.method,
            "path": str(request.url.path),
            "status_code": response.status_code,
            "ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent"),
            "duration_ms": duration,
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            r = await cache_service._get_redis()
            await r.lpush("audit:queue", json.dumps(audit_data))
            await r.ltrim("audit:queue", 0, 9999)  # Keep last 10k
        except Exception:
            pass

        return response


# ══════════════════════════════════════════════════════════════════
# GLOBAL EXCEPTION HANDLER
# ══════════════════════════════════════════════════════════════════

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Centralized error handler"""
    request_id = getattr(request.state, "request_id", "unknown")

    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "request_id": request_id,
            },
            headers=exc.headers or {},
        )

    # Unexpected error
    error_id = str(uuid.uuid4())
    logger.error(
        f"Unhandled exception [{error_id}]: {type(exc).__name__}: {str(exc)}\n"
        f"{traceback.format_exc()}"
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_id": error_id,
            "request_id": request_id,
            "message": str(exc) if settings.DEBUG else "An unexpected error occurred",
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url.path),
            "request_id": getattr(request.state, "request_id", None),
        },
    )