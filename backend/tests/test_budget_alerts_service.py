"""Tests for budget alerts service."""

import pytest
from datetime import date, timedelta
from decimal import Decimal
import uuid

from app.services.budget_alerts import (
    get_or_create_settings,
    get_budget_spending,
    check_budget_alerts,
    check_all_budget_alerts,
    get_budget_alert_summary
)
from app.models.budget import Budget, BudgetPeriod
from app.models.category import Category
from app.models.alert import Alert, AlertType, Severity, AlertSettings
from app.models.transaction import Transaction


class TestBudgetAlertSettings:
    """Test budget alert settings management."""

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


class TestBudgetSpendingCalculation:
    """Test budget spending calculation."""

    def test_no_transactions(self, db_session, sample_budget):
        """Spending should be 0 with no transactions."""
        spending = get_budget_spending(db_session, sample_budget)
        assert spending["spent"] == 0.0
        assert spending["percent_used"] == 0.0

    def test_calculates_spending_weekly(self, db_session, sample_budget, sample_account):
        """Should calculate spending over 7 days."""
        amount = Decimal("-75.00")
        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-weekly-1",
            date=date.today() - timedelta(days=2),
            amount=amount,
            raw_description="Weekly spend",
            category_id=sample_budget.category_id,
            account_id=sample_account.id
        )
        db_session.add(txn)
        db_session.commit()

        spending = get_budget_spending(db_session, sample_budget)
        assert spending["spent"] == 75.0
        assert spending["percent_used"] == 15.0

    def test_calculates_spending_monthly(self, db_session, sample_budget, sample_account):
        """Should calculate spending over 30 days."""
        # Change budget to monthly so 30-day window includes transactions from 10 days ago
        sample_budget.period = BudgetPeriod.monthly
        db_session.commit()

        amount = Decimal("-450.00")
        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-monthly-1",
            date=date.today() - timedelta(days=10),
            amount=amount,
            raw_description="Monthly spend",
            category_id=sample_budget.category_id,
            account_id=sample_account.id
        )
        db_session.add(txn)
        db_session.commit()

        spending = get_budget_spending(db_session, sample_budget)
        assert spending["spent"] == 450.0
        assert spending["percent_used"] == 90.0

    def test_calculates_spending_yearly(self, db_session, sample_budget, sample_account):
        """Should calculate spending over 365 days."""
        # Change budget to yearly so 365-day window includes transactions from 180 days ago
        sample_budget.period = BudgetPeriod.yearly
        sample_budget.amount = Decimal("5000.00")
        db_session.commit()

        amount = Decimal("-5400.00")
        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-yearly-1",
            date=date.today() - timedelta(days=180),
            amount=amount,
            raw_description="Yearly spend",
            category_id=sample_budget.category_id,
            account_id=sample_account.id
        )
        db_session.add(txn)
        db_session.commit()

        spending = get_budget_spending(db_session, sample_budget)
        assert spending["spent"] == 5400.0
        assert spending["percent_used"] == 108.0

    def test_excludes_income(self, db_session, sample_budget, sample_account):
        """Should only count expenses (negative amounts)."""
        expense = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-expense",
            date=date.today() - timedelta(days=1),
            amount=Decimal("-100.00"),
            raw_description="Expense",
            category_id=sample_budget.category_id,
            account_id=sample_account.id
        )
        income = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-income",
            date=date.today() - timedelta(days=1),
            amount=Decimal("500.00"),
            raw_description="Income",
            category_id=sample_budget.category_id,
            account_id=sample_account.id
        )
        db_session.add_all([expense, income])
        db_session.commit()

        spending = get_budget_spending(db_session, sample_budget)
        assert spending["spent"] == 100.0


