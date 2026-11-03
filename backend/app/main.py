import os
import logging
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .db import SessionLocal, Base, engine
from .models import User
from .routers import market, strategies, backtests, paper, journal, watchlist, research, lineage, auth
from .config import get_settings
from .security import limiter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Validate critical settings at startup
settings = get_settings()
if not settings.JWT_SECRET_KEY or len(settings.JWT_SECRET_KEY) < 32:
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        raise RuntimeError("JWT_SECRET_KEY must be set and at least 32 characters in production")
    else:
        logger.warning("JWT_SECRET_KEY is not set or too short; using development default")

Base.metadata.create_all(bind=engine)  # safety net; Alembic is the primary path
with SessionLocal() as db:  # single seeded local user (no auth in MVP)
    if not db.get(User, 1): db.add(User(id=1, email="local@quantniti")); db.commit()

app = FastAPI(title="QuantNiti — PAPER/SIMULATED ONLY")

# Attach rate limiter to app state for access in routers
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS hardening: explicit origins, methods, headers; no wildcard with credentials
cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]
# Reject wildcard when credentials would be needed
if "*" in cors_origins:
    logger.warning("CORS wildcard origin detected; credentials will not be allowed")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
    allow_credentials=False,  # Tokens via Authorization header, not cookies
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # CSP: allow self, inline scripts/styles for dev, connect to API origin
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        f"connect-src 'self' {cors_origins[0] if cors_origins else 'http://localhost:5173'}; "
        "font-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers["Content-Security-Policy"] = csp
    return response

for r in (market, strategies, backtests, paper, journal, watchlist, research, lineage, auth):
    app.include_router(r.router)


@app.get("/api/health")
def health(): return {"ok": True, "mode": "PAPER/SIMULATED", "live_trading": False}
