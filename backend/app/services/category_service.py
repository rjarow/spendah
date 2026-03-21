"""
Category service layer.
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)


class CategoryService:
    """Service for category operations."""

    def __init__(self, db: Session):
        self.db = db

    def list_categories(self) -> List[Category]:
        """List all categories."""
        return self.db.query(Category).all()

    def build_category_tree(self, categories: List[Category]) -> List[Dict[str, Any]]:
        """
        Build a hierarchical tree structure from flat category list.

        Args:
            categories: List of Category objects

        Returns:
            List of category dictionaries with children nested
        """
        category_map = {str(cat.id): self._category_to_dict(cat) for cat in categories}

        root_categories = []
        for cat_dict in category_map.values():
            if cat_dict.get("parent_id") is None:
                root_categories.append(cat_dict)
            else:
                parent = category_map.get(cat_dict["parent_id"])
                if parent:
                    parent["children"].append(cat_dict)

        return root_categories

    def _category_to_dict(self, category: Category) -> Dict[str, Any]:
        """Convert a Category object to a dictionary."""
        return {
            "id": str(category.id),
            "name": category.name,
            "parent_id": str(category.parent_id) if category.parent_id else None,
            "color": category.color,
            "icon": category.icon,
            "is_system": category.is_system,
            "created_at": category.created_at.isoformat()
            if category.created_at
            else None,
            "children": [],
        }

    def get_category(self, category_id: str) -> Optional[Category]:
        """Get a single category by ID."""
        return self.db.query(Category).filter(Category.id == category_id).first()

    def create_category(
        self,
        name: str,
        parent_id: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> Category:
        """
        Create a new category.

        Args:
            name: Category name
            parent_id: Optional parent category ID
            color: Optional hex color code
            icon: Optional icon name

        Returns:
            Created Category object

        Raises:
            ValueError: If parent category not found
        """
        if parent_id:
            parent = self.get_category(parent_id)
            if not parent:
                raise ValueError("Parent category not found")

        category = Category(
            name=name, parent_id=parent_id, color=color, icon=icon, is_system=False
        )
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)

        logger.info(f"Created category: {name}")
        return category

    def update_category(
        self,
        category_id: str,
        name: Optional[str] = None,
        parent_id: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> Optional[Category]:
        """
        Update a category.

        Args:
            category_id: ID of category to update
            name: Optional new name
            parent_id: Optional new parent ID
            color: Optional new color
            icon: Optional new icon

        Returns:
            Updated Category or None if not found

        Raises:
            ValueError: If parent category not found
        """
        category = self.get_category(category_id)
        if not category:
            return None

        if parent_id is not None:
            parent = self.get_category(parent_id)
            if not parent:
                raise ValueError("Parent category not found")
            category.parent_id = parent_id

        if name is not None:
            category.name = name
        if color is not None:
            category.color = color
        if icon is not None:
            category.icon = icon

        self.db.commit()
        self.db.refresh(category)

        logger.info(f"Updated category: {category.name}")
        return category

    def delete_category(self, category_id: str) -> bool:
        """
        Delete a category, reassigning transactions to 'Other'.

        Args:
            category_id: ID of category to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If 'Other' category not found
        """
        category = self.get_category(category_id)
        if not category:
            return False

        other_category = (
            self.db.query(Category)
            .filter(Category.name == "Other", Category.is_system == True)
            .first()
        )

        if not other_category:
            raise ValueError("'Other' category not found. Cannot delete category.")

        self.db.query(Transaction).filter(
            Transaction.category_id == category_id
        ).update({"category_id": other_category.id})

        self.db.delete(category)
        self.db.commit()

        logger.info(
            f"Deleted category: {category.name}, reassigned transactions to Other"
        )
        return True
