"""
Application configuration using Pydantic settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # App
    app_name: str = "Spendah"

    # Database
    database_url: str = "sqlite:///./data/db.sqlite"

    # Import paths
    import_inbox_path: str = "./data/imports/inbox"
    import_processed_path: str = "./data/imports/processed"
    import_failed_path: str = "./data/imports/failed"

    # AI Provider
    ai_provider: str = "openrouter"  # openrouter, ollama, openai, anthropic
    ai_model: str = "anthropic/claude-3-haiku"
    ai_base_url: Optional[str] = None  # For Ollama: http://localhost:11434

    # API Keys (optional based on provider)
    openrouter_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # AI Feature Flags
    ai_auto_categorize: bool = True
    ai_clean_merchants: bool = True
    ai_detect_format: bool = True

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_url: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file="/app/.env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# Global settings instance
settings = Settings()
