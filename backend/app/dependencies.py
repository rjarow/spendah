"""
FastAPI dependencies.
"""

from typing import Generator
from sqlalchemy.orm import Session
from app.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database sessions.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
