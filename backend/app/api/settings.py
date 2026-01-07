from fastapi import APIRouter, HTTPException
from app.schemas.settings import (
    AISettings,
    AISettingsUpdate,
    SettingsResponse,
    AvailableProvider
)
from app.config import settings
import os

router = APIRouter(prefix="/settings", tags=["settings"])

AVAILABLE_PROVIDERS = [
    AvailableProvider(
        id="openrouter",
        name="OpenRouter",
        requires_key=True,
        models=[
            "anthropic/claude-3-haiku",
            "anthropic/claude-3-sonnet",
            "openai/gpt-4o-mini",
            "openai/gpt-4o",
            "google/gemini-flash-1.5",
            "meta-llama/llama-3.1-8b-instruct",
        ]
    ),
    AvailableProvider(
        id="ollama",
        name="Ollama (Local)",
        requires_key=False,
        models=[
            "llama3.1:8b",
            "llama3.1:70b",
            "mistral:7b",
            "codellama:7b",
        ]
    ),
    AvailableProvider(
        id="anthropic",
        name="Anthropic",
        requires_key=True,
        models=[
            "claude-3-haiku-20240307",
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229",
        ]
    ),
    AvailableProvider(
        id="openai",
        name="OpenAI",
        requires_key=True,
        models=[
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4-turbo",
        ]
    ),
]


@router.get("", response_model=SettingsResponse)
def get_settings():
    return SettingsResponse(
        ai=AISettings(
            provider=settings.ai_provider,
            model=settings.ai_model,
            auto_categorize=settings.ai_auto_categorize,
            clean_merchants=settings.ai_clean_merchants,
            detect_format=settings.ai_detect_format,
        ),
        available_providers=AVAILABLE_PROVIDERS
    )


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

    from app.ai.client import _ai_client
    global _ai_client
    _ai_client = None

    return AISettings(
        provider=settings.ai_provider,
        model=settings.ai_model,
        auto_categorize=settings.ai_auto_categorize,
        clean_merchants=settings.ai_clean_merchants,
        detect_format=settings.ai_detect_format,
    )


@router.post("/ai/test")
async def test_ai_connection():
    from app.ai.client import get_ai_client

    try:
        client = get_ai_client()
        response = await client.complete(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'OK' if you can hear me.",
            max_tokens=10
        )
        return {"status": "ok", "response": response.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI connection failed: {str(e)}")
