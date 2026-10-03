"""Read-only public model/rate configuration. Never exposes credentials or calls a provider."""
from fastapi import APIRouter
from app.core.config import get_settings
router = APIRouter(tags=["pricing"])

@router.get("/pricing")
def pricing() -> dict:
    settings = get_settings()
    return {
        "models": {"classifier": settings.openai_classifier_model, "research": settings.research_model,
                   "brief": settings.brief_model, "writer": settings.writer_model},
        "rates": settings.llm_pricing,
        "source_url": "https://developers.openai.com/api/docs/pricing",
        "verified_at": "2026-10-03",
    }
