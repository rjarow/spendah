"""
Category API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.dependencies import get_db
from app.models import Category
from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryList,
)

router = APIRouter()


def build_category_tree(categories: List[Category]) -> List[CategoryResponse]:
    """Build a hierarchical tree structure from flat category list."""
    # Create a mapping of category IDs to category objects
    category_map = {cat.id: CategoryResponse.model_validate(cat) for cat in categories}

    # Build the tree
    root_categories = []
    for cat in category_map.values():
        if cat.parent_id is None:
            root_categories.append(cat)
        else:
            parent = category_map.get(cat.parent_id)
            if parent:
                parent.children.append(cat)

    return root_categories


@router.get("", response_model=CategoryList)
def list_categories(
    db: Session = Depends(get_db)
):
    """List all categories with tree structure."""
    categories = db.query(Category).all()
    tree = build_category_tree(categories)

    return CategoryList(
        items=tree,
        total=len(categories)
    )


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db)
):
    """Create a new category."""
    # Validate parent exists if parent_id is provided
    if category.parent_id:
        parent = db.query(Category).filter(Category.id == category.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent category not found")

    db_category = Category(
        name=category.name,
        parent_id=category.parent_id,
        color=category.color,
        icon=category.icon,
        is_system=False  # User-created categories are not system categories
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific category."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: str,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db)
):
    """Update a category."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Validate parent exists if parent_id is being updated
    if category_update.parent_id is not None:
        parent = db.query(Category).filter(Category.id == category_update.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent category not found")

    # Update fields if provided
    if category_update.name is not None:
        category.name = category_update.name
    if category_update.parent_id is not None:
        category.parent_id = category_update.parent_id
    if category_update.color is not None:
        category.color = category_update.color
    if category_update.icon is not None:
        category.icon = category_update.icon

    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: str,
    db: Session = Depends(get_db)
):
    """Delete a category (reassigns transactions to 'Other' first)."""
    from app.models import Transaction

    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Find the "Other" category
    other_category = db.query(Category).filter(
        Category.name == "Other",
        Category.is_system == True
    ).first()

    if not other_category:
        raise HTTPException(
            status_code=500,
            detail="'Other' category not found. Cannot delete category."
        )

    # Reassign all transactions to "Other"
    db.query(Transaction).filter(
        Transaction.category_id == category_id
    ).update({"category_id": other_category.id})

    # Delete the category
    db.delete(category)
    db.commit()
    return None
