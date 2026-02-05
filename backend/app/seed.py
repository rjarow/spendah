"""
Seed script for default categories and account balances.
"""

from app.database import SessionLocal
from app.models import Category, Account, BalanceHistory
from app.models.account import AccountType
from datetime import date, datetime
import uuid


def seed_categories():
    """Seed default categories into the database."""

    db = SessionLocal()

    try:
        # Check if categories already exist
        existing_count = db.query(Category).count()
        if existing_count > 0:
            print(f"Categories already seeded ({existing_count} categories exist)")
            return

        # Define default categories with their subcategories
        categories_data = [
            {
                "name": "Income",
                "color": "#10b981",
                "icon": "dollar-sign",
                "children": []
            },
            {
                "name": "Housing",
                "color": "#3b82f6",
                "icon": "home",
                "children": [
                    {"name": "Rent/Mortgage", "color": "#3b82f6", "icon": "key"},
                    {"name": "Utilities", "color": "#3b82f6", "icon": "zap"},
                    {"name": "Insurance", "color": "#3b82f6", "icon": "shield"},
                ]
            },
            {
                "name": "Transportation",
                "color": "#8b5cf6",
                "icon": "car",
                "children": [
                    {"name": "Gas", "color": "#8b5cf6", "icon": "fuel"},
                    {"name": "Auto Insurance", "color": "#8b5cf6", "icon": "shield-check"},
                    {"name": "Maintenance", "color": "#8b5cf6", "icon": "wrench"},
                    {"name": "Parking", "color": "#8b5cf6", "icon": "square-parking"},
                ]
            },
            {
                "name": "Food",
                "color": "#f59e0b",
                "icon": "utensils",
                "children": [
                    {"name": "Groceries", "color": "#f59e0b", "icon": "shopping-cart"},
                    {"name": "Restaurants", "color": "#f59e0b", "icon": "utensils-crossed"},
                    {"name": "Coffee", "color": "#f59e0b", "icon": "coffee"},
                ]
            },
            {
                "name": "Shopping",
                "color": "#ec4899",
                "icon": "shopping-bag",
                "children": [
                    {"name": "Clothing", "color": "#ec4899", "icon": "shirt"},
                    {"name": "Electronics", "color": "#ec4899", "icon": "laptop"},
                    {"name": "Home", "color": "#ec4899", "icon": "home"},
                ]
            },
            {
                "name": "Entertainment",
                "color": "#f43f5e",
                "icon": "tv",
                "children": [
                    {"name": "Streaming", "color": "#f43f5e", "icon": "play-circle"},
                    {"name": "Games", "color": "#f43f5e", "icon": "gamepad"},
                    {"name": "Events", "color": "#f43f5e", "icon": "ticket"},
                ]
            },
            {
                "name": "Health",
                "color": "#14b8a6",
                "icon": "heart-pulse",
                "children": [
                    {"name": "Medical", "color": "#14b8a6", "icon": "stethoscope"},
                    {"name": "Pharmacy", "color": "#14b8a6", "icon": "pills"},
                    {"name": "Fitness", "color": "#14b8a6", "icon": "dumbbell"},
                ]
            },
            {
                "name": "Personal",
                "color": "#6366f1",
                "icon": "user",
                "children": [
                    {"name": "Haircut", "color": "#6366f1", "icon": "scissors"},
                    {"name": "Education", "color": "#6366f1", "icon": "graduation-cap"},
                ]
            },
            {
                "name": "Travel",
                "color": "#06b6d4",
                "icon": "plane",
                "children": []
            },
            {
                "name": "Subscriptions",
                "color": "#a855f7",
                "icon": "repeat",
                "children": []
            },
            {
                "name": "Transfers",
                "color": "#64748b",
                "icon": "arrow-right-left",
                "children": []
            },
            {
                "name": "Fees",
                "color": "#ef4444",
                "icon": "alert-circle",
                "children": []
            },
            {
                "name": "Other",
                "color": "#9ca3af",
                "icon": "circle",
                "children": []
            },
        ]

        # Create categories
        for cat_data in categories_data:
            parent = Category(
                id=str(uuid.uuid4()),
                name=cat_data["name"],
                color=cat_data["color"],
                icon=cat_data["icon"],
                is_system=True
            )
            db.add(parent)
            db.flush()  # Get the parent ID

            # Create subcategories
            for child_data in cat_data["children"]:
                child = Category(
                    id=str(uuid.uuid4()),
                    name=child_data["name"],
                    color=child_data["color"],
                    icon=child_data["icon"],
                    parent_id=parent.id,
                    is_system=True
                )
                db.add(child)

        db.commit()
        print(f"Successfully seeded {len(categories_data)} parent categories with subcategories")

    except Exception as e:
        print(f"Error seeding categories: {e}")
        db.rollback()
    finally:
        db.close()


def seed_account_balances():
    """Seed initial account balances for development testing."""
    db = SessionLocal()

    try:
        # Check if accounts exist
        existing_accounts = db.query(Account).count()
        if existing_accounts == 0:
            print("No accounts found. Run account seed first.")
            return

        # Get existing accounts and set initial balances
        accounts = db.query(Account).filter(Account.is_active == True).all()

        print(f"Setting initial balances on {len(accounts)} accounts...")

        for account in accounts:
            if account.is_active:
                # Set different balances based on account type
                if account.account_type == AccountType.bank:
                    account.current_balance = 2500.00
                    account.balance_updated_at = datetime.utcnow()
                    print(f"  {account.name}: $2500.00")
                elif account.account_type == AccountType.credit:
                    account.current_balance = -1500.00
                    account.balance_updated_at = datetime.utcnow()
                    print(f"  {account.name}: -$1500.00")
                elif account.account_type == AccountType.cash:
                    account.current_balance = 500.00
                    account.balance_updated_at = datetime.utcnow()
                    print(f"  {account.name}: $500.00")
                else:
                    account.current_balance = 1000.00
                    account.balance_updated_at = datetime.utcnow()
                    print(f"  {account.name}: $1000.00")

        # Create some balance history snapshots for testing
        print("\nCreating balance history snapshots...")

        active_accounts = [acc for acc in accounts if acc.is_active]
        for account in active_accounts[:3]:  # Only snapshot first 3 accounts
            for i in range(5):  # Create 5 snapshots per account
                days_ago = 5 - i
                snapshot_date = date.today() - __import__('datetime').timedelta(days=days_ago)

                # Vary the balance slightly for each snapshot
                balance_offset = (5 - i) * 50
                if account.account_type == AccountType.credit:
                    balance = -(1500.00 + balance_offset)
                else:
                    balance = (2500.00 + balance_offset) if account.account_type == AccountType.bank else (500.00 + balance_offset)

                snapshot = BalanceHistory(
                    account_id=account.id,
                    balance=balance,
                    recorded_at=snapshot_date
                )
                db.add(snapshot)
                print(f"  {account.name} on {snapshot_date}: ${balance:.2f}")

        db.commit()
        print("\nSuccessfully seeded account balances and history")

    except Exception as e:
        print(f"Error seeding account balances: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_categories()
    seed_account_balances()
