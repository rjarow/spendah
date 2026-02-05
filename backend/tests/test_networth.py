"""Tests for net worth functionality."""

import pytest
from datetime import date, datetime
from decimal import Decimal

from app.models.account import Account, AccountType
from app.models.balance_history import BalanceHistory
from app.services.networth_service import (
    get_current_networth,
    get_networth_breakdown,
    record_balance_snapshot,
    get_networth_history,
    auto_snapshot_all_balances,
    NetWorthError
)


class TestNetWorthCalculation:
    """Test net worth calculation functionality."""

    def test_get_current_networth_single_asset(self, db):
        """Calculate net worth with a single asset account."""
        account = Account(
            name="Checking Account",
            account_type=AccountType.bank,
            current_balance=Decimal("1000.00")
        )
        db.add(account)
        db.commit()

        net_worth = get_current_networth(db)
        assert net_worth == Decimal("1000.00")

    def test_get_current_networth_single_liability(self, db):
        """Calculate net worth with a single liability account."""
        account = Account(
            name="Credit Card",
            account_type=AccountType.credit,
            current_balance=Decimal("-500.00")
        )
        db.add(account)
        db.commit()

        net_worth = get_current_networth(db)
        assert net_worth == Decimal("-500.00")

    def test_get_current_networth_mixed(self, db):
        """Calculate net worth with multiple asset and liability accounts."""
        asset1 = Account(
            name="Bank Account",
            account_type=AccountType.bank,
            current_balance=Decimal("2000.00")
        )
        asset2 = Account(
            name="Cash Wallet",
            account_type=AccountType.cash,
            current_balance=Decimal("500.00")
        )
        liability1 = Account(
            name="Credit Card",
            account_type=AccountType.credit,
            current_balance=Decimal("-1000.00")
        )
        liability2 = Account(
            name="Student Loan",
            account_type=AccountType.other,
            current_balance=Decimal("-2000.00")
        )

        db.add_all([asset1, asset2, liability1, liability2])
        db.commit()

        net_worth = get_current_networth(db)
        expected = Decimal("2000.00") + Decimal("500.00") - Decimal("1000.00") - Decimal("2000.00")
        assert net_worth == expected

    def test_get_current_networth_zero_balances(self, db):
        """Calculate net worth with all zero balances."""
        account = Account(
            name="Empty Account",
            account_type=AccountType.bank,
            current_balance=Decimal("0.00")
        )
        db.add(account)
        db.commit()

        net_worth = get_current_networth(db)
        assert net_worth == Decimal("0.00")


class TestNetWorthBreakdown:
    """Test net worth breakdown functionality."""

    def test_get_networth_breakdown_single_account(self, db):
        """Get breakdown with a single account."""
        account = Account(
            name="Checking Account",
            account_type=AccountType.bank,
            current_balance=Decimal("1000.00")
        )
        db.add(account)
        db.commit()

        breakdown = get_networth_breakdown(db)

        assert breakdown["total_assets"] == 1000.00
        assert breakdown["total_liabilities"] == 0.00
        assert breakdown["net_worth"] == 1000.00
        assert len(breakdown["accounts"]) == 1
        assert breakdown["accounts"][0]["name"] == "Checking Account"

    def test_get_networth_breakdown_mixed_accounts(self, db):
        """Get breakdown with mixed account types."""
        assets = [
            Account(name="Bank", account_type=AccountType.bank, current_balance=Decimal("3000.00")),
            Account(name="Cash", account_type=AccountType.cash, current_balance=Decimal("500.00")),
            Account(name="Savings", account_type=AccountType.debit, current_balance=Decimal("1500.00"))
        ]
        liabilities = [
            Account(name="Credit Card", account_type=AccountType.credit, current_balance=Decimal("-1000.00")),
            Account(name="Loan", account_type=AccountType.other, current_balance=Decimal("-2000.00"))
        ]

        db.add_all(assets + liabilities)
        db.commit()

        breakdown = get_networth_breakdown(db)

        assert breakdown["total_assets"] == 5000.00
        assert breakdown["total_liabilities"] == 3000.00
        assert breakdown["net_worth"] == 2000.00
        assert len(breakdown["accounts"]) == 5


