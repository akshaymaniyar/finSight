"""
Analytics router: category breakdowns, monthly trends, top merchants,
and card-type comparisons.
"""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.services import analytics_service

router = APIRouter()


@router.get("/by-category")
async def category_breakdown(
    date_from: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    card_type: Optional[str] = Query(None, description="ACCOUNT, CREDIT_CARD, or DEBIT_CARD"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get spending breakdown by category."""
    logger.info("Analytics by-category: user_id=%s, date_from=%s, date_to=%s, card_type=%s", current_user.id, date_from, date_to, card_type)
    data = analytics_service.get_category_breakdown(
        user_id=current_user.id,
        db=db,
        date_from=date_from,
        date_to=date_to,
        card_type=card_type.upper() if card_type else None,
    )
    return {"categories": data}


@router.get("/monthly-trend")
async def monthly_trend(
    months: int = Query(12, ge=1, le=60, description="Number of months to look back"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get monthly income/expense trend."""
    logger.info("Analytics monthly-trend: user_id=%s, months=%d", current_user.id, months)
    data = analytics_service.get_monthly_trend(
        user_id=current_user.id,
        db=db,
        months=months,
    )
    return {"months": data}


@router.get("/top-merchants")
async def top_merchants(
    limit: int = Query(20, ge=1, le=100, description="Number of merchants to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get top merchants by total spend."""
    logger.info("Analytics top-merchants: user_id=%s, limit=%d", current_user.id, limit)
    data = analytics_service.get_top_merchants(
        user_id=current_user.id,
        db=db,
        limit=limit,
    )
    return {"merchants": data}


@router.get("/card-comparison")
async def card_comparison(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compare spending across credit card, debit card, and account."""
    logger.info("Analytics card-comparison: user_id=%s", current_user.id)
    data = analytics_service.get_card_comparison(
        user_id=current_user.id,
        db=db,
    )
    return data
