"""
Seed script for default categories.
"""

from app.database import SessionLocal
from app.models import Category
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


if __name__ == "__main__":
    seed_categories()
