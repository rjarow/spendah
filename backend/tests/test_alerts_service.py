"""Tests for alerts service threshold logic."""

import pytest
from datetime import date, timedelta
from decimal import Decimal
import uuid

from app.services.alerts_service import (
    get_or_create_settings,
    get_category_average,
    is_first_time_merchant,
    check_price_increase,
    get_alerts,
    get_unread_count,
    mark_all_read,
    get_upcoming_renewals,
)
from app.models.transaction import Transaction
from app.models.recurring import RecurringGroup, Frequency
from app.models.alert import Alert, AlertType, Severity


class TestAlertSettings:
    """Test alert settings management."""

    def test_creates_default_settings(self, db_session):
        """Should create default settings if none exist."""
        settings = get_or_create_settings(db_session)
        assert settings is not None
        assert float(settings.large_purchase_multiplier) == 3.0
        assert float(settings.unusual_merchant_threshold) == 200.0
        assert settings.alerts_enabled is True

    def test_returns_existing_settings(self, db_session, alert_settings):
        """Should return existing settings, not create new."""
        settings = get_or_create_settings(db_session)
        assert settings.id == alert_settings.id


class TestCategoryAverage:
    """Test category spending average calculation."""

    def test_no_transactions(self, db_session, sample_category):
        """Average should be 0 with no transactions."""
        avg = get_category_average(db_session, sample_category.id)
        assert avg == 0.0

    def test_calculates_average(self, db_session, sample_category, sample_account):
        """Should calculate average of expenses."""
        # Add some transactions with recent dates
        amounts = [Decimal("-50.00"), Decimal("-100.00"), Decimal("-150.00")]
        for i, amount in enumerate(amounts):
            txn = Transaction(
                id=str(uuid.uuid4()),
                hash=f"hash-cat-{i}",
                date=date.today() - timedelta(days=i + 1),  # Recent dates
                amount=amount,
                raw_description=f"Test {i}",
                category_id=sample_category.id,
                account_id=sample_account.id
            )
            db_session.add(txn)
        db_session.commit()

        avg = get_category_average(db_session, sample_category.id, months=12)
        assert avg == 100.0  # Average of 50, 100, 150

    def test_only_expenses(self, db_session, sample_category, sample_account):
        """Should only average negative amounts (expenses)."""
        # Add an income transaction
        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-income",
            date=date(2024, 1, 1),
            amount=Decimal("500.00"),  # Positive = income
            raw_description="Refund",
            category_id=sample_category.id,
            account_id=sample_account.id
        )
        db_session.add(txn)
        db_session.commit()

        avg = get_category_average(db_session, sample_category.id)
        assert avg == 0.0  # Income should be excluded


class TestFirstTimeMerchant:
    """Test first-time merchant detection."""

    def test_new_merchant(self, db_session):
        """Should return True for unknown merchant."""
        assert is_first_time_merchant(db_session, "Brand New Store") is True

    def test_existing_merchant(self, db_session, sample_transaction):
        """Should return False for known merchant."""
        assert is_first_time_merchant(db_session, sample_transaction.clean_merchant) is False

    def test_excludes_current_transaction(self, db_session, sample_transaction):
        """Should exclude specified transaction from check."""
        # Even though merchant exists, excluding this txn makes it "new"
        result = is_first_time_merchant(
            db_session,
            sample_transaction.clean_merchant,
            exclude_txn_id=sample_transaction.id
        )
        assert result is True


class TestPriceIncrease:
    """Test price increase detection."""

    def test_no_recurring_group(self, db_session):
        """Should return None if no recurring group."""
        result = check_price_increase(db_session, "Netflix", 15.99, None)
        assert result is None

    def test_no_expected_amount(self, db_session, sample_recurring_group):
        """Should return None if group has no expected amount."""
        sample_recurring_group.expected_amount = None
        db_session.commit()

        result = check_price_increase(db_session, "Netflix", 15.99, sample_recurring_group)
        assert result is None

    def test_no_increase(self, db_session, sample_recurring_group):
        """Should return None if amount hasn't increased."""
        result = check_price_increase(db_session, "Netflix", 15.99, sample_recurring_group)
        assert result is None

    def test_small_increase_ignored(self, db_session, sample_recurring_group):
        """Should return None for increases under 5%."""
        # 15.99 * 1.04 = 16.63 (4% increase)
        result = check_price_increase(db_session, "Netflix", 16.63, sample_recurring_group)
        assert result is None

    def test_detects_increase(self, db_session, sample_recurring_group):
        """Should detect price increase over 5%."""
        # 15.99 * 1.10 = 17.59 (10% increase)
        result = check_price_increase(db_session, "Netflix", 17.59, sample_recurring_group)
        assert result is not None
        assert result["previous_amount"] == 15.99
        assert result["new_amount"] == 17.59
        assert result["increase"] == pytest.approx(1.60, rel=0.01)


