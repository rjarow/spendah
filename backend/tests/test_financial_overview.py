"""Integration tests for the financial overview feature.

Tests the complete financial picture including:
- Net worth calculation with all account types
- Budget progress tracking with transactions
- Integration between net worth and budgeting features
"""

import pytest
from datetime import datetime, date
from decimal import Decimal

from app.models.account import Account, AccountType
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.budget import Budget, BudgetPeriod
from app.models.balance_history import BalanceHistory
from app.services.networth_service import get_networth_breakdown
from app.services.budget_service import get_all_budgets_progress
from hashlib import sha256
from sqlalchemy.orm import Session

def generate_transaction_hash(tx_id, account_id, amount, date, description):
    """Generate a hash for a transaction to prevent duplicates."""
    data = f"{tx_id}_{account_id}_{amount}_{date}_{description}".encode("utf-8")
    return sha256(data).hexdigest()[:64]



def test_financial_overview_with_all_account_types(db_session: Session):
    """Test that net worth correctly calculates balances from all account types."""
    # Create accounts of different types
    checking_account = Account(
        id=1,
        name="Checking",
        account_type=AccountType.checking,
        current_balance=Decimal("5000.00"),
        is_active=True
    )
    savings_account = Account(
        id=2,
        name="Savings",
        account_type=AccountType.savings,
        current_balance=Decimal("15000.00"),
        is_active=True
    )
    credit_account = Account(
        id=3,
        name="Credit Card",
        account_type=AccountType.credit_card,
        current_balance=Decimal("-2000.00"),
        is_active=True
    )
    investment_account = Account(
        id=4,
        name="Investments",
        account_type=AccountType.investment,
        current_balance=Decimal("25000.00"),
        is_active=True
    )
    loan_account = Account(
        id=5,
        name="Car Loan",
        account_type=AccountType.loan,
        current_balance=Decimal("-15000.00"),
        is_active=True
    )
    mortgage_account = Account(
        id=6,
        name="Mortgage",
        account_type=AccountType.mortgage,
        current_balance=Decimal("-250000.00"),
        is_active=True
    )
    cash_account = Account(
        id=7,
        name="Cash",
        account_type=AccountType.cash,
        current_balance=Decimal("500.00"),
        is_active=True
    )

    db_session.add_all([
        checking_account, savings_account, credit_account,
        investment_account, loan_account, mortgage_account, cash_account
    ])
    db_session.commit()

    # Get net worth breakdown
    breakdown = get_networth_breakdown(db_session)

    # Verify total net worth
    total_assets = breakdown['total_assets']
    total_liabilities = breakdown['total_liabilities']
    expected_net_worth = Decimal("5000.00") + Decimal("15000.00") - Decimal("2000.00") + Decimal("25000.00") - Decimal("15000.00") - Decimal("250000.00") + Decimal("500.00")
    assert breakdown['net_worth'] == expected_net_worth
    assert total_assets == Decimal("45500.00")  # 5000 + 15000 + 25000 + 500
    assert total_liabilities == Decimal("267000.00")  # 2000 + 15000 + 250000

    # Verify individual account breakdown
    assert str(checking_account.id) in [acc['id'] for acc in breakdown['accounts']]
    assert str(savings_account.id) in [acc['id'] for acc in breakdown['accounts']]
    assert str(credit_account.id) in [acc['id'] for acc in breakdown['accounts']]
    assert str(investment_account.id) in [acc['id'] for acc in breakdown['accounts']]
    assert str(loan_account.id) in [acc['id'] for acc in breakdown['accounts']]
    assert str(mortgage_account.id) in [acc['id'] for acc in breakdown['accounts']]
    assert str(cash_account.id) in [acc['id'] for acc in breakdown['accounts']]


