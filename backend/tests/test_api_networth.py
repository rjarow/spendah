"""Tests for Net Worth API endpoints."""

import pytest
from datetime import date, timedelta
from decimal import Decimal
import uuid

from app.models.account import Account, AccountType
from app.models.balance_history import BalanceHistory


class TestNetWorthSummary:
    """Test net worth summary endpoint."""

    def test_get_net_worth_empty(self, client):
        """Should return zeros when no accounts."""
        response = client.get("/api/v1/networth")
        assert response.status_code == 200
        data = response.json()
        assert data["total_assets"] == 0
        assert data["total_liabilities"] == 0
        assert data["net_worth"] == 0

    def test_get_net_worth_with_accounts(self, client, db_session, sample_account):
        """Should calculate net worth from account balances."""
        sample_account.current_balance = Decimal("1000.00")
        db_session.commit()

        response = client.get("/api/v1/networth")
        assert response.status_code == 200
        data = response.json()
        assert data["total_assets"] == 1000.0
        assert data["net_worth"] == 1000.0


class TestNetWorthBreakdown:
    """Test net worth breakdown endpoint."""

    def test_get_breakdown_empty(self, client):
        """Should return empty breakdown when no accounts."""
        response = client.get("/api/v1/networth/breakdown")
        assert response.status_code == 200
        data = response.json()
        assert data["total_assets"] == 0
        assert data["total_liabilities"] == 0
        assert data["accounts"] == []

    def test_get_breakdown_with_accounts(self, client, db_session):
        """Should return breakdown with account details."""
        checking = Account(
            id=str(uuid.uuid4()),
            name="Checking",
            account_type=AccountType.checking,
            current_balance=Decimal("2000.00"),
            is_active=True,
        )
        credit_card = Account(
            id=str(uuid.uuid4()),
            name="Credit Card",
            account_type=AccountType.credit_card,
            current_balance=Decimal("-500.00"),
            is_active=True,
        )
        db_session.add_all([checking, credit_card])
        db_session.commit()

        response = client.get("/api/v1/networth/breakdown")
        assert response.status_code == 200
        data = response.json()
        assert data["total_assets"] == 2000.0
        assert data["total_liabilities"] == 500.0
        assert data["net_worth"] == 1500.0
        assert len(data["accounts"]) == 2

    def test_get_breakdown_excludes_inactive(self, client, db_session):
        """Should exclude inactive accounts from breakdown."""
        active = Account(
            id=str(uuid.uuid4()),
            name="Active",
            account_type=AccountType.checking,
            current_balance=Decimal("1000.00"),
            is_active=True,
        )
        inactive = Account(
            id=str(uuid.uuid4()),
            name="Inactive",
            account_type=AccountType.checking,
            current_balance=Decimal("5000.00"),
            is_active=False,
        )
        db_session.add_all([active, inactive])
        db_session.commit()

        response = client.get("/api/v1/networth/breakdown")
        assert response.status_code == 200
        data = response.json()
        assert data["total_assets"] == 1000.0
        assert len(data["accounts"]) == 1


class TestNetWorthHistory:
    """Test net worth history endpoint."""

    def test_get_history_empty(self, client):
        """Should return empty list when no history."""
        start_date = (date.today() - timedelta(days=365)).isoformat()
        response = client.get(f"/api/v1/networth/history?start_date={start_date}")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_get_history_with_snapshots(self, client, db_session, sample_account):
        """Should return history of balance snapshots."""
        today = date.today()

        for i in range(5):
            snapshot = BalanceHistory(
                id=str(uuid.uuid4()),
                account_id=sample_account.id,
                balance=Decimal(f"{1000 + i * 100}.00"),
                recorded_at=today - timedelta(days=i * 30),
            )
            db_session.add(snapshot)
        db_session.commit()

        start_date = (today - timedelta(days=365)).isoformat()
        response = client.get(f"/api/v1/networth/history?start_date={start_date}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        assert all("date" in item for item in data)
        assert all("net_worth" in item for item in data)

    def test_get_history_date_range(self, client, db_session, sample_account):
        """Should filter history by date range."""
        today = date.today()

        for i in range(10):
            snapshot = BalanceHistory(
                id=str(uuid.uuid4()),
                account_id=sample_account.id,
                balance=Decimal("1000.00"),
                recorded_at=today - timedelta(days=i * 30),
            )
            db_session.add(snapshot)
        db_session.commit()

        start_date = (today - timedelta(days=90)).isoformat()
        response = client.get(f"/api/v1/networth/history?start_date={start_date}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 4


class TestAutoSnapshot:
    """Test auto snapshot endpoint."""

    def test_auto_snapshot_creates_records(self, client, db_session, sample_account):
        """Should create balance snapshots for all accounts."""
        sample_account.current_balance = Decimal("1500.00")
        db_session.commit()

        response = client.post("/api/v1/networth/auto-snapshot")
        assert response.status_code == 200
        data = response.json()
        assert data["total_snapshots"] >= 1
        assert data["errors"] == 0

        snapshots = (
            db_session.query(BalanceHistory)
            .filter(BalanceHistory.account_id == sample_account.id)
            .all()
        )
        assert len(snapshots) == 1

    def test_auto_snapshot_multiple_accounts(self, client, db_session):
        """Should snapshot all active accounts."""
        for i in range(3):
            account = Account(
                id=str(uuid.uuid4()),
                name=f"Account {i}",
                account_type=AccountType.checking,
                current_balance=Decimal(f"{1000 * (i + 1)}.00"),
                is_active=True,
            )
            db_session.add(account)
        db_session.commit()

        response = client.post("/api/v1/networth/auto-snapshot")
        assert response.status_code == 200
        data = response.json()
        assert data["total_snapshots"] == 3


class TestUpdateBalance:
    """Test account balance update endpoint."""

    def test_update_balance(self, client, db_session, sample_account):
        """Should update account balance via query params."""
        response = client.post(
            f"/api/v1/accounts/{sample_account.id}/balance?current_balance=2500.00"
        )
        assert response.status_code == 200

        db_session.refresh(sample_account)
        assert float(sample_account.current_balance) == 2500.0

    def test_update_balance_creates_snapshot(self, client, db_session, sample_account):
        """Should create balance snapshot on update."""
        response = client.post(
            f"/api/v1/accounts/{sample_account.id}/balance?current_balance=3000.00"
        )
        assert response.status_code == 200

        snapshots = (
            db_session.query(BalanceHistory)
            .filter(BalanceHistory.account_id == sample_account.id)
            .all()
        )
        assert len(snapshots) >= 1

    def test_update_balance_invalid_account(self, client):
        """Should return 404 for non-existent account."""
        response = client.post(
            "/api/v1/accounts/nonexistent/balance?current_balance=1000.00"
        )
        assert response.status_code == 404
