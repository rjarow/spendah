"""Schemas for privacy settings."""

from pydantic import BaseModel
from typing import Optional, List, Dict


class ProviderPrivacyConfig(BaseModel):
    """Privacy settings for a specific AI provider."""
    provider: str
    obfuscation_enabled: bool


class PrivacySettingsResponse(BaseModel):
    """Privacy settings response."""
    obfuscation_enabled: bool
    provider_settings: List[ProviderPrivacyConfig]

    class Config:
        from_attributes = True


class PrivacySettingsUpdate(BaseModel):
    """Update privacy settings."""
    obfuscation_enabled: Optional[bool] = None
    provider_settings: Optional[List[ProviderPrivacyConfig]] = None


class TokenStats(BaseModel):
    """Statistics about tokenization."""
    merchants: int
    accounts: int
    people: int
    date_shift_days: int


class PrivacyPreview(BaseModel):
    """Preview of tokenized data."""
    original: str
    tokenized: str


class TokenInfo(BaseModel):
    """Info about a single token."""
    token: str
    original: str
    token_type: str
    metadata: Optional[Dict] = None
    created_at: str


class PrivacyStatusResponse(BaseModel):
    """Full privacy status response."""
    obfuscation_enabled: bool
    provider_settings: List[ProviderPrivacyConfig]
    stats: TokenStats
