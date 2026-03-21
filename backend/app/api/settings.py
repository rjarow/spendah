from fastapi import APIRouter, HTTPException, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
import httpx

from app.schemas.settings import (
    AISettings,
    AISettingsUpdate,
    SettingsResponse,
    AvailableProvider,
    APIKeys,
    APIKeysUpdate,
    TaskModels,
    TaskModelsUpdate,
)
from app.config import settings
from app.dependencies import get_db
from app.models.ai_settings import get_or_create_ai_settings
import logging

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULT_PROVIDERS = [
    AvailableProvider(
        id="openrouter",
        name="OpenRouter",
        requires_key=True,
        models=[
            "anthropic/claude-3-haiku",
            "anthropic/claude-3.5-haiku",
            "anthropic/claude-3.7-sonnet",
            "openai/gpt-4o-mini",
            "openai/gpt-4o",
        ],
    ),
    AvailableProvider(
        id="ollama",
        name="Ollama (Local)",
        requires_key=False,
        models=["llama3.1:8b", "mistral:7b"],
    ),
    AvailableProvider(
        id="anthropic",
        name="Anthropic",
        requires_key=True,
        models=[
            "claude-3-haiku-20240307",
            "claude-3-5-haiku-20241022",
            "claude-3-5-sonnet-20241022",
        ],
    ),
    AvailableProvider(
        id="openai",
        name="OpenAI",
        requires_key=True,
        models=["gpt-4o-mini", "gpt-4o"],
    ),
]


def _mask_key(key):
    if not key:
        return None
    if len(key) <= 4:
        return "****"
    return "*" * (len(key) - 4) + key[-4:]


