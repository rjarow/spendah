"""
Seed script for default categories and account balances.
"""

from app.database import SessionLocal
from app.models import Category, Account, BalanceHistory
from app.models.account import AccountType
from datetime import date, datetime
import uuid
from decimal import Decimal


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
                "llm_prompt": "salary, wages, paychecks, bonuses, freelance income, dividend payments, interest earned, refunds, reimbursements",
                "children": [],
            },
            {
                "name": "Housing",
                "color": "#3b82f6",
                "icon": "home",
                "llm_prompt": "rent, mortgage, property tax, home insurance, repairs, maintenance, HOA fees, home improvement",
                "children": [
                    {
                        "name": "Rent/Mortgage",
                        "color": "#3b82f6",
                        "icon": "key",
                        "llm_prompt": "rent payment, mortgage payment, property lease",
                    },
                    {
                        "name": "Utilities",
                        "color": "#3b82f6",
                        "icon": "zap",
                        "llm_prompt": "electric, gas, water, sewer, trash, internet, cable, phone bill",
                    },
                    {
                        "name": "Insurance",
                        "color": "#3b82f6",
                        "icon": "shield",
                        "llm_prompt": "home insurance, renters insurance, property insurance",
                    },
                ],
            },
            {
                "name": "Transportation",
                "color": "#8b5cf6",
                "icon": "car",
                "llm_prompt": "car, vehicle, auto, gas station, fuel, parking, tolls, public transit, uber, lyft, taxi, bus, train, subway",
                "children": [
                    {
                        "name": "Gas",
                        "color": "#8b5cf6",
                        "icon": "fuel",
                        "llm_prompt": "gas station, fuel, petrol, diesel, shell, chevron, exxon, bp, mobil",
                    },
                    {
                        "name": "Auto Insurance",
                        "color": "#8b5cf6",
                        "icon": "shield-check",
                        "llm_prompt": "car insurance, auto insurance, vehicle insurance",
                    },
                    {
                        "name": "Maintenance",
                        "color": "#8b5cf6",
                        "icon": "wrench",
                        "llm_prompt": "oil change, tire rotation, car repair, auto shop, mechanic, car wash",
                    },
                    {
                        "name": "Parking",
                        "color": "#8b5cf6",
                        "icon": "square-parking",
                        "llm_prompt": "parking garage, parking meter, parking lot, valet",
                    },
                ],
            },
            {
                "name": "Food",
                "color": "#f59e0b",
                "icon": "utensils",
                "llm_prompt": "food, dining, meals, restaurants, groceries, coffee, fast food, delivery",
                "children": [
                    {
                        "name": "Groceries",
                        "color": "#f59e0b",
                        "icon": "shopping-cart",
                        "llm_prompt": "grocery stores, supermarkets, whole foods, trader joes, kroger, safeway, walmart grocery, costco, food shopping",
                    },
                    {
                        "name": "Restaurants",
                        "color": "#f59e0b",
                        "icon": "utensils-crossed",
                        "llm_prompt": "restaurants, dining out, takeout, fast food, mcdonalds, chipotle, pizza, sushi, delivery, doordash, ubereats",
                    },
                    {
                        "name": "Coffee",
                        "color": "#f59e0b",
                        "icon": "coffee",
                        "llm_prompt": "starbucks, coffee shops, cafes, dunkin, peets, dutch bros, espresso",
                    },
                ],
            },
            {
                "name": "Shopping",
                "color": "#ec4899",
                "icon": "shopping-bag",
                "llm_prompt": "retail, stores, online shopping, amazon, target, walmart, purchases",
                "children": [
                    {
                        "name": "Clothing",
                        "color": "#ec4899",
                        "icon": "shirt",
                        "llm_prompt": "clothing stores, fashion, apparel, shoes, nike, adidas, gap, zara, h&m, department stores",
                    },
                    {
                        "name": "Electronics",
                        "color": "#ec4899",
                        "icon": "laptop",
                        "llm_prompt": "electronics, best buy, apple store, computer, phone, gadgets, tech",
                    },
                    {
                        "name": "Home",
                        "color": "#ec4899",
                        "icon": "home",
                        "llm_prompt": "home goods, furniture, ikea, target, bed bath, home decor, appliances",
                    },
                ],
            },
            {
                "name": "Entertainment",
                "color": "#f43f5e",
                "icon": "tv",
                "llm_prompt": "entertainment, movies, concerts, games, fun, leisure, hobbies",
                "children": [
                    {
                        "name": "Streaming",
                        "color": "#f43f5e",
                        "icon": "play-circle",
                        "llm_prompt": "netflix, hulu, disney+, hbo, spotify, apple music, streaming services, video on demand",
                    },
                    {
                        "name": "Games",
                        "color": "#f43f5e",
                        "icon": "gamepad",
                        "llm_prompt": "video games, steam, playstation, xbox, nintendo, game store, gaming",
                    },
                    {
                        "name": "Events",
                        "color": "#f43f5e",
                        "icon": "ticket",
                        "llm_prompt": "concerts, movies, theater, sports events, tickets, eventbrite, live entertainment",
                    },
                ],
            },
            {
                "name": "Health",
                "color": "#14b8a6",
                "icon": "heart-pulse",
                "llm_prompt": "healthcare, medical, doctor, hospital, dental, vision, wellness",
                "children": [
                    {
                        "name": "Medical",
                        "color": "#14b8a6",
                        "icon": "stethoscope",
                        "llm_prompt": "doctor visits, hospital, clinic, medical center, healthcare, urgent care, lab tests",
                    },
                    {
                        "name": "Pharmacy",
                        "color": "#14b8a6",
                        "icon": "pills",
                        "llm_prompt": "pharmacy, cvs, walgreens, prescriptions, medicine, drugstore",
                    },
                    {
                        "name": "Fitness",
                        "color": "#14b8a6",
                        "icon": "dumbbell",
                        "llm_prompt": "gym, fitness center, yoga, pilates, personal trainer, workout, exercise, gym membership",
                    },
                ],
            },
            {
                "name": "Personal",
                "color": "#6366f1",
                "icon": "user",
                "llm_prompt": "personal care, grooming, self-care, education, professional services",
                "children": [
                    {
                        "name": "Haircut",
                        "color": "#6366f1",
                        "icon": "scissors",
                        "llm_prompt": "hair salon, barber, haircut, hair styling, beauty salon, spa",
                    },
                    {
                        "name": "Education",
                        "color": "#6366f1",
                        "icon": "graduation-cap",
                        "llm_prompt": "courses, classes, tuition, books, learning, training, workshops, online courses",
                    },
                ],
            },
            {
                "name": "Travel",
                "color": "#06b6d4",
                "icon": "plane",
                "llm_prompt": "travel, flights, hotels, airbnb, vacation, airlines, booking, rental car, trip",
                "children": [],
            },
            {
                "name": "Subscriptions",
                "color": "#a855f7",
                "icon": "repeat",
                "llm_prompt": "monthly subscriptions, recurring payments, membership fees, software subscriptions, saas",
                "children": [],
            },
            {
                "name": "Transfers",
                "color": "#64748b",
                "icon": "arrow-right-left",
                "llm_prompt": "transfers between accounts, internal transfers, venmo, paypal, zelle, payment transfers",
                "children": [],
            },
            {
                "name": "Fees",
                "color": "#ef4444",
                "icon": "alert-circle",
                "llm_prompt": "bank fees, atm fees, overdraft fees, late fees, service charges, transaction fees",
                "children": [],
            },
            {
                "name": "Other",
                "color": "#9ca3af",
                "icon": "circle",
                "llm_prompt": "miscellaneous, uncategorized, other expenses that dont fit elsewhere",
                "children": [],
            },
        ]

        # Create categories
        for cat_data in categories_data:
            parent = Category(
                id=str(uuid.uuid4()),
                name=cat_data["name"],
                color=cat_data["color"],
                icon=cat_data["icon"],
                llm_prompt=cat_data.get("llm_prompt"),
                is_system=True,
            )
            db.add(parent)
            db.flush()

            for child_data in cat_data["children"]:
                child = Category(
                    id=str(uuid.uuid4()),
                    name=child_data["name"],
                    color=child_data["color"],
                    icon=child_data["icon"],
                    llm_prompt=child_data.get("llm_prompt"),
                    parent_id=parent.id,
                    is_system=True,
                )
                db.add(child)

        db.commit()
        print(
            f"Successfully seeded {len(categories_data)} parent categories with subcategories"
        )

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
                account_type_value = account.account_type.value
                if account_type_value == "checking":
                    account.current_balance = Decimal("2500.00")
                    account.balance_updated_at = datetime.utcnow()
                    print(f"  {account.name}: $2500.00")
                elif account_type_value == "savings":
                    account.current_balance = Decimal("3000.00")
                    account.balance_updated_at = datetime.utcnow()
                    print(f"  {account.name}: $3000.00")
                elif account_type_value == "credit_card":
                    account.current_balance = Decimal("-1500.00")
                    account.balance_updated_at = datetime.utcnow()
                    print(f"  {account.name}: -$1500.00")
                elif account_type_value == "cash":
                    account.current_balance = Decimal("500.00")
                    account.balance_updated_at = datetime.utcnow()
                    print(f"  {account.name}: $500.00")
                elif account_type_value == "investment":
                    account.current_balance = Decimal("10000.00")
                    account.balance_updated_at = datetime.utcnow()
                    print(f"  {account.name}: $10000.00")
                elif account_type_value in ["loan", "mortgage"]:
                    account.current_balance = Decimal("-8000.00")
                    account.balance_updated_at = datetime.utcnow()
                    print(f"  {account.name}: -$8000.00")
                else:
                    account.current_balance = Decimal("1000.00")
                    account.balance_updated_at = datetime.utcnow()
                    print(f"  {account.name}: $1000.00")

        # Create some balance history snapshots for testing
        print("\nCreating balance history snapshots...")

        active_accounts = [acc for acc in accounts if acc.is_active]
        for account in active_accounts[:3]:  # Only snapshot first 3 accounts
            for i in range(5):  # Create 5 snapshots per account
                days_ago = 5 - i
                snapshot_date = date.today() - __import__("datetime").timedelta(
                    days=days_ago
                )

                # Vary the balance slightly for each snapshot
                balance_offset = (5 - i) * 50
                account_type_value = account.account_type.value
                if account_type_value == "credit_card":
                    balance = Decimal("-1500.00") - balance_offset
                elif account_type_value == "checking":
                    balance = Decimal("2500.00") + balance_offset
                else:
                    balance = Decimal("500.00") + balance_offset

                snapshot = BalanceHistory(
                    account_id=account.id, balance=balance, recorded_at=snapshot_date
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
