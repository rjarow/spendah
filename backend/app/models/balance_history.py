"""
BalanceHistory database model.
"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Column, String, Date, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class BalanceHistory(Base):
    """Balance history model for tracking account balances over time."""

    __tablename__ = "balance_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False)
    balance = Column(Numeric(12, 2), nullable=False)
    recorded_at = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    account = relationship("Account", back_populates="balance_history")

    def __repr__(self):
        return f"<BalanceHistory(id={self.id}, account_id={self.account_id}, balance={self.balance}, recorded_at={self.recorded_at})>"