class TestBalanceHistory:
    """Test balance history recording."""

    def test_record_balance_snapshot(self, db):
        """Record a single balance snapshot."""
        account = Account(
            name="Test Account",
            account_type=AccountType.bank,
            current_balance=Decimal("1000.00")
        )
        db.add(account)
        db.commit()

        snapshot = record_balance_snapshot(db, account.id, Decimal("1000.00"), date.today())

        assert snapshot is not None
        assert snapshot.account_id == account.id
        assert snapshot.balance == Decimal("1000.00")
        assert snapshot.recorded_at == date.today()

        # Verify it was saved to DB
        saved = db.query(BalanceHistory).filter(BalanceHistory.id == snapshot.id).first()
        assert saved is not None

    def test_record_balance_snapshot_default_date(self, db):
        """Record balance snapshot with default date."""
        account = Account(
            name="Test Account",
            account_type=AccountType.bank,
            current_balance=Decimal("1000.00")
        )
        db.add(account)
        db.commit()

        snapshot = record_balance_snapshot(db, account.id, Decimal("1000.00"))

        assert snapshot.recorded_at == date.today()

    def test_record_balance_snapshot_invalid_account(self, db):
        """Record balance snapshot for non-existent account."""
        with pytest.raises(NetWorthError):
            record_balance_snapshot(db, "non-existent-id", Decimal("1000.00"))

    def test_record_balance_snapshot_different_dates(self, db):
        """Record balance snapshots on different dates."""
        account = Account(
            name="Test Account",
            account_type=AccountType.bank,
            current_balance=Decimal("1000.00")
        )
        db.add(account)
        db.commit()

        snapshot1 = record_balance_snapshot(db, account.id, Decimal("1000.00"), date(2024, 1, 1))
        snapshot2 = record_balance_snapshot(db, account.id, Decimal("1500.00"), date(2024, 1, 15))

        assert snapshot1.recorded_at == date(2024, 1, 1)
        assert snapshot2.recorded_at == date(2024, 1, 15)

    def test_auto_snapshot_all_balances(self, db):
        """Record snapshots for all active accounts."""
        account1 = Account(
            name="Account 1",
            account_type=AccountType.bank,
            current_balance=Decimal("1000.00")
        )
        account2 = Account(
            name="Account 2",
            account_type=AccountType.credit,
            current_balance=Decimal("-500.00")
        )
        inactive_account = Account(
            name="Inactive Account",
            account_type=AccountType.bank,
            current_balance=Decimal("200.00"),
            is_active=False
        )

        db.add_all([account1, account2, inactive_account])
        db.commit()

        result = auto_snapshot_all_balances(db)

        assert result["total_snapshots"] == 2
        assert result["errors"] == 0

        # Verify snapshots were created
        snapshots = db.query(BalanceHistory).all()
        assert len(snapshots) == 2


class TestNetWorthHistory:
    """Test net worth history functionality."""

    def test_get_networth_history_empty(self, db):
        """Get history when no snapshots exist."""
        history = get_networth_history(db, date(2024, 1, 1), date(2024, 12, 31))

        assert history == []

    def test_get_networth_history_with_snapshots(self, db):
        """Get history when snapshots exist."""
        account = Account(
            name="Test Account",
            account_type=AccountType.bank,
            current_balance=Decimal("1000.00")
        )
        db.add(account)
        db.commit()

        # Create snapshots on different dates
        record_balance_snapshot(db, account.id, Decimal("1000.00"), date(2024, 1, 1))
        record_balance_snapshot(db, account.id, Decimal("1500.00"), date(2024, 6, 1))
        record_balance_snapshot(db, account.id, Decimal("1200.00"), date(2024, 12, 1))

        history = get_networth_history(db, date(2024, 1, 1), date(2024, 12, 31))

        assert len(history) == 3
        assert history[0]["date"] == "2024-01-01"
        assert history[0]["net_worth"] == 1000.00
        assert history[1]["date"] == "2024-06-01"
        assert history[1]["net_worth"] == 1500.00
        assert history[2]["date"] == "2024-12-01"
        assert history[2]["net_worth"] == 1200.00

    def test_get_networth_history_single_date(self, db):
        """Get history for a single date."""
        account = Account(
            name="Test Account",
            account_type=AccountType.bank,
            current_balance=Decimal("1000.00")
        )
        db.add(account)
        db.commit()

        record_balance_snapshot(db, account.id, Decimal("1000.00"), date(2024, 6, 1))

        history = get_networth_history(db, date(2024, 6, 1), date(2024, 6, 1))

        assert len(history) == 1
        assert history[0]["date"] == "2024-06-01"
        assert history[0]["net_worth"] == 1000.00

    def test_get_networth_history_no_data_range(self, db):
        """Get history outside of snapshot dates."""
        account = Account(
            name="Test Account",
            account_type=AccountType.bank,
            current_balance=Decimal("1000.00")
        )
        db.add(account)
        db.commit()

        record_balance_snapshot(db, account.id, Decimal("1000.00"), date(2024, 6, 1))

        history = get_networth_history(db, date(2023, 1, 1), date(2023, 12, 31))

        assert history == []

    def test_get_networth_history_mixed_accounts(self, db):
        """Get history with multiple accounts."""
        asset = Account(
            name="Asset",
            account_type=AccountType.bank,
            current_balance=Decimal("2000.00")
        )
        liability = Account(
            name="Liability",
            account_type=AccountType.credit,
            current_balance=Decimal("-1000.00")
        )
        db.add_all([asset, liability])
        db.commit()

        # Record snapshots
        record_balance_snapshot(db, asset.id, Decimal("2000.00"), date(2024, 1, 1))
        record_balance_snapshot(db, liability.id, Decimal("-1000.00"), date(2024, 1, 1))

        history = get_networth_history(db, date(2024, 1, 1), date(2024, 12, 31))

        assert len(history) == 1
        assert history[0]["net_worth"] == 1000.00
