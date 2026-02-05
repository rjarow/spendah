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
from app.services.balance_inference import (
    BalanceInferenceError,
    calculate_balance_from_transactions,
    get_balance_difference,
    get_accounts_with_stale_balances,
    infer_balance_from_transactions
)


class TestNetWorthCalculation:
    """Test net worth calculation functionality."""

    def test_get_current_networth_single_asset(self, db):
        """Calculate net worth with a single asset account."""
        account = Account(
            name="Checking Account",
            account_type=AccountType.checking,
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
            account_type=AccountType.checking,
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
            account_type=AccountType.checking,
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
            account_type=AccountType.checking,
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
            Account(name="Bank", account_type=AccountType.checking, current_balance=Decimal("3000.00")),
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
            account_type=AccountType.checking,
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
            account_type=AccountType.checking,
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
            account_type=AccountType.checking,
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
            account_type=AccountType.checking,
            current_balance=Decimal("1000.00")
        )
        account2 = Account(
            name="Account 2",
            account_type=AccountType.credit,
            current_balance=Decimal("-500.00")
        )
        inactive_account = Account(
            name="Inactive Account",
            account_type=AccountType.checking,
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
            account_type=AccountType.checking,
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
            account_type=AccountType.checking,
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
            account_type=AccountType.checking,
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
            account_type=AccountType.checking,
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


class TestBalanceInference:
    """Test balance inference from transactions."""

    def test_calculate_balance_from_transactions_bank_account(self, db_session):
        """Calculate balance for bank account from transactions."""
        import uuid
        from datetime import date
        from decimal import Decimal
        from app.models.transaction import Transaction

        account = Account(
            name="Bank Account",
            account_type=AccountType.checking,
            current_balance=Decimal("1000.00")
        )
        db_session.add(account)
        db_session.commit()

        # Add transactions: -50 (expense), +100 (income), -30 (expense)
        transaction1 = Transaction(
            id=str(uuid.uuid4()),
            hash=str(uuid.uuid4()),
            date=date.today(),
            amount=Decimal("-50.00"),
            raw_description="Purchase",
            clean_merchant="Grocery Store",
            account_id=account.id
        )
        transaction2 = Transaction(
            id=str(uuid.uuid4()),
            hash=str(uuid.uuid4()),
            date=date.today(),
            amount=Decimal("100.00"),
            raw_description="Deposit",
            clean_merchant="Salary",
            account_id=account.id
        )
        transaction3 = Transaction(
            id=str(uuid.uuid4()),
            hash=str(uuid.uuid4()),
            date=date.today(),
            amount=Decimal("-30.00"),
            raw_description="Purchase",
            clean_merchant="Gas Station",
            account_id=account.id
        )

        db_session.add_all([transaction1, transaction2, transaction3])
        db_session.commit()

        calculated = calculate_balance_from_transactions(db_session, account.id)

        expected = Decimal("1000.00") + Decimal("-50.00") + Decimal("100.00") + Decimal("-30.00")
        assert calculated == expected

    def test_calculate_balance_from_transactions_credit_account(self, db_session):
        """Calculate balance for credit account from transactions."""
        import uuid
        from datetime import date
        from decimal import Decimal
        from app.models.transaction import Transaction

        account = Account(
            name="Credit Card",
            account_type=AccountType.credit,
            current_balance=None
        )
        db_session.add(account)
        db_session.commit()

        # Add transactions: -100 (charge), -200 (charge)
        transaction1 = Transaction(
            id=str(uuid.uuid4()),
            hash=str(uuid.uuid4()),
            date=date.today(),
            amount=Decimal("-100.00"),
            raw_description="Charge",
            clean_merchant="Restaurant",
            account_id=account.id
        )
        transaction2 = Transaction(
            id=str(uuid.uuid4()),
            hash=str(uuid.uuid4()),
            date=date.today(),
            amount=Decimal("-200.00"),
            raw_description="Charge",
            clean_merchant="Online Shopping",
            account_id=account.id
        )

        db_session.add_all([transaction1, transaction2])
        db_session.commit()

        calculated = calculate_balance_from_transactions(db_session, account.id)

        expected = Decimal("-100.00") + Decimal("-200.00")
        assert calculated == expected

    def test_calculate_balance_from_transactions_cash_account(self, db_session):
        """Calculate balance for cash account from transactions."""
        import uuid
        from datetime import date
        from decimal import Decimal
        from app.models.transaction import Transaction

        account = Account(
            name="Cash Wallet",
            account_type=AccountType.cash,
            current_balance=Decimal("50.00")
        )
        db_session.add(account)
        db_session.commit()

        # Add transactions
        transaction1 = Transaction(
            id=str(uuid.uuid4()),
            hash=str(uuid.uuid4()),
            date=date.today(),
            amount=Decimal("-15.00"),
            raw_description="Purchase",
            clean_merchant="Coffee Shop",
            account_id=account.id
        )
        transaction2 = Transaction(
            id=str(uuid.uuid4()),
            hash=str(uuid.uuid4()),
            date=date.today(),
            amount=Decimal("20.00"),
            raw_description="Deposit",
            clean_merchant="Cash from bank",
            account_id=account.id
        )

        db_session.add_all([transaction1, transaction2])
        db_session.commit()

        calculated = calculate_balance_from_transactions(db_session, account.id)

        expected = Decimal("50.00") + Decimal("-15.00") + Decimal("20.00")
        assert calculated == expected

    def test_calculate_balance_from_transactions_no_current_balance(self, db_session):
        """Calculate balance when account has no current balance."""
        import uuid
        from datetime import date
        from decimal import Decimal
        from app.models.transaction import Transaction

        account = Account(
            name="New Account",
            account_type=AccountType.checking,
            current_balance=None
        )
        db_session.add(account)
        db_session.commit()

        # Add transactions only
        transaction1 = Transaction(
            id=str(uuid.uuid4()),
            hash=str(uuid.uuid4()),
            date=date.today(),
            amount=Decimal("-100.00"),
            raw_description="Purchase",
            clean_merchant="Store",
            account_id=account.id
        )

        db_session.add(transaction1)
        db_session.commit()

        calculated = calculate_balance_from_transactions(db_session, account.id)

        expected = Decimal("-100.00")
        assert calculated == expected

    def test_calculate_balance_from_transactions_no_transactions(self, db_session):
        """Calculate balance when account has no transactions."""
        import uuid
        from decimal import Decimal

        account = Account(
            name="Empty Account",
            account_type=AccountType.checking,
            current_balance=Decimal("500.00")
        )
        db_session.add(account)
        db_session.commit()

        calculated = calculate_balance_from_transactions(db_session, account.id)

        expected = Decimal("500.00")
        assert calculated == expected

    def test_get_balance_difference_stale_balance(self, db_session):
        """Get balance difference when manual balance differs from calculated."""
        import uuid
        from datetime import date
        from decimal import Decimal
        from app.models.transaction import Transaction

        account = Account(
            name="Stale Balance Account",
            account_type=AccountType.checking,
            current_balance=Decimal("1000.00")
        )
        db_session.add(account)
        db_session.commit()

        # Add transactions that change the balance
        transaction1 = Transaction(
            id=str(uuid.uuid4()),
            hash=str(uuid.uuid4()),
            date=date.today(),
            amount=Decimal("-50.00"),
            raw_description="Purchase",
            clean_merchant="Store",
            account_id=account.id
        )

        db_session.add(transaction1)
        db_session.commit()

        diff = get_balance_difference(db_session, account.id)

        assert diff["manual_balance"] == 1000.00
        assert diff["calculated_balance"] == 950.00
        assert diff["difference"] == -50.00
        assert diff["is_stale"] is True

    def test_get_balance_difference_current_balance(self, db_session):
        """Get balance difference when manual balance matches calculated."""
        import uuid
        from datetime import date
        from decimal import Decimal
        from app.models.transaction import Transaction

        account = Account(
            name="Current Balance Account",
            account_type=AccountType.checking,
            current_balance=Decimal("1000.00")
        )
        db_session.add(account)
        db_session.commit()

        diff = get_balance_difference(db_session, account.id)

        assert diff["manual_balance"] == 1000.00
        assert diff["calculated_balance"] == 1000.00
        assert diff["difference"] == 0.00
        assert diff["is_stale"] is False

    def test_get_balance_difference_invalid_account(self, db_session):
        """Get balance difference for non-existent account."""
        with pytest.raises(BalanceInferenceError):
            get_balance_difference(db_session, "non-existent-id")

    def test_get_accounts_with_stale_balances(self, db_session):
        """Get all accounts with stale balances."""
        import uuid
        from datetime import date
        from decimal import Decimal
        from app.models.transaction import Transaction

        account1 = Account(
            name="Stale Account",
            account_type=AccountType.checking,
            current_balance=Decimal("1000.00")
        )
        account2 = Account(
            name="Current Account",
            account_type=AccountType.checking,
            current_balance=Decimal("500.00")
        )
        account3 = Account(
            name="Inactive Account",
            account_type=AccountType.checking,
            current_balance=Decimal("200.00"),
            is_active=False
        )
        account4 = Account(
            name="Credit Card",
            account_type=AccountType.credit,
            current_balance=Decimal("-300.00")
        )

        db_session.add_all([account1, account2, account3, account4])
        db_session.commit()

        # Add transactions to account1 to make it stale
        transaction1 = Transaction(
            id=str(uuid.uuid4()),
            hash=str(uuid.uuid4()),
            date=date.today(),
            amount=Decimal("-50.00"),
            raw_description="Purchase",
            clean_merchant="Store",
            account_id=account1.id
        )
        db_session.add(transaction1)
        db_session.commit()

        stale_accounts = get_accounts_with_stale_balances(db_session)

        assert len(stale_accounts) == 2
        assert stale_accounts[0]["name"] == "Stale Account"
        assert stale_accounts[0]["is_stale"] is True

    def test_infer_balance_from_transactions(self, db_session):
        """Infer and update balance from transactions."""
        import uuid
        from datetime import date
        from decimal import Decimal
        from app.models.transaction import Transaction

        account = Account(
            name="Test Account",
            account_type=AccountType.checking,
            current_balance=Decimal("1000.00")
        )
        db_session.add(account)
        db_session.commit()

        # Add transactions
        transaction1 = Transaction(
            id=str(uuid.uuid4()),
            hash=str(uuid.uuid4()),
            date=date.today(),
            amount=Decimal("-50.00"),
            raw_description="Purchase",
            clean_merchant="Store",
            account_id=account.id
        )
        transaction2 = Transaction(
            id=str(uuid.uuid4()),
            hash=str(uuid.uuid4()),
            date=date.today(),
            amount=Decimal("200.00"),
            raw_description="Deposit",
            clean_merchant="Salary",
            account_id=account.id
        )

        db_session.add_all([transaction1, transaction2])
        db_session.commit()

        # Infer the balance from transactions
        new_balance = infer_balance_from_transactions(db_session, account.id)

        expected = Decimal("1000.00") + Decimal("-50.00") + Decimal("200.00")
        assert new_balance == expected

        # Verify the account was updated
        db_session.refresh(account)
        assert account.current_balance == expected

    def test_get_networth_breakdown_with_calculated_balance(self, db_session):
        """Test that net worth breakdown includes calculated balances."""
        import uuid
        from datetime import date
        from decimal import Decimal
        from app.models.transaction import Transaction

        account1 = Account(
            name="Stale Asset Account",
            account_type=AccountType.checking,
            current_balance=Decimal("1000.00")
        )
        account2 = Account(
            name="Current Asset Account",
            account_type=AccountType.cash,
            current_balance=Decimal("500.00")
        )
        account3 = Account(
            name="Credit Card",
            account_type=AccountType.credit,
            current_balance=Decimal("-300.00")
        )

        db_session.add_all([account1, account2, account3])
        db_session.commit()

        # Add transaction to account1 to make it stale
        transaction1 = Transaction(
            id=str(uuid.uuid4()),
            hash=str(uuid.uuid4()),
            date=date.today(),
            amount=Decimal("-50.00"),
            raw_description="Purchase",
            clean_merchant="Store",
            account_id=account1.id
        )
        db_session.add(transaction1)
        db_session.commit()

        breakdown = get_networth_breakdown(db_session)

        assert breakdown["total_assets"] == 1000.00 + 500.00
        assert breakdown["total_liabilities"] == 300.00
        assert breakdown["net_worth"] == 1200.00

        # Verify accounts data includes calculated_balance and is_stale
        account1_data = next((a for a in breakdown["accounts"] if a["name"] == "Stale Asset Account"), None)
        assert account1_data is not None
        assert account1_data["current_balance"] == 1000.00
        assert account1_data.get("calculated_balance") == 950.00
        assert account1_data["is_stale"] is True
