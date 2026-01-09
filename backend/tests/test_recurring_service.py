"""Tests for recurring service date calculations and group management."""

import pytest
from datetime import date
from decimal import Decimal

from app.services.recurring_service import (
    calculate_next_expected,
    get_group_transaction_count,
)
from app.models.recurring import Frequency
from app.models.transaction import Transaction


class TestCalculateNextExpected:
    """Test next expected date calculations."""

    def test_weekly(self):
        """Weekly should add 7 days."""
        result = calculate_next_expected(date(2024, 1, 15), Frequency.weekly)
        assert result == date(2024, 1, 22)

    def test_biweekly(self):
        """Biweekly should add 14 days."""
        result = calculate_next_expected(date(2024, 1, 15), Frequency.biweekly)
        assert result == date(2024, 1, 29)

    def test_monthly_normal(self):
        """Monthly should add one month."""
        result = calculate_next_expected(date(2024, 1, 15), Frequency.monthly)
        assert result == date(2024, 2, 15)

    def test_monthly_year_rollover(self):
        """Monthly in December should roll to January."""
        result = calculate_next_expected(date(2024, 12, 15), Frequency.monthly)
        assert result == date(2025, 1, 15)

    def test_monthly_end_of_month(self):
        """Monthly on 31st should handle shorter months."""
        result = calculate_next_expected(date(2024, 1, 31), Frequency.monthly)
        # February doesn't have 31 days, should fall back to 28
        assert result == date(2024, 2, 28)

    def test_quarterly(self):
        """Quarterly should add 3 months."""
        result = calculate_next_expected(date(2024, 1, 15), Frequency.quarterly)
        assert result == date(2024, 4, 15)

    def test_quarterly_year_rollover(self):
        """Quarterly in November should roll to next year."""
        result = calculate_next_expected(date(2024, 11, 15), Frequency.quarterly)
        assert result == date(2025, 2, 15)

    def test_yearly(self):
        """Yearly should add one year."""
        result = calculate_next_expected(date(2024, 1, 15), Frequency.yearly)
        assert result == date(2025, 1, 15)

    def test_yearly_leap_day(self):
        """Yearly on Feb 29 should handle non-leap years."""
        result = calculate_next_expected(date(2024, 2, 29), Frequency.yearly)
        # 2025 is not a leap year
        assert result == date(2025, 2, 28) or result == date(2025, 3, 1)


class TestGroupTransactionCount:
    """Test transaction counting for recurring groups."""

    def test_empty_group(self, db_session, sample_recurring_group):
        """Empty group should have count of 0."""
        count = get_group_transaction_count(db_session, sample_recurring_group.id)
        assert count == 0

    def test_with_transactions(self, db_session, sample_recurring_group, sample_account):
        """Should count transactions in group."""
        # Add transactions to the recurring group
        for i in range(3):
            txn = Transaction(
                id=f"txn-{i}",
                hash=f"hash-{i}",
                date=date(2024, 1, i + 1),
                amount=Decimal("-15.99"),
                raw_description="NETFLIX",
                account_id=sample_account.id,
                recurring_group_id=sample_recurring_group.id,
                is_recurring=True
            )
            db_session.add(txn)
        db_session.commit()

        count = get_group_transaction_count(db_session, sample_recurring_group.id)
        assert count == 3

    def test_only_counts_group_transactions(self, db_session, sample_recurring_group, sample_transaction):
        """Should not count transactions from other groups."""
        # sample_transaction is not in sample_recurring_group
        count = get_group_transaction_count(db_session, sample_recurring_group.id)
        assert count == 0
