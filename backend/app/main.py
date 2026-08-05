
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.limiter import limiter
from app.core.middleware import SecurityHeadersMiddleware

settings = get_settings()

app = FastAPI(
    title="ContractAI API",
    version="0.1.0",
    # Hide interactive docs in production to reduce attack-surface discovery
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url=None,
)

# --- Rate limiting ---
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Too many requests. Please slow down."})


# --- CORS: locked to the known frontend origin, not '*' ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)

# --- Trusted host: rejects requests with spoofed/unexpected Host headers ---
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", settings.FRONTEND_ORIGIN.replace("http://", "").replace("https://", "")],
)

# --- Security headers on every response ---
app.add_middleware(SecurityHeadersMiddleware)


@app.get("/health")
async def health_check():
    """Liveness/readiness probe target for Docker/CI. No auth required,
    intentionally returns no internal details."""
    return {"status": "ok"}

from app.api import projects, images  # noqa: E402

app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(images.router, prefix="/projects", tags=["images"])
