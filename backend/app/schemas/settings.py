from pydantic import BaseModel
from typing import Optional, List


class AISettings(BaseModel):
    provider: str
    model: str
    auto_categorize: bool
    clean_merchants: bool
    detect_format: bool


class AISettingsUpdate(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    auto_categorize: Optional[bool] = None
    clean_merchants: Optional[bool] = None
    detect_format: Optional[bool] = None


class AvailableProvider(BaseModel):
    id: str
    name: str
    requires_key: bool
    models: List[str]


class SettingsResponse(BaseModel):
    ai: AISettings
    available_providers: List[AvailableProvider]
