"""Tests for Dashboard API endpoints."""

import pytest
from datetime import date, timedelta
from decimal import Decimal
import uuid

from app.models.budget import Budget, BudgetPeriod
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.account import Account, AccountType


class TestDashboardSummary:
    """Test dashboard summary endpoint."""

    def test_get_summary_empty(self, client):
        """Should return zeros when no transactions exist."""
        response = client.get("/api/v1/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_income"] == 0
        assert data["total_expenses"] == 0
        assert data["net"] == 0
        assert data["by_category"] == []

    def test_get_summary_with_transactions(
        self, client, db_session, sample_account, sample_category
    ):
        """Should calculate summary correctly with transactions."""
        today = date.today()

        income = Transaction(
            id=str(uuid.uuid4()),
            hash="income1",
            date=today,
            amount=Decimal("1000.00"),
            raw_description="PAYROLL",
            account_id=sample_account.id,
            is_recurring=False,
            ai_categorized=False,
        )
        expense = Transaction(
            id=str(uuid.uuid4()),
            hash="expense1",
            date=today,
            amount=Decimal("-50.00"),
            raw_description="GROCERY STORE",
            category_id=sample_category.id,
            account_id=sample_account.id,
            is_recurring=False,
            ai_categorized=False,
        )

        db_session.add_all([income, expense])
        db_session.commit()

        response = client.get("/api/v1/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_income"] == 1000.0
        assert data["total_expenses"] == 50.0
        assert data["net"] == 950.0
        assert len(data["by_category"]) == 1
        assert data["by_category"][0]["category_name"] == sample_category.name

    def test_get_summary_specific_month(
        self, client, db_session, sample_account, sample_category
    ):
        """Should filter by specific month."""
        last_month = date.today() - timedelta(days=35)

        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="old_txn",
            date=last_month,
            amount=Decimal("-100.00"),
            raw_description="OLD STORE",
            category_id=sample_category.id,
            account_id=sample_account.id,
            is_recurring=False,
            ai_categorized=False,
        )
        db_session.add(txn)
        db_session.commit()

        month_str = last_month.strftime("%Y-%m")
        response = client.get(f"/api/v1/dashboard/summary?month={month_str}")
        assert response.status_code == 200
        data = response.json()
        assert data["total_expenses"] == 100.0


class TestDashboardTrends:
    """Test dashboard trends endpoint."""

    def test_get_trends_empty(self, client):
        """Should return zeros for all months when no transactions."""
        response = client.get("/api/v1/dashboard/trends?months=6")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 6
        for month in data:
            assert month["income"] == 0
            assert month["expenses"] == 0
            assert month["net"] == 0

    def test_get_trends_with_data(self, client, db_session, sample_account):
        """Should return trends with correct calculations."""
        today = date.today()

        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="trend_txn",
            date=today,
            amount=Decimal("-100.00"),
            raw_description="STORE",
            account_id=sample_account.id,
            is_recurring=False,
            ai_categorized=False,
        )
        db_session.add(txn)
        db_session.commit()

        response = client.get("/api/v1/dashboard/trends?months=6")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 6

        current_month = today.strftime("%Y-%m")
        current_month_data = next(
            (m for m in data if m["month"] == current_month), None
        )
        assert current_month_data is not None
        assert current_month_data["expenses"] == 100.0

    def test_get_trends_custom_months(self, client):
        """Should respect months parameter."""
        response = client.get("/api/v1/dashboard/trends?months=12")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 12


class TestRecentTransactions:
    """Test recent transactions endpoint."""

    def test_get_recent_empty(self, client):
        """Should return empty list when no transactions."""
        response = client.get("/api/v1/dashboard/recent-transactions")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_get_recent_with_transactions(
        self, client, db_session, sample_account, sample_category
    ):
        """Should return transactions sorted by date desc."""
        for i in range(5):
            txn = Transaction(
                id=str(uuid.uuid4()),
                hash=f"recent_{i}",
                date=date.today() - timedelta(days=i),
                amount=Decimal("-10.00"),
                raw_description=f"STORE {i}",
                category_id=sample_category.id,
                account_id=sample_account.id,
                is_recurring=False,
                ai_categorized=False,
            )
            db_session.add(txn)
        db_session.commit()

        response = client.get("/api/v1/dashboard/recent-transactions?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["merchant"] == "STORE 0"

    def test_get_recent_uses_clean_merchant(self, client, db_session, sample_account):
        """Should prefer clean_merchant over raw_description."""
        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="clean_merchant_test",
            date=date.today(),
            amount=Decimal("-50.00"),
            raw_description="WHOLE FOODS MKT #12345",
            clean_merchant="Whole Foods",
            account_id=sample_account.id,
            is_recurring=False,
            ai_categorized=True,
        )
        db_session.add(txn)
        db_session.commit()

        response = client.get("/api/v1/dashboard/recent-transactions")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["merchant"] == "Whole Foods"
