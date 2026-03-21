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


class TaskModels(BaseModel):
    categorize: Optional[str] = None
    merchant_clean: Optional[str] = None
    format_detect: Optional[str] = None
    coach: Optional[str] = None


class TaskModelsUpdate(BaseModel):
    categorize: Optional[str] = None
    merchant_clean: Optional[str] = None
    format_detect: Optional[str] = None
    coach: Optional[str] = None


class APIKeys(BaseModel):
    openrouter_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None


class APIKeysUpdate(BaseModel):
    openrouter_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None


class AvailableProvider(BaseModel):
    id: str
    name: str
    requires_key: bool
    models: List[str]


class SettingsResponse(BaseModel):
    ai: AISettings
    api_keys: APIKeys
    task_models: TaskModels
    available_providers: List[AvailableProvider]