def test_financial_overview_with_transaction_balances(db_session: Session):
    """Test net worth with transactions that affect account balances."""
    # Create account
    account = Account(
        id=1,
        name="Bank Account",
        account_type=AccountType.checking,
        current_balance=Decimal("1000.00"),
        is_active=True
    )
    db_session.add(account)
    db_session.commit()

    # Create transactions
    tx1 = Transaction(
        id=1,
        account_id=account.id,
        amount=Decimal("-100.00"),
        date=date(2024, 1, 15),
        raw_description="Grocery shopping",
        clean_merchant="Grocery Store",
        ai_categorized=False,
        hash=generate_transaction_hash(1, account.id, Decimal("-100.00"), date(2024, 1, 15), "Grocery shopping")
    )
    tx2 = Transaction(
        id=2,
        account_id=account.id,
        amount=Decimal("50.00"),
        date=date(2024, 1, 20),
        raw_description="Deposit",
        clean_merchant="Deposit",
        ai_categorized=False,
        hash=generate_transaction_hash(2, account.id, Decimal("50.00"), date(2024, 1, 20), "Deposit")
    )
    tx3 = Transaction(
        id=3,
        account_id=account.id,
        amount=Decimal("-200.00"),
        date=date(2024, 2, 5),
        raw_description="Gas",
        clean_merchant="Gas Station",
        ai_categorized=False,
        hash=generate_transaction_hash(3, account.id, Decimal("-200.00"), date(2024, 2, 5), "Gas")
    )

    db_session.add_all([tx1, tx2, tx3])
    db_session.commit()

    # Get net worth - should show calculated balance from transactions
    breakdown = get_networth_breakdown(db_session)

    # Starting balance 1000 - 100 + 50 - 200 = 750
    expected_balance = Decimal("750.00")
    assert breakdown['net_worth'] == expected_balance
    assert breakdown['accounts']['Bank Account']['current_balance'] == expected_balance


def test_financial_overview_with_snapshots(db_session: Session):
    """Test that net worth history shows balance progression."""
    # Create account
    account = Account(
        id=1,
        name="Savings",
        account_type=AccountType.savings,
        current_balance=Decimal("10000.00"),
        is_active=True
    )
    db_session.add(account)
    db_session.commit()

    # Create snapshots at different times
    snapshot1 = BalanceHistory(
        id=1,
        account_id=account.id,
        balance=Decimal("10000.00"),
        recorded_at=date(2024, 1, 1)
    )
    snapshot2 = BalanceHistory(
        id=2,
        account_id=account.id,
        balance=Decimal("11500.00"),
        recorded_at=date(2024, 2, 1)
    )
    snapshot3 = BalanceHistory(
        id=3,
        account_id=account.id,
        balance=Decimal("13000.00"),
        recorded_at=date(2024, 3, 1)
    )

    db_session.add_all([snapshot1, snapshot2, snapshot3])
    db_session.commit()

    # Get snapshots - should be ordered by date
    snapshots = db_session.query(BalanceHistory).order_by(BalanceHistory.recorded_at).all()

    assert len(snapshots) == 3
    assert snapshots[0].balance == Decimal("10000.00")
    assert snapshots[1].balance == Decimal("11500.00")
    assert snapshots[2].balance == Decimal("13000.00")


