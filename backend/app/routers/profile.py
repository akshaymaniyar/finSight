"""
Profile router: manage user profile data needed for PDF password generation.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
):
    """Get the current user's profile."""
    logger.info("Profile get for user_id=%s", current_user.id)
    return ProfileResponse(
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        dob=current_user.dob,
        pan_first5=current_user.pan_first5,
        mobile_last5=current_user.mobile_last5,
        customer_ids=current_user.customer_ids or {},
        profile_completed=bool(current_user.profile_completed),
    )


@router.put("", response_model=ProfileResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user profile fields."""
    logger.info("Profile update for user_id=%s", current_user.id)

    if request.first_name is not None:
        current_user.first_name = request.first_name
    if request.last_name is not None:
        current_user.last_name = request.last_name
    if request.dob is not None:
        current_user.dob = request.dob
    if request.pan_first5 is not None:
        current_user.pan_first5 = request.pan_first5.upper()[:5]
    if request.mobile_last5 is not None:
        current_user.mobile_last5 = request.mobile_last5[-5:]
    if request.customer_ids is not None:
        existing = current_user.customer_ids or {}
        existing.update(request.customer_ids)
        current_user.customer_ids = existing

    # Mark profile as completed if we have at least first_name + dob
    if current_user.first_name and current_user.dob:
        current_user.profile_completed = 1

    db.commit()
    db.refresh(current_user)

    return ProfileResponse(
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        dob=current_user.dob,
        pan_first5=current_user.pan_first5,
        mobile_last5=current_user.mobile_last5,
        customer_ids=current_user.customer_ids or {},
        profile_completed=bool(current_user.profile_completed),
    )
