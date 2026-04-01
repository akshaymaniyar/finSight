from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


class TransactionResponse(BaseModel):
    id: int
    transaction_type: str
    amount: Decimal
    merchant: Optional[str] = None
    raw_description: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    transaction_date: date
    reference_id: Optional[str] = None
    balance_after: Optional[Decimal] = None
    is_self_transfer: bool = False
    is_investment: bool = False
    is_mutual_fund: bool = False
    is_zerodha: bool = False
    is_excluded: bool = False
    card_type: str = "ACCOUNT"
    bank_name: Optional[str] = None
    statement_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    transactions: List[TransactionResponse]
    total: int
    limit: int
    offset: int


class TransactionUpdateRequest(BaseModel):
    category: Optional[str] = None
    sub_category: Optional[str] = None
    is_excluded: Optional[bool] = None
