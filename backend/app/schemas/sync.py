from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class SyncMonthRequest(BaseModel):
    month: str  # YYYY-MM format
    force: bool = False


class SyncStatusItem(BaseModel):
    month: str
    sync_status: Optional[str] = None
    emails_found: int = 0
    emails_parsed: int = 0
    transactions_created: int = 0
    last_synced: Optional[datetime] = None


class SyncStatusResponse(BaseModel):
    months: List[SyncStatusItem]


class SyncResultResponse(BaseModel):
    status: str
    month: str
    emails_found: int = 0
    emails_parsed: int = 0
    transactions_created: int = 0
    message: str = ""


class SyncHistoryResponse(BaseModel):
    id: int
    sync_month: date
    sync_status: str
    emails_found: int = 0
    emails_parsed: int = 0
    transactions_created: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