class TestBudgetAlerts:
    """Test budget alert detection."""

    def test_no_alert_when_zero_spending(self, db_session, sample_budget):
        """Should not create alert when spending is 0%."""
        alert = check_budget_alerts(db_session, sample_budget.id)
        assert alert is None

    def test_no_alert_under_80_percent(self, db_session, sample_budget, sample_account):
        """Should not create alert when spending is under 80%."""
        amount = Decimal("-300.00")
        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-under-80",
            date=date.today() - timedelta(days=1),
            amount=amount,
            raw_description="Under 80%",
            category_id=sample_budget.category_id,
            account_id=sample_account.id
        )
        db_session.add(txn)
        db_session.commit()

        alert = check_budget_alerts(db_session, sample_budget.id)
        assert alert is None

    def test_creates_warning_at_80_percent(self, db_session, sample_budget, sample_account):
        """Should create warning alert at 80%."""
        amount = Decimal("-400.00")
        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-at-80",
            date=date.today() - timedelta(days=1),
            amount=amount,
            raw_description="At 80%",
            category_id=sample_budget.category_id,
            account_id=sample_account.id
        )
        db_session.add(txn)
        db_session.commit()

        alert = check_budget_alerts(db_session, sample_budget.id)
        assert alert is not None
        assert alert.type == AlertType.budget_warning
        assert alert.severity == Severity.warning
        assert alert.budget_id == sample_budget.id

    def test_creates_warning_at_99_percent(self, db_session, sample_budget, sample_account):
        """Should create warning alert at 99%."""
        amount = Decimal("-495.00")
        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-at-99",
            date=date.today() - timedelta(days=1),
            amount=amount,
            raw_description="At 99%",
            category_id=sample_budget.category_id,
            account_id=sample_account.id
        )
        db_session.add(txn)
        db_session.commit()

        alert = check_budget_alerts(db_session, sample_budget.id)
        assert alert is not None
        assert alert.type == AlertType.budget_warning
        assert alert.severity == Severity.warning

    def test_creates_exceeded_at_100_percent(self, db_session, sample_budget, sample_account):
        """Should create exceeded alert at 100%."""
        amount = Decimal("-500.00")
        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-at-100",
            date=date.today() - timedelta(days=1),
            amount=amount,
            raw_description="At 100%",
            category_id=sample_budget.category_id,
            account_id=sample_account.id
        )
        db_session.add(txn)
        db_session.commit()

        alert = check_budget_alerts(db_session, sample_budget.id)
        assert alert is not None
        assert alert.type == AlertType.budget_exceeded
        assert alert.severity == Severity.attention

    def test_creates_exceeded_at_150_percent(self, db_session, sample_budget, sample_account):
        """Should create exceeded alert at 150%."""
        amount = Decimal("-750.00")
        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-at-150",
            date=date.today() - timedelta(days=1),
            amount=amount,
            raw_description="At 150%",
            category_id=sample_budget.category_id,
            account_id=sample_account.id
        )
        db_session.add(txn)
        db_session.commit()

        alert = check_budget_alerts(db_session, sample_budget.id)
        assert alert is not None
        assert alert.type == AlertType.budget_exceeded
        assert alert.severity == Severity.attention

    def test_no_duplicate_warning_alerts(self, db_session, sample_budget, sample_account):
        """Should not create duplicate warning alerts."""
        # Create alert at 80%
        amount = Decimal("-400.00")
        txn1 = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-dup-1",
            date=date.today() - timedelta(days=1),
            amount=amount,
            raw_description="First alert",
            category_id=sample_budget.category_id,
            account_id=sample_account.id
        )
        db_session.add(txn1)
        db_session.commit()

        alert1 = check_budget_alerts(db_session, sample_budget.id)
        assert alert1 is not None

        # Check again at 80% - should not create duplicate
        alert2 = check_budget_alerts(db_session, sample_budget.id)
        assert alert2 is None

    def test_no_duplicate_exceeded_alerts(self, db_session, sample_budget, sample_account):
        """Should not create duplicate exceeded alerts."""
        # Create alert at 100%
        amount = Decimal("-500.00")
        txn1 = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-dup-2",
            date=date.today() - timedelta(days=1),
            amount=amount,
            raw_description="First exceeded",
            category_id=sample_budget.category_id,
            account_id=sample_account.id
        )
        db_session.add(txn1)
        db_session.commit()

        alert1 = check_budget_alerts(db_session, sample_budget.id)
        assert alert1 is not None
        assert alert1.type == AlertType.budget_exceeded

        # Add more spending to 120% - should not create new exceeded alert
        txn2 = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-dup-3",
            date=date.today() - timedelta(days=1),
            amount=Decimal("-100.00"),
            raw_description="More spending",
            category_id=sample_budget.category_id,
            account_id=sample_account.id
        )
        db_session.add(txn2)
        db_session.commit()

        alert2 = check_budget_alerts(db_session, sample_budget.id)
        assert alert2 is None

    def test_no_alert_when_disabled(self, db_session, sample_budget, sample_account, alert_settings):
        """Should not create alerts when alerts are disabled."""
        alert_settings.alerts_enabled = False
        db_session.commit()

        amount = Decimal("-400.00")
        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-disabled",
            date=date.today() - timedelta(days=1),
            amount=amount,
            raw_description="Disabled",
            category_id=sample_budget.category_id,
            account_id=sample_account.id
        )
        db_session.add(txn)
        db_session.commit()

        alert = check_budget_alerts(db_session, sample_budget.id)
        assert alert is None

    def test_inactive_budget_excluded(self, db_session, sample_budget, sample_account):
        """Should not create alerts for inactive budgets."""
        sample_budget.is_active = False
        db_session.commit()

        amount = Decimal("-100.00")
        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-inactive",
            date=date.today() - timedelta(days=1),
            amount=amount,
            raw_description="Inactive",
            category_id=sample_budget.category_id,
            account_id=sample_account.id
        )
        db_session.add(txn)
        db_session.commit()

        alert = check_budget_alerts(db_session, sample_budget.id)
        assert alert is None

    def test_nonexistent_budget_returns_none(self, db_session):
        """Should return None for nonexistent budget."""
        alert = check_budget_alerts(db_session, str(uuid.uuid4()))
        assert alert is None