@router.get("", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    ai_settings = get_or_create_ai_settings(db)

    return SettingsResponse(
        ai=AISettings(
            provider=settings.ai_provider,
            model=settings.ai_model,
            auto_categorize=settings.ai_auto_categorize,
            clean_merchants=settings.ai_clean_merchants,
            detect_format=settings.ai_detect_format,
        ),
        api_keys=APIKeys(
            openrouter_api_key=_mask_key(ai_settings.openrouter_api_key),
            openai_api_key=_mask_key(ai_settings.openai_api_key),
            anthropic_api_key=_mask_key(ai_settings.anthropic_api_key),
        ),
        task_models=TaskModels(
            categorize=ai_settings.categorize_model,
            merchant_clean=ai_settings.merchant_clean_model,
            format_detect=ai_settings.format_detect_model,
            coach=ai_settings.coach_model,
        ),
        available_providers=DEFAULT_PROVIDERS,
    )


@router.get("/providers/{provider_id}/models")
async def get_provider_models(provider_id: str, db: Session = Depends(get_db)):
    ai_settings = get_or_create_ai_settings(db)

    if provider_id == "openrouter":
        api_key = ai_settings.openrouter_api_key
        if not api_key:
            raise HTTPException(
                status_code=400, detail="OpenRouter API key not configured"
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()

            models = []
            for model in data.get("data", []):
                model_id = model.get("id", "")
                pricing = model.get("pricing", {})
                prompt_price = pricing.get("prompt", "0")
                label = model_id
                if prompt_price and prompt_price != "0":
                    try:
                        price_float = float(prompt_price)
                        if price_float > 0:
                            label += f" (${price_float * 1_000_000:.2f}/M)"
                    except (ValueError, TypeError):
                        pass
                models.append({"id": model_id, "name": model_id, "label": label})

            models.sort(key=lambda m: m["id"])
            return {"models": models}

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch OpenRouter models: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch models")

    elif provider_id == "ollama":
        ollama_url = settings.ai_base_url or "http://localhost:11434"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{ollama_url}/api/tags", timeout=5.0)
                response.raise_for_status()
                data = response.json()

            models = [
                {
                    "id": m.get("name", ""),
                    "name": m.get("name", ""),
                    "label": m.get("name", ""),
                }
                for m in data.get("models", [])
            ]
            return {"models": models}

        except httpx.HTTPError:
            raise HTTPException(status_code=500, detail="Is Ollama running?")

    elif provider_id == "anthropic":
        return {
            "models": [
                {
                    "id": "claude-3-haiku-20240307",
                    "name": "Claude 3 Haiku",
                    "label": "claude-3-haiku-20240307 ($0.25/M)",
                },
                {
                    "id": "claude-3-5-haiku-20241022",
                    "name": "Claude 3.5 Haiku",
                    "label": "claude-3-5-haiku-20241022 ($1.00/M)",
                },
                {
                    "id": "claude-3-5-sonnet-20241022",
                    "name": "Claude 3.5 Sonnet",
                    "label": "claude-3-5-sonnet-20241022 ($3.00/M)",
                },
                {
                    "id": "claude-3-7-sonnet-20250219",
                    "name": "Claude 3.7 Sonnet",
                    "label": "claude-3-7-sonnet-20250219 ($3.00/M)",
                },
            ]
        }

    elif provider_id == "openai":
        return {
            "models": [
                {
                    "id": "gpt-4o-mini",
                    "name": "GPT-4o Mini",
                    "label": "gpt-4o-mini ($0.15/M)",
                },
                {"id": "gpt-4o", "name": "GPT-4o", "label": "gpt-4o ($2.50/M)"},
            ]
        }

    raise HTTPException(status_code=404, detail="Provider not found")


@router.patch("/ai", response_model=AISettings)
def update_ai_settings(update: AISettingsUpdate):
    if update.provider is not None:
        settings.ai_provider = update.provider
    if update.model is not None:
        settings.ai_model = update.model
    if update.auto_categorize is not None:
        settings.ai_auto_categorize = update.auto_categorize
    if update.clean_merchants is not None:
        settings.ai_clean_merchants = update.clean_merchants
    if update.detect_format is not None:
        settings.ai_detect_format = update.detect_format

    from app.ai import client

    client._ai_client = None

    return AISettings(
        provider=settings.ai_provider,
        model=settings.ai_model,
        auto_categorize=settings.ai_auto_categorize,
        clean_merchants=settings.ai_clean_merchants,
        detect_format=settings.ai_detect_format,
    )


@router.patch("/task-models", response_model=TaskModels)
def update_task_models(update: TaskModelsUpdate, db: Session = Depends(get_db)):
    ai_settings = get_or_create_ai_settings(db)

    if update.categorize is not None:
        ai_settings.categorize_model = update.categorize or None
    if update.merchant_clean is not None:
        ai_settings.merchant_clean_model = update.merchant_clean or None
    if update.format_detect is not None:
        ai_settings.format_detect_model = update.format_detect or None
    if update.coach is not None:
        ai_settings.coach_model = update.coach or None

    db.commit()

    return TaskModels(
        categorize=ai_settings.categorize_model,
        merchant_clean=ai_settings.merchant_clean_model,
        format_detect=ai_settings.format_detect_model,
        coach=ai_settings.coach_model,
    )


@router.patch("/api-keys", response_model=APIKeys)
def update_api_keys(update: APIKeysUpdate, db: Session = Depends(get_db)):
    ai_settings = get_or_create_ai_settings(db)

    if update.openrouter_api_key is not None:
        ai_settings.openrouter_api_key = update.openrouter_api_key or None
    if update.openai_api_key is not None:
        ai_settings.openai_api_key = update.openai_api_key or None
    if update.anthropic_api_key is not None:
        ai_settings.anthropic_api_key = update.anthropic_api_key or None

    db.commit()

    from app.ai import client

    client._ai_client = None

    return APIKeys(
        openrouter_api_key=_mask_key(ai_settings.openrouter_api_key),
        openai_api_key=_mask_key(ai_settings.openai_api_key),
        anthropic_api_key=_mask_key(ai_settings.anthropic_api_key),
    )


@router.post("/ai/test")
@limiter.limit("5/minute")
async def test_ai_connection(request: Request, db: Session = Depends(get_db)):
    from app.ai.client import get_ai_client_with_db

    try:
        ai_client = get_ai_client_with_db(db)
        response = await ai_client.complete(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'OK' if you can hear me.",
            max_tokens=10,
        )
        return {"status": "ok", "response": response.strip()}
    except Exception as e:
        logger.error(f"AI connection test failed: {e}")
        raise HTTPException(status_code=500, detail="AI connection test failed")


@router.get("/ai/usage")
def get_ai_usage(days: int = 30, db: Session = Depends(get_db)):
    """Get AI token usage statistics for the last N days."""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from app.models.ai_token_usage import AITokenUsage

    start_date = datetime.utcnow() - timedelta(days=days)

    usage_records = (
        db.query(AITokenUsage).filter(AITokenUsage.created_at >= start_date).all()
    )

    total_prompt = sum(r.prompt_tokens or 0 for r in usage_records)
    total_completion = sum(r.completion_tokens or 1 for r in usage_records)
    total_tokens = sum(r.total_tokens or 1 for r in usage_records)

    by_task = {}
    for record in usage_records:
        task = record.task or "unknown"
        if task not in by_task:
            by_task[task] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "call_count": 0,
            }
        by_task[task]["prompt_tokens"] += record.prompt_tokens or 0
        by_task[task]["completion_tokens"] += record.completion_tokens or 1
        by_task[task]["total_tokens"] += record.total_tokens or 1
        by_task[task]["call_count"] += 1

    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "totals": {
            "prompt_tokens": total_prompt,
            "completion_tokens": total_completion,
            "total_tokens": total_tokens,
            "call_count": len(usage_records),
        },
        "by_task": by_task,
    }
