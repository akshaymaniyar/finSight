from __future__ import annotations

from datetime import date
from typing import Optional, Dict

from pydantic import BaseModel


class ProfileResponse(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dob: Optional[date] = None
    pan_first5: Optional[str] = None
    mobile_last5: Optional[str] = None
    customer_ids: Optional[Dict[str, str]] = None
    profile_completed: bool = False

    class Config:
        from_attributes = True


class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dob: Optional[date] = None
    pan_first5: Optional[str] = None
    mobile_last5: Optional[str] = None
    customer_ids: Optional[Dict[str, str]] = None
