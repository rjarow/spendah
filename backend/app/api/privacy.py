"""Privacy settings API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.schemas.privacy import (
    PrivacySettingsResponse,
    PrivacySettingsUpdate,
    PrivacyStatusResponse,
    PrivacyPreview,
    TokenInfo,
    TokenStats,
    ProviderPrivacyConfig,
)
from app.services.tokenization_service import TokenizationService
from app.models.token_map import TokenMap, TokenType
from app.models.privacy_settings import get_or_create_privacy_settings

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.get("/settings", response_model=PrivacyStatusResponse)
def get_privacy_settings(db: Session = Depends(get_db)):
    """Get current privacy settings and token statistics."""
    settings = get_or_create_privacy_settings(db)
    token_service = TokenizationService(db)
    stats = token_service.get_token_stats()

    provider_settings = [
        ProviderPrivacyConfig(provider="ollama", obfuscation_enabled=settings.ollama_obfuscation),
        ProviderPrivacyConfig(provider="openrouter", obfuscation_enabled=settings.openrouter_obfuscation),
        ProviderPrivacyConfig(provider="anthropic", obfuscation_enabled=settings.anthropic_obfuscation),
        ProviderPrivacyConfig(provider="openai", obfuscation_enabled=settings.openai_obfuscation),
    ]

    return PrivacyStatusResponse(
        obfuscation_enabled=settings.obfuscation_enabled,
        provider_settings=provider_settings,
        stats=TokenStats(
            merchants=stats.get("merchant", 0),
            accounts=stats.get("account", 0),
            people=stats.get("person", 0),
            date_shift_days=stats.get("date_shift_days", 0),
        )
    )


@router.patch("/settings", response_model=PrivacyStatusResponse)
def update_privacy_settings(
    updates: PrivacySettingsUpdate,
    db: Session = Depends(get_db)
):
    """Update privacy settings."""
    settings = get_or_create_privacy_settings(db)

    if updates.obfuscation_enabled is not None:
        settings.obfuscation_enabled = updates.obfuscation_enabled

    if updates.provider_settings:
        for ps in updates.provider_settings:
            if ps.provider == "ollama":
                settings.ollama_obfuscation = ps.obfuscation_enabled
            elif ps.provider == "openrouter":
                settings.openrouter_obfuscation = ps.obfuscation_enabled
            elif ps.provider == "anthropic":
                settings.anthropic_obfuscation = ps.obfuscation_enabled
            elif ps.provider == "openai":
                settings.openai_obfuscation = ps.obfuscation_enabled

    db.commit()
    db.refresh(settings)

    return get_privacy_settings(db)


@router.get("/preview")
def preview_tokenization(
    text: str,
    db: Session = Depends(get_db)
) -> PrivacyPreview:
    """Preview how text would be tokenized."""
    token_service = TokenizationService(db)

    # Try tokenizing as merchant
    tokenized = token_service.tokenize_merchant(text)

    return PrivacyPreview(
        original=text,
        tokenized=tokenized
    )


@router.get("/tokens", response_model=List[TokenInfo])
def list_tokens(
    token_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List tokens in the token map."""
    query = db.query(TokenMap)

    if token_type:
        query = query.filter(TokenMap.token_type == token_type)

    tokens = query.order_by(TokenMap.created_at.desc()).offset(offset).limit(limit).all()

    return [
        TokenInfo(
            token=t.token,
            original=t.original_value,
            token_type=t.token_type.value,
            metadata=t.metadata_,
            created_at=t.created_at.isoformat() if t.created_at else ""
        )
        for t in tokens
    ]


@router.get("/stats", response_model=TokenStats)
def get_token_stats(db: Session = Depends(get_db)):
    """Get token statistics."""
    token_service = TokenizationService(db)
    stats = token_service.get_token_stats()

    return TokenStats(
        merchants=stats.get("merchant", 0),
        accounts=stats.get("account", 0),
        people=stats.get("person", 0),
        date_shift_days=stats.get("date_shift_days", 0),
    )