def test_budget_progress_with_transactions(db_session: Session):
    """Test that budget progress correctly reflects transaction categorization."""
    # Create categories
    category1 = Category(
        id=1,
        name="Food"
    )
    category2 = Category(
        id=2,
        name="Rent"
    )
    db_session.add_all([category1, category2])
    db_session.commit()

    # Create account
    account = Account(
        id=1,
        name="Account",
        account_type=AccountType.checking,
        current_balance=Decimal("1000.00"),
        is_active=True
    )
    db_session.add(account)
    db_session.commit()

    # Create transactions for Food category
    tx1 = Transaction(
        id=1,
        account_id=account.id,
        amount=Decimal("-150.00"),
        date=date(2024, 1, 10),
        raw_description="Groceries",
        clean_merchant="Grocery Store",
        category_id=category1.id,
        ai_categorized=False,
        hash=generate_transaction_hash(1, account.id, Decimal("-150.00"), date(2024, 1, 10), "Groceries")
    )
    tx2 = Transaction(
        id=2,
        account_id=account.id,
        amount=Decimal("-75.00"),
        date=date(2024, 1, 15),
        raw_description="Restaurant",
        clean_merchant="Restaurant",
        category_id=category1.id,
        ai_categorized=False,
        hash=generate_transaction_hash(2, account.id, Decimal("-75.00"), date(2024, 1, 15), "Restaurant")
    )

    # Create transaction for Rent category
    tx3 = Transaction(
        id=3,
        account_id=account.id,
        amount=Decimal("-1200.00"),
        date=date(2024, 1, 1),
        raw_description="Monthly rent",
        clean_merchant="Rent Payment",
        category_id=category2.id,
        ai_categorized=False,
        hash=generate_transaction_hash(3, account.id, Decimal("-1200.00"), date(2024, 1, 1), "Monthly rent")
    )

    db_session.add_all([tx1, tx2, tx3])
    db_session.commit()

    # Create budget for Food category
    budget = Budget(
        id=1,
        category_id=category1.id,
        amount=Decimal("500.00"),
        period=BudgetPeriod.monthly,
        start_date=datetime(2024, 1, 1)
    )
    db_session.add(budget)
    db_session.commit()

    # Get budget status
    budget_status = get_all_budgets_progress(db_session)

    # Verify Food budget has correct progress
    food_budget = next((b for b in budget_status if b['category_id'] == category1.id), None)
    assert food_budget is not None
    assert food_budget['spent'] == Decimal("225.00")
    assert food_budget['budgeted'] == Decimal("500.00")
    assert food_budget['remaining'] == Decimal("275.00")
    assert food_budget['percentage'] == 45.0  # 225/500 * 100

    # Verify Rent budget is tracked separately
    rent_budget = next((b for b in budget_status if b['category_id'] == category2.id), None)
    assert rent_budget is not None
    assert rent_budget['spent'] == Decimal("1200.00")
    assert rent_budget['budgeted'] == Decimal("1200.00")
    assert rent_budget['remaining'] == Decimal("0.00")
    assert rent_budget['percentage'] == 100.0


