"""
Sync router: trigger email syncs, check sync status, and view history.
"""

from __future__ import annotations

import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)
from typing import Optional

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.sync_history import SyncHistory
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.sync import (
    SyncHistoryResponse,
    SyncMonthRequest,
    SyncResultResponse,
    SyncStatusItem,
    SyncStatusResponse,
)
from app.services import sync_service

router = APIRouter()


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the sync status for the last 24 months."""
    logger.info("Sync status request for user_id=%s", current_user.id)
    today = date.today()
    months: list[SyncStatusItem] = []

    for i in range(24):
        month_date = today.replace(day=1) - relativedelta(months=i)
        month_str = month_date.strftime("%Y-%m")

        # Get the latest SyncHistory record for this month
        latest_sync = (
            db.query(SyncHistory)
            .filter(
                SyncHistory.user_id == current_user.id,
                SyncHistory.sync_month == month_date,
            )
            .order_by(SyncHistory.started_at.desc())
            .first()
        )

        # Count transactions for this month
        first_day = month_date
        last_day = (month_date + relativedelta(months=1)) - relativedelta(days=1)
        txn_count = (
            db.query(func.count(Transaction.id))
            .filter(
                Transaction.user_id == current_user.id,
                Transaction.transaction_date >= first_day,
                Transaction.transaction_date <= last_day,
            )
            .scalar()
        ) or 0

        item = SyncStatusItem(
            month=month_str,
            sync_status=latest_sync.sync_status if latest_sync else None,
            emails_found=latest_sync.emails_found if latest_sync else 0,
            emails_parsed=latest_sync.emails_parsed if latest_sync else 0,
            transactions_created=txn_count,
            last_synced=latest_sync.completed_at if latest_sync else None,
        )
        months.append(item)

    return SyncStatusResponse(months=months)


@router.post("/month", response_model=SyncResultResponse)
async def sync_month(
    request: SyncMonthRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync bank emails for a specific month."""
    logger.info("Sync month request: user_id=%s, month=%s, force=%s", current_user.id, request.month, request.force)
    # Validate month format
    try:
        datetime.strptime(request.month, "%Y-%m")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid month format. Use YYYY-MM (e.g., 2024-03)",
        )

    result = await sync_service.sync_month(
        user_id=current_user.id,
        month_str=request.month,
        force_resync=request.force,
        db=db,
    )
    return result


@router.post("/resync", response_model=SyncResultResponse)
async def resync_month(
    request: SyncMonthRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Force re-sync for a specific month (deletes existing data first)."""
    logger.info("Resync request: user_id=%s, month=%s", current_user.id, request.month)
    try:
        datetime.strptime(request.month, "%Y-%m")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid month format. Use YYYY-MM (e.g., 2024-03)",
        )

    result = await sync_service.sync_month(
        user_id=current_user.id,
        month_str=request.month,
        force_resync=True,
        db=db,
    )
    return result


@router.get("/history", response_model=list[SyncHistoryResponse])
async def get_sync_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all sync history records for the current user."""
    records = (
        db.query(SyncHistory)
        .filter(SyncHistory.user_id == current_user.id)
        .order_by(SyncHistory.sync_month.desc(), SyncHistory.started_at.desc())
        .all()
    )
    return records
