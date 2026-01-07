"""
Category Pydantic schemas for API validation.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class CategoryBase(BaseModel):
    """Base category schema."""
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)


class CategoryCreate(CategoryBase):
    """Schema for creating a category."""
    pass


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    parent_id: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)


class CategoryResponse(CategoryBase):
    """Schema for category response."""
    id: str
    is_system: bool
    created_at: datetime
    children: list["CategoryResponse"] = []

    class Config:
        from_attributes = True


# Enable forward references for recursive model
CategoryResponse.model_rebuild()


class CategoryList(BaseModel):
    """Schema for listing categories."""
    items: list[CategoryResponse]
    total: int
