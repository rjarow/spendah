"""AI settings model - persisted in database for API keys and per-task models."""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class AISettingsDB(Base):
    """
    AI settings stored in database.
    Singleton pattern - only one row with id=1.
    """

    __tablename__ = "ai_settings"

    id = Column(Integer, primary_key=True, default=1)

    openrouter_api_key = Column(String(255), nullable=True)
    openai_api_key = Column(String(255), nullable=True)
    anthropic_api_key = Column(String(255), nullable=True)

    categorize_model = Column(String(100), nullable=True)
    merchant_clean_model = Column(String(100), nullable=True)
    format_detect_model = Column(String(100), nullable=True)
    coach_model = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


def get_or_create_ai_settings(db) -> AISettingsDB:
    """Get the singleton AI settings, creating with defaults if needed."""
    settings = db.query(AISettingsDB).filter(AISettingsDB.id == 1).first()
    if not settings:
        settings = AISettingsDB(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings
