from __future__ import annotations

from typing import Optional, List

from pydantic import BaseModel


class SubcategoryResponse(BaseModel):
    id: int
    name: str
    keywords: Optional[str] = None

    class Config:
        from_attributes = True


class CategoryResponse(BaseModel):
    id: int
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    is_income: bool = False
    is_system: bool = True
    sort_order: int = 0
    subcategories: List[SubcategoryResponse] = []

    class Config:
        from_attributes = True


class CategoryCreateRequest(BaseModel):
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    is_income: bool = False
    parent_id: Optional[int] = None  # If set, creates a subcategory


class CategoryUpdateRequest(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    keywords: Optional[str] = None
    sort_order: Optional[int] = None


class CategoryListResponse(BaseModel):
    categories: List[CategoryResponse]