def test_financial_overview_integration_multiple_categories(db_session: Session):
    """Test that financial overview works across multiple categories and accounts."""
    # Create categories
    categories = [
        Category(id=1, name="Food"),
        Category(id=2, name="Transport"),
        Category(id=3, name="Entertainment"),
        Category(id=4, name="Salary"),
    ]
    db_session.add_all(categories)
    db_session.commit()

    # Create accounts
    checking = Account(id=1, name="Checking", account_type=AccountType.checking, current_balance=Decimal("1000.00"), is_active=True)
    savings = Account(id=2, name="Savings", account_type=AccountType.savings, current_balance=Decimal("5000.00"), is_active=True)
    db_session.add_all([checking, savings])
    db_session.commit()

    # Create transactions
    tx1 = Transaction(
        id=1,
        account_id=checking.id,
        amount=Decimal("-150.00"),
        date=date(2024, 1, 5),
        raw_description="Groceries",
        clean_merchant="Grocery Store",
        category_id=categories[0].id,
        ai_categorized=False,
        hash=generate_transaction_hash(1, checking.id, Decimal("-150.00"), date(2024, 1, 5), "Groceries")
    )
    tx2 = Transaction(
        id=2,
        account_id=checking.id,
        amount=Decimal("-50.00"),
        date=date(2024, 1, 10),
        raw_description="Gas",
        clean_merchant="Gas Station",
        category_id=categories[1].id,
        ai_categorized=False,
        hash=generate_transaction_hash(2, checking.id, Decimal("-50.00"), date(2024, 1, 10), "Gas")
    )
    tx3 = Transaction(
        id=3,
        account_id=checking.id,
        amount=Decimal("-100.00"),
        date=date(2024, 1, 12),
        raw_description="Movies",
        clean_merchant="Movie Theater",
        category_id=categories[2].id,
        ai_categorized=False,
        hash=generate_transaction_hash(3, checking.id, Decimal("-100.00"), date(2024, 1, 12), "Movies")
    )
    tx4 = Transaction(
        id=4,
        account_id=checking.id,
        amount=Decimal("4000.00"),
        date=date(2024, 1, 1),
        raw_description="Paycheck",
        clean_merchant="Paycheck",
        category_id=categories[3].id,
        ai_categorized=False,
        hash=generate_transaction_hash(4, checking.id, Decimal("4000.00"), date(2024, 1, 1), "Paycheck")
    )
    tx5 = Transaction(
        id=5,
        account_id=checking.id,
        amount=Decimal("-200.00"),
        date=date(2024, 1, 15),
        raw_description="Dinner",
        clean_merchant="Restaurant",
        category_id=categories[0].id,
        ai_categorized=False,
        hash=generate_transaction_hash(5, checking.id, Decimal("-200.00"), date(2024, 1, 15), "Dinner")
    )
    tx6 = Transaction(
        id=6,
        account_id=checking.id,
        amount=Decimal("-30.00"),
        date=date(2024, 1, 18),
        raw_description="Bus pass",
        clean_merchant="Bus",
        category_id=categories[1].id,
        ai_categorized=False,
        hash=generate_transaction_hash(6, checking.id, Decimal("-30.00"), date(2024, 1, 18), "Bus pass")
    )

    db_session.add_all([tx1, tx2, tx3, tx4, tx5, tx6])
    db_session.commit()

    # Create budgets
    budgets = [
        Budget(id=1, category_id=categories[0].id, amount=Decimal("400.00"), period=BudgetPeriod.monthly, start_date=datetime(2024, 1, 1)),
        Budget(id=2, category_id=categories[1].id, amount=Decimal("200.00"), period=BudgetPeriod.monthly, start_date=datetime(2024, 1, 1)),
        Budget(id=3, category_id=categories[2].id, amount=Decimal("150.00"), period=BudgetPeriod.monthly, start_date=datetime(2024, 1, 1)),
    ]
    db_session.add_all(budgets)
    db_session.commit()

    # Get financial overview
    breakdown = get_networth_breakdown(db_session)

    # Verify net worth
    total_spent = Decimal("-430.00")  # 150 + 50 + 100 + 200 + 30
    total_income = Decimal("4000.00")
    expected_net_worth = Decimal("1000.00") + Decimal("5000.00") + total_income + total_spent
    assert breakdown['net_worth'] == expected_net_worth

    # Verify budget progress
    budget_status = get_all_budgets_progress(db_session)

    # Food budget
    food = next((b for b in budget_status if b['category_id'] == categories[0].id), None)
    assert food is not None
    assert food['spent'] == Decimal("350.00")
    assert food['remaining'] == Decimal("50.00")
    assert food['percentage'] == 87.5

    # Transport budget
    transport = next((b for b in budget_status if b['category_id'] == categories[1].id), None)
    assert transport is not None
    assert transport['spent'] == Decimal("80.00")
    assert transport['remaining'] == Decimal("120.00")
    assert transport['percentage'] == 40.0

    # Entertainment budget
    entertainment = next((b for b in budget_status if b['category_id'] == categories[2].id), None)
    assert entertainment is not None
    assert entertainment['spent'] == Decimal("100.00")
    assert entertainment['remaining'] == Decimal("50.00")
    assert entertainment['percentage'] == 66.7


def test_financial_overview_with_stale_balances(db_session: Session):
    """Test handling of accounts where manual balance doesn't match transactions."""
    # Create account
    account = Account(
        id=1,
        name="Account",
        account_type=AccountType.checking,
        current_balance=Decimal("1000.00"),
        is_active=True
    )
    db_session.add(account)
    db_session.commit()

    # Create transaction
    tx = Transaction(
        id=1,
        account_id=account.id,
        amount=Decimal("-50.00"),
        date=date(2024, 1, 10),
        raw_description="Test transaction",
        clean_merchant="Test Merchant",
        ai_categorized=False,
        hash=generate_transaction_hash(1, account.id, Decimal("-50.00"), date(2024, 1, 10), "Test transaction")
    )
    db_session.add(tx)
    db_session.commit()

    # Get net worth - should show calculated balance
    breakdown = get_networth_breakdown(db_session)

    # Account should show calculated balance
    assert breakdown['accounts']['Account']['current_balance'] == Decimal("950.00")

    # Account should be flagged as stale
    account_data = breakdown['accounts']['Account']
    assert 'calculated_balance' in account_data
    assert account_data['calculated_balance'] == Decimal("950.00")
    assert account_data['is_stale'] is True


