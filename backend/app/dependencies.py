"""
FastAPI dependencies.
"""

import logging
from typing import Generator
from sqlalchemy.orm import Session
from app.database import SessionLocal

logger = logging.getLogger(__name__)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database sessions.

    Handles transaction management with proper rollback on errors.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        logger.exception("Database transaction failed, rolling back")
        db.rollback()
        raise
    finally:
        db.close()
