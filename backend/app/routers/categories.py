"""
Category router: CRUD for two-level expense categories.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.category import Category
from app.models.user import User
from app.schemas.category import (
    CategoryResponse,
    SubcategoryResponse,
    CategoryCreateRequest,
    CategoryUpdateRequest,
    CategoryListResponse,
)
from app.services.category_seed import DEFAULT_CATEGORIES

logger = logging.getLogger(__name__)

router = APIRouter()


def _seed_categories_for_user(user_id: int, db: Session) -> None:
    """Seed default categories for a user if they have none."""
    existing = db.query(Category).filter(Category.user_id == user_id).count()
    if existing > 0:
        return

    logger.info("Seeding default categories for user_id=%s", user_id)
    sort_order = 0
    for name, icon, color, is_income, subcats in DEFAULT_CATEGORIES:
        parent = Category(
            user_id=user_id,
            name=name,
            icon=icon,
            color=color,
            is_income=is_income,
            is_system=True,
            sort_order=sort_order,
        )
        db.add(parent)
        db.flush()

        for sub_name, keywords in subcats:
            sub = Category(
                user_id=user_id,
                name=sub_name,
                parent_id=parent.id,
                is_income=is_income,
                is_system=True,
                keywords=keywords,
            )
            db.add(sub)

        sort_order += 1

    db.commit()
    logger.info("Seeded %d parent categories for user_id=%s", sort_order, user_id)


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all categories with subcategories for the current user."""
    # Seed defaults on first access
    _seed_categories_for_user(current_user.id, db)

    parents = (
        db.query(Category)
        .filter(
            Category.user_id == current_user.id,
            Category.parent_id == None,
        )
        .order_by(Category.sort_order)
        .all()
    )

    result = []
    for p in parents:
        subs = (
            db.query(Category)
            .filter(Category.parent_id == p.id)
            .order_by(Category.id)
            .all()
        )
        result.append(
            CategoryResponse(
                id=p.id,
                name=p.name,
                icon=p.icon,
                color=p.color,
                is_income=p.is_income,
                is_system=p.is_system,
                sort_order=p.sort_order,
                subcategories=[
                    SubcategoryResponse(id=s.id, name=s.name, keywords=s.keywords)
                    for s in subs
                ],
            )
        )

    return CategoryListResponse(categories=result)


@router.post("", response_model=CategoryResponse)
async def create_category(
    request: CategoryCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new category or subcategory."""
    # If creating a subcategory, verify parent exists and belongs to user
    if request.parent_id:
        parent = db.query(Category).filter(
            Category.id == request.parent_id,
            Category.user_id == current_user.id,
        ).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent category not found")

    cat = Category(
        user_id=current_user.id,
        name=request.name,
        icon=request.icon,
        color=request.color,
        is_income=request.is_income,
        parent_id=request.parent_id,
        is_system=False,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)

    return CategoryResponse(
        id=cat.id,
        name=cat.name,
        icon=cat.icon,
        color=cat.color,
        is_income=cat.is_income,
        is_system=cat.is_system,
        sort_order=cat.sort_order,
        subcategories=[],
    )


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    request: CategoryUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a category's name, icon, color, or keywords."""
    cat = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id,
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    if request.name is not None:
        cat.name = request.name
    if request.icon is not None:
        cat.icon = request.icon
    if request.color is not None:
        cat.color = request.color
    if request.keywords is not None:
        cat.keywords = request.keywords
    if request.sort_order is not None:
        cat.sort_order = request.sort_order

    db.commit()
    db.refresh(cat)

    subs = (
        db.query(Category)
        .filter(Category.parent_id == cat.id)
        .order_by(Category.id)
        .all()
    )

    return CategoryResponse(
        id=cat.id,
        name=cat.name,
        icon=cat.icon,
        color=cat.color,
        is_income=cat.is_income,
        is_system=cat.is_system,
        sort_order=cat.sort_order,
        subcategories=[
            SubcategoryResponse(id=s.id, name=s.name, keywords=s.keywords)
            for s in subs
        ],
    )


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a user-created category. System categories cannot be deleted."""
    cat = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id,
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    if cat.is_system:
        raise HTTPException(status_code=400, detail="System categories cannot be deleted")

    # Delete subcategories first
    db.query(Category).filter(Category.parent_id == cat.id).delete()
    db.delete(cat)
    db.commit()

    return {"message": "Category deleted"}
