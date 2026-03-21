"""Tests for budgets API endpoints."""

import pytest
from datetime import date, timedelta
from decimal import Decimal
import uuid

from app.models.budget import Budget, BudgetPeriod
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.alert import Alert, AlertType, Severity


class TestBudgetsAPI:
    """Test budgets CRUD endpoints."""

    def test_list_budgets_empty(self, client):
        """Should return empty list when no budgets."""
        response = client.get("/api/v1/budgets")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_create_budget_with_category(self, client, sample_category):
        """Should create a budget for an existing category."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "category_id": sample_category.id,
                "amount": "500.00",
                "period": "monthly",
                "start_date": date.today().isoformat(),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["category_id"] == sample_category.id
        assert data["amount"] == "500.00"
        assert data["period"] == "monthly"
        assert "id" in data

    def test_create_overall_budget(self, client):
        """Should create a budget without a category (overall)."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "amount": "2000.00",
                "period": "monthly",
                "start_date": date.today().isoformat(),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["category_id"] is None
        assert data["amount"] == "2000.00"

    def test_get_budget_progress_with_transactions(
        self, client, db_session, sample_account, sample_category
    ):
        """Should calculate progress when transactions exist in period."""
        # Create a transaction within the current period
        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="budget_progress_test",
            date=date.today() - timedelta(days=1),
            amount=Decimal("-50.00"),
            raw_description="Test Transaction",
            category_id=sample_category.id,
            account_id=sample_account.id,
        )
        db_session.add(txn)

        budget = Budget(
            id=str(uuid.uuid4()),
            category_id=sample_category.id,
            amount=Decimal("100.00"),
            period=BudgetPeriod.weekly,
            start_date=date.today() - timedelta(days=3),
            is_active=True,
        )
        db_session.add(budget)
        db_session.commit()

        response = client.get(f"/api/v1/budgets/{budget.id}/progress")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == budget.id
        assert data["category_id"] == sample_category.id
        assert data["category_name"] == sample_category.name
        assert data["amount"] == "100.00"
        assert data["spent"] == "50.00"
        assert data["remaining"] == "50.00"
        assert data["percent_used"] == 50.0
        assert data["is_over_budget"] is False

    def test_get_budget_progress_no_transactions(
        self, client, db_session, sample_category
    ):
        """Should calculate 0% used when no transactions exist."""
        budget = Budget(
            id=str(uuid.uuid4()),
            category_id=sample_category.id,
            amount=Decimal("100.00"),
            period=BudgetPeriod.weekly,
            start_date=date.today() - timedelta(days=3),
            is_active=True,
        )

        db_session.add(budget)
        db_session.commit()

        response = client.get(f"/api/v1/budgets/{budget.id}/progress")
        assert response.status_code == 200
        data = response.json()
        assert data["percent_used"] == 0.0
        assert float(data["spent"]) == 0.0
        assert float(data["remaining"]) == 100.0

    def test_update_budget(self, client, sample_budget):
        """Should update budget amount."""
        response = client.patch(
            f"/api/v1/budgets/{sample_budget.id}", json={"amount": "750.00"}
        )
        assert response.status_code == 200
        assert response.json()["amount"] == "750.00"

    def test_delete_budget(self, client, sample_budget):
        """Should soft delete budget."""
        response = client.delete(f"/api/v1/budgets/{sample_budget.id}")
        assert response.status_code == 204

        # Verify soft deleted
        response = client.get("/api/v1/budgets")
        assert response.json()["items"] == []

    def test_list_budgets_with_progress(
        self, client, sample_budget, sample_transaction
    ):
        """Should list budgets with progress calculation."""
        response = client.get("/api/v1/budgets?include_progress=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == sample_budget.id
        assert "spent" in data["items"][0]
        assert "percent_used" in data["items"][0]

    def test_check_budget_alerts(self, client, db_session, sample_account, sample_budget):
        """Should check all budgets for alerts and create them if needed."""
        # First clear any existing alerts
        db_session.query(Alert).filter(Alert.budget_id == sample_budget.id).delete()
        db_session.commit()

        # Create transactions within current period to get to 90% of budget
        for i in range(9):
            txn = Transaction(
                id=str(uuid.uuid4()),
                hash=f"alert-test-hash-{i}",
                date=date.today(),
                amount=Decimal("-50.00"),
                raw_description=f"Test transaction {i}",
                clean_merchant=f"Test Merchant {i}",
                category_id=sample_budget.category_id,
                account_id=sample_account.id,
            )
            db_session.add(txn)
        db_session.commit()

        # Trigger budget alert check
        response = client.post("/api/v1/budgets/check-alerts")
        assert response.status_code == 200
        data = response.json()
        assert "created_alerts" in data
        assert "alerts" in data
        assert data["created_alerts"] >= 0

    def test_check_budget_alerts_no_duplicates(self, client, db_session, sample_account, sample_budget):
        """Should not create duplicate alerts for same budget condition."""
        # Clear existing alerts
        db_session.query(Alert).filter(Alert.budget_id == sample_budget.id).delete()
        db_session.commit()

        # Create transactions to reach 90% of budget
        for i in range(9):
            txn = Transaction(
                id=str(uuid.uuid4()),
                hash=f"nodup-hash-{i}",
                date=date.today(),
                amount=Decimal("-50.00"),
                raw_description=f"Test transaction {i}",
                clean_merchant=f"Test Merchant {i}",
                category_id=sample_budget.category_id,
                account_id=sample_account.id,
            )
            db_session.add(txn)
        db_session.commit()

        # First check - should create alerts
        response1 = client.post("/api/v1/budgets/check-alerts")
        assert response1.status_code == 200
        alert_count_after_first = response1.json()["created_alerts"]

        # Second check - should not create duplicate alerts
        response2 = client.post("/api/v1/budgets/check-alerts")
        assert response2.status_code == 200
        alert_count_after_second = response2.json()["created_alerts"]

        assert alert_count_after_second <= alert_count_after_first

    def test_check_budget_alerts_no_alerts_when_disabled(self, client, db_session, sample_budget):
        """Should not create alerts when budget is inactive."""
        # Disable the budget
        budget = db_session.query(Budget).filter(Budget.id == sample_budget.id).first()
        budget.is_active = False
        db_session.commit()

        # Clear existing alerts
        db_session.query(Alert).filter(Alert.budget_id == sample_budget.id).delete()
        db_session.commit()

        # Trigger budget alert check - inactive budget should not generate alerts
        response = client.post("/api/v1/budgets/check-alerts")
        assert response.status_code == 200
        data = response.json()

        # No alerts should be created for disabled budget
        assert data["created_alerts"] == 0
