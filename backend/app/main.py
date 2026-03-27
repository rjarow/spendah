"""
FastAPI application entry point.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.api.router import api_router


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Local-first personal finance tracker with AI-powered categorization",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def read_root():
    """Root endpoint."""
    return {"name": settings.app_name, "version": "1.0.0", "status": "running"}


@app.get("/api/v1/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "app_name": settings.app_name}
