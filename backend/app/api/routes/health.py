"""Health check routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response

from app.api.deps import get_app_settings
from app.config import Settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(settings: Settings = Depends(get_app_settings)) -> dict:
    """Liveness probe. Confirms the API process is running."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/ready")
async def readiness_check(
    response: Response,
    settings: Settings = Depends(get_app_settings),
) -> dict:
    """Readiness probe. Confirms required integrations are configured."""
    checks = {
        "api": True,
        "openai_configured": bool(settings.openai_api_key),
        "google_configured": bool(settings.google_api_key),
        "llm_configured": bool(settings.openai_api_key or settings.google_api_key),
        "tavily_configured": bool(settings.tavily_api_key),
        "finnhub_configured": bool(settings.finnhub_api_key),
        "prism_enabled": settings.prism_enabled,
        "prism_required": settings.prism_required,
    }
    ready = not settings.prism_required or settings.prism_enabled
    if not ready:
        response.status_code = 503
    return {
        "status": "ready" if ready else "not_ready",
        "service": settings.app_name,
        "version": settings.app_version,
        "checks": checks,
        "timestamp": datetime.now(UTC).isoformat(),
    }