def test_financial_overview_empty_state(db_session: Session):
    """Test financial overview when no data exists."""
    # Don't create any accounts, transactions, or budgets
    # Just ensure API handles empty state gracefully

    # Get net worth - should be 0 or show no accounts
    breakdown = get_networth_breakdown(db_session)

    # Should have at least empty structure
    assert breakdown is not None
    assert 'total' in breakdown
    assert breakdown['net_worth'] == Decimal("0.00")
    assert 'accounts' in breakdown
    assert len(breakdown['accounts']) == 0

    # Get budget status - should be empty list
    budget_status = get_all_budgets_progress(db_session)
    assert budget_status == []


def test_financial_overview_heterogeneous_accounts(db_session: Session):
    """Test financial overview with a mix of asset and liability accounts."""
    # Create accounts
    asset1 = Account(id=1, name="Cash", account_type=AccountType.cash, current_balance=Decimal("500.00"), is_active=True)
    asset2 = Account(id=2, name="Stocks", account_type=AccountType.investment, current_balance=Decimal("10000.00"), is_active=True)
    liability1 = Account(id=3, name="Credit Card", account_type=AccountType.credit_card, current_balance=Decimal("-500.00"), is_active=True)
    liability2 = Account(id=4, name="Student Loan", account_type=AccountType.loan, current_balance=Decimal("-3000.00"), is_active=True)

    db_session.add_all([asset1, asset2, liability1, liability2])
    db_session.commit()

    # Get net worth
    breakdown = get_networth_breakdown(db_session)

    # Calculate expected
    expected_total = Decimal("500.00") + Decimal("10000.00") - Decimal("500.00") - Decimal("3000.00")
    assert breakdown['net_worth'] == expected_total

    # Verify separate asset and liability totals
    assert breakdown['total_assets'] == Decimal("10500.00")
    assert breakdown['total_liabilities'] == Decimal("3500.00")

    # Verify individual breakdown
    assert breakdown['accounts']['Cash']['current_balance'] == Decimal("500.00")
    assert breakdown['accounts']['Stocks']['current_balance'] == Decimal("10000.00")
    assert breakdown['accounts']['Credit Card']['current_balance'] == Decimal("-500.00")
    assert breakdown['accounts']['Student Loan']['current_balance'] == Decimal("-3000.00")


def test_financial_overview_transaction_deduplication(db_session: Session):
    """Test that duplicate transactions are handled correctly in financial overview."""
    # Create account
    account = Account(id=1, name="Checking", account_type=AccountType.checking, current_balance=Decimal("1000.00"), is_active=True)
    db_session.add(account)
    db_session.commit()

    # Create duplicate transaction
    tx = Transaction(
        id=1,
        account_id=account.id,
        amount=Decimal("-100.00"),
        date=date(2024, 1, 10),
        raw_description="Duplicate transaction",
        clean_merchant="Duplicate Merchant",
        ai_categorized=False,
        hash=generate_transaction_hash(1, account.id, Decimal("-100.00"), date(2024, 1, 10), "Duplicate transaction")
    )
    db_session.add(tx)
    db_session.commit()

    # Create another transaction with same details (simulating deduplication)
    tx2 = Transaction(
        id=2,
        account_id=account.id,
        amount=Decimal("-100.00"),
        date=date(2024, 1, 10),
        raw_description="Duplicate transaction",
        clean_merchant="Duplicate Merchant",
        ai_categorized=False,
        hash=generate_transaction_hash(2, account.id, Decimal("-100.00"), date(2024, 1, 10), "Duplicate transaction")
    )
    db_session.add(tx2)
    db_session.commit()

    # Get net worth
    breakdown = get_networth_breakdown(db_session)

    # Should handle duplicates - accounts should have consistent balance
    assert breakdown['accounts']['Checking']['current_balance'] == Decimal("900.00")
