from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class StatementResponse(BaseModel):
    id: int
    source_type: str
    email_from: Optional[str] = None
    email_subject: Optional[str] = None
    email_date: Optional[datetime] = None
    statement_month: Optional[date] = None
    parse_status: str
    parse_error: Optional[str] = None
    transaction_count: int = 0
    total_amount_due: Optional[float] = None
    minimum_amount_due: Optional[float] = None
    bank_name: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StatementDetailResponse(StatementResponse):
    raw_content: Optional[str] = None
    transactions: List = []


class StatementListResponse(BaseModel):
    statements: List[StatementResponse]
    total: int
