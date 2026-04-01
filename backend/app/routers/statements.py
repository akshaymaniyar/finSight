"""
Statements router: list and view bank statement records.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

logger = logging.getLogger(__name__)
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.bank_account import BankAccount
from app.models.statement import Statement
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.statement import (
    StatementDetailResponse,
    StatementListResponse,
    StatementResponse,
)
from app.schemas.transaction import TransactionResponse

router = APIRouter()


@router.get("", response_model=StatementListResponse)
async def list_statements(
    bank_name: Optional[str] = Query(None, description="Filter by bank name"),
    month: Optional[str] = Query(None, description="Filter by month (YYYY-MM)"),
    parse_status: Optional[str] = Query(None, description="Filter by parse status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List statements with optional filters and pagination."""
    logger.info("Statement list request: user_id=%s, bank=%s, month=%s, status=%s", current_user.id, bank_name, month, parse_status)
    query = (
        db.query(Statement, BankAccount.bank_name)
        .join(BankAccount, Statement.bank_account_id == BankAccount.id, isouter=True)
        .filter(Statement.user_id == current_user.id)
    )

    if bank_name:
        query = query.filter(BankAccount.bank_name.ilike(f"%{bank_name}%"))

    if month:
        from datetime import datetime
        try:
            month_date = datetime.strptime(month, "%Y-%m").date()
            query = query.filter(Statement.statement_month == month_date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid month format. Use YYYY-MM",
            )

    if parse_status:
        query = query.filter(Statement.parse_status == parse_status.upper())

    # Get total count before pagination
    total = query.count()

    # Apply pagination and ordering
    rows = (
        query.order_by(Statement.email_date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    statements = []
    for stmt, b_name in rows:
        statements.append(
            StatementResponse(
                id=stmt.id,
                source_type=stmt.source_type,
                email_from=stmt.email_from,
                email_subject=stmt.email_subject,
                email_date=stmt.email_date,
                statement_month=stmt.statement_month,
                parse_status=stmt.parse_status,
                parse_error=stmt.parse_error,
                transaction_count=stmt.transaction_count,
                bank_name=b_name,
                created_at=stmt.created_at,
            )
        )

    return StatementListResponse(statements=statements, total=total)


@router.get("/{statement_id}", response_model=StatementDetailResponse)
async def get_statement_detail(
    statement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a statement with its transactions and raw content."""
    logger.info("Statement detail request: user_id=%s, statement_id=%s", current_user.id, statement_id)
    row = (
        db.query(Statement, BankAccount.bank_name)
        .join(BankAccount, Statement.bank_account_id == BankAccount.id, isouter=True)
        .filter(
            Statement.id == statement_id,
            Statement.user_id == current_user.id,
        )
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="Statement not found")

    stmt, b_name = row

    # Fetch associated transactions
    txn_rows = (
        db.query(Transaction, BankAccount.bank_name)
        .join(BankAccount, Transaction.bank_account_id == BankAccount.id, isouter=True)
        .filter(Transaction.statement_id == stmt.id)
        .order_by(Transaction.transaction_date.asc())
        .all()
    )

    transactions = []
    for txn, txn_bank_name in txn_rows:
        transactions.append(
            TransactionResponse(
                id=txn.id,
                transaction_type=txn.transaction_type,
                amount=txn.amount,
                merchant=txn.merchant,
                raw_description=txn.raw_description,
                category=txn.category,
                sub_category=txn.sub_category,
                transaction_date=txn.transaction_date,
                reference_id=txn.reference_id,
                balance_after=txn.balance_after,
                is_self_transfer=txn.is_self_transfer,
                is_investment=txn.is_investment,
                is_mutual_fund=txn.is_mutual_fund,
                is_zerodha=txn.is_zerodha,
                is_excluded=txn.is_excluded,
                card_type=txn.card_type,
                bank_name=txn_bank_name,
                statement_id=txn.statement_id,
                created_at=txn.created_at,
            )
        )

    return StatementDetailResponse(
        id=stmt.id,
        source_type=stmt.source_type,
        email_from=stmt.email_from,
        email_subject=stmt.email_subject,
        email_date=stmt.email_date,
        statement_month=stmt.statement_month,
        parse_status=stmt.parse_status,
        parse_error=stmt.parse_error,
        transaction_count=stmt.transaction_count,
        bank_name=b_name,
        created_at=stmt.created_at,
        raw_content=stmt.raw_content,
        transactions=transactions,
    )