class TestCheckAllBudgetAlerts:
    """Test checking all budgets."""

    def test_empty_when_no_budgets(self, db_session):
        """Should return empty list when no budgets exist."""
        alerts = check_all_budget_alerts(db_session)
        assert alerts == []

    def test_checks_all_active_budgets(self, db_session, sample_category, sample_account):
        """Should check all active budgets."""
        budget1 = Budget(
            id=str(uuid.uuid4()),
            category_id=sample_category.id,
            amount=Decimal("100.00"),
            period=BudgetPeriod.weekly,
            start_date=date.today() - timedelta(days=3),
            is_active=True
        )
        budget2 = Budget(
            id=str(uuid.uuid4()),
            category_id=sample_category.id,
            amount=Decimal("100.00"),
            period=BudgetPeriod.weekly,
            start_date=date.today() - timedelta(days=3),
            is_active=True
        )
        budget3 = Budget(
            id=str(uuid.uuid4()),
            category_id=sample_category.id,
            amount=Decimal("100.00"),
            period=BudgetPeriod.weekly,
            start_date=date.today() - timedelta(days=3),
            is_active=False
        )
        db_session.add_all([budget1, budget2, budget3])
        db_session.commit()

        amount = Decimal("-300.00")
        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-all",
            date=date.today() - timedelta(days=1),
            amount=amount,
            raw_description="All budgets",
            category_id=sample_category.id,
            account_id=sample_account.id
        )
        db_session.add(txn)
        db_session.commit()

        alerts = check_all_budget_alerts(db_session)
        assert len(alerts) == 2
        alert_types = {alert.type for alert in alerts}
        assert AlertType.budget_exceeded in alert_types

    def test_handles_multiple_budgets_separately(self, db_session, sample_category, sample_account):
        """Should create alerts for each budget that shares the same category spending."""
        budget1 = Budget(
            id=str(uuid.uuid4()),
            category_id=sample_category.id,
            amount=Decimal("100.00"),
            period=BudgetPeriod.weekly,
            start_date=date.today() - timedelta(days=3),
            is_active=True
        )
        # Second category with a higher amount so it is NOT exceeded
        other_category = Category(
            id=str(uuid.uuid4()),
            name="Other Category",
            color="#ff0000",
            icon="tag",
            is_system=True
        )
        db_session.add(other_category)
        db_session.flush()

        budget2 = Budget(
            id=str(uuid.uuid4()),
            category_id=other_category.id,
            amount=Decimal("100.00"),
            period=BudgetPeriod.weekly,
            start_date=date.today() - timedelta(days=3),
            is_active=True
        )
        db_session.add_all([budget1, budget2])
        db_session.commit()

        # Only exceed budget1's category
        txn1 = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-b1",
            date=date.today() - timedelta(days=1),
            amount=Decimal("-150.00"),
            raw_description="Budget 1 exceeded",
            category_id=sample_category.id,
            account_id=sample_account.id
        )
        db_session.add(txn1)
        db_session.commit()

        alerts = check_all_budget_alerts(db_session)
        assert len(alerts) == 1
        assert alerts[0].budget_id == str(budget1.id)


class TestBudgetAlertSummary:
    """Test budget alert summary query."""

    def test_empty_summary_for_no_budget(self, db_session):
        """Should return empty dict for no budget."""
        summary = get_budget_alert_summary(db_session, str(uuid.uuid4()))
        assert summary == {}

    def test_basic_summary(self, db_session, sample_budget, sample_account):
        """Should return basic summary for active budget."""
        amount = Decimal("-300.00")
        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-summary",
            date=date.today() - timedelta(days=1),
            amount=amount,
            raw_description="Summary test",
            category_id=sample_budget.category_id,
            account_id=sample_account.id
        )
        db_session.add(txn)
        db_session.commit()

        summary = get_budget_alert_summary(db_session, sample_budget.id)
        assert summary["budget_id"] == sample_budget.id
        assert summary["category_name"] == sample_budget.category.name
        assert summary["total_spent"] == 300.0
        assert summary["budget_limit"] == float(sample_budget.amount)
        assert summary["percent_used"] == 60.0
        assert summary["period"] == "weekly"

    def test_summary_with_recent_alerts(self, db_session, sample_budget, sample_account):
        """Should include recent alerts in summary."""
        amount = Decimal("-400.00")
        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-alerts",
            date=date.today() - timedelta(days=1),
            amount=amount,
            raw_description="Alert test",
            category_id=sample_budget.category_id,
            account_id=sample_account.id
        )
        db_session.add(txn)
        db_session.commit()

        # Create an alert
        alert = Alert(
            id=str(uuid.uuid4()),
            type=AlertType.budget_warning,
            severity=Severity.warning,
            title="Test Alert",
            description="Test description",
            budget_id=sample_budget.id,
            is_read=False
        )
        db_session.add(alert)
        db_session.commit()

        summary = get_budget_alert_summary(db_session, sample_budget.id)
        assert "recent_alerts" in summary
        assert len(summary["recent_alerts"]) == 1
        assert summary["recent_alerts"][0]["type"] == "budget_warning"
        assert summary["recent_alerts"][0]["is_read"] is False