class TestAlertQueries:
    """Test alert query functions."""

    def test_get_alerts_empty(self, db_session):
        """Should return empty list with no alerts."""
        alerts = get_alerts(db_session)
        assert alerts == []

    def test_get_alerts_filters_dismissed(self, db_session):
        """Should filter out dismissed alerts by default."""
        alert = Alert(
            id=str(uuid.uuid4()),
            type=AlertType.large_purchase,
            severity=Severity.warning,
            title="Test",
            description="Test alert",
            is_dismissed=True
        )
        db_session.add(alert)
        db_session.commit()

        alerts = get_alerts(db_session)
        assert alerts == []

    def test_get_unread_count(self, db_session):
        """Should count unread, non-dismissed alerts."""
        # Add 2 unread, 1 read
        for i in range(2):
            db_session.add(Alert(
                id=str(uuid.uuid4()),
                type=AlertType.large_purchase,
                severity=Severity.info,
                title=f"Unread {i}",
                description="Test",
                is_read=False
            ))
        db_session.add(Alert(
            id=str(uuid.uuid4()),
            type=AlertType.large_purchase,
            severity=Severity.info,
            title="Read",
            description="Test",
            is_read=True
        ))
        db_session.commit()

        count = get_unread_count(db_session)
        assert count == 2

    def test_mark_all_read(self, db_session):
        """Should mark all alerts as read."""
        for i in range(3):
            db_session.add(Alert(
                id=str(uuid.uuid4()),
                type=AlertType.large_purchase,
                severity=Severity.info,
                title=f"Alert {i}",
                description="Test",
                is_read=False
            ))
        db_session.commit()

        updated = mark_all_read(db_session)
        assert updated == 3
        assert get_unread_count(db_session) == 0


class TestUpcomingRenewals:
    """Test upcoming renewals query (Phase 6)."""

    def test_empty_renewals(self, db_session):
        """Should return empty when no upcoming renewals."""
        result = get_upcoming_renewals(db_session, days=30)
        assert result["renewals"] == []
        assert result["total_upcoming_30_days"] == 0

    def test_future_renewal_excluded(self, db_session, sample_recurring_group, sample_account):
        """Should exclude renewals beyond 30 days."""
        # Set next expected date to 60 days in future
        sample_recurring_group.next_expected_date = date.today() + timedelta(days=60)
        db_session.commit()

        result = get_upcoming_renewals(db_session, days=30)
        assert result["renewals"] == []

    def test_past_renewal_included(self, db_session, sample_recurring_group, sample_account):
        """Should include renewals within 30 days."""
        # Set next expected date to 7 days in future
        sample_recurring_group.next_expected_date = date.today() + timedelta(days=7)
        db_session.commit()

        result = get_upcoming_renewals(db_session, days=30)
        assert len(result["renewals"]) == 1
        assert result["renewals"][0]["days_until"] == 7

    def test_inactive_group_excluded(self, db_session, sample_recurring_group):
        """Should exclude inactive recurring groups."""
        sample_recurring_group.is_active = False
        db_session.commit()

        result = get_upcoming_renewals(db_session, days=30)
        assert result["renewals"] == []

    def test_no_next_expected_date_excluded(self, db_session, sample_recurring_group):
        """Should exclude groups with no next expected date."""
        sample_recurring_group.next_expected_date = None
        sample_recurring_group.is_active = True
        db_session.commit()

        result = get_upcoming_renewals(db_session, days=30)
        assert result["renewals"] == []

    def test_calculates_total(self, db_session, sample_recurring_group, sample_account):
        """Should sum amounts of upcoming renewals."""
        # Add another recurring group with upcoming date
        group2 = RecurringGroup(
            id=str(uuid.uuid4()),
            name="Spotify",
            merchant_pattern="Spotify",
            expected_amount=Decimal("10.00"),
            amount_variance=Decimal("10.0"),
            frequency=Frequency.monthly,
            category_id=sample_recurring_group.category_id,
            is_active=True,
            last_seen_date=date(2024, 1, 1),
            next_expected_date=date.today() + timedelta(days=15)
        )
        db_session.add(group2)
        db_session.commit()

        result = get_upcoming_renewals(db_session, days=30)
        assert result["total_upcoming_30_days"] == pytest.approx(25.99, rel=0.01)
