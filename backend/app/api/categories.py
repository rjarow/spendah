"""
Category API endpoints - refactored to use service layer.
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
from app.services.category_service import CategoryService

router = APIRouter()


@router.get("", response_model=CategoryList)
def list_categories(db: Session = Depends(get_db)):
    """List all categories with tree structure."""
    service = CategoryService(db)
    categories = service.list_categories()
    tree = service.build_category_tree(categories)

    return CategoryList(
        items=[CategoryResponse(**cat) for cat in tree], total=len(categories)
    )


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    """Create a new category."""
    service = CategoryService(db)
    try:
        db_category = service.create_category(
            name=category.name,
            parent_id=category.parent_id,
            color=category.color,
            icon=category.icon,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return db_category


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: str, db: Session = Depends(get_db)):
    """Get a specific category."""
    service = CategoryService(db)
    category = service.get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: str, category_update: CategoryUpdate, db: Session = Depends(get_db)
):
    """Update a category."""
    service = CategoryService(db)
    try:
        category = service.update_category(
            category_id=category_id,
            name=category_update.name,
            parent_id=category_update.parent_id,
            color=category_update.color,
            icon=category_update.icon,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: str, db: Session = Depends(get_db)):
    """Delete a category (reassigns transactions to 'Other' first)."""
    service = CategoryService(db)
    try:
        deleted = service.delete_category(category_id)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not deleted:
        raise HTTPException(status_code=404, detail="Category not found")
    return None
