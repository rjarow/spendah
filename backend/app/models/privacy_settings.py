"""Privacy settings model - persisted in database like alert_settings."""

from sqlalchemy import Column, Integer, Boolean, DateTime
from sqlalchemy.sql import func
import uuid

from app.database import Base


class PrivacySettings(Base):
    """
    Privacy settings stored in database.
    Singleton pattern - only one row with id=1.
    Similar to AlertSettings model.
    """
    __tablename__ = "privacy_settings"

    id = Column(Integer, primary_key=True, default=1)

    # Master toggle
    obfuscation_enabled = Column(Boolean, default=True, nullable=False)

    # Per-provider settings
    # Local providers default to OFF (no need to obfuscate)
    ollama_obfuscation = Column(Boolean, default=False, nullable=False)

    # Cloud providers default to ON
    openrouter_obfuscation = Column(Boolean, default=True, nullable=False)
    anthropic_obfuscation = Column(Boolean, default=True, nullable=False)
    openai_obfuscation = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


def get_or_create_privacy_settings(db) -> PrivacySettings:
    """Get the singleton privacy settings, creating with defaults if needed."""
    settings = db.query(PrivacySettings).filter(PrivacySettings.id == 1).first()
    if not settings:
        settings = PrivacySettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings
