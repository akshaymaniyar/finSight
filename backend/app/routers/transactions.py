"""
Transactions router: list, search, summarize, and update transactions.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, case
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.bank_account import BankAccount
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import (
    TransactionListResponse,
    TransactionResponse,
    TransactionUpdateRequest,
)

router = APIRouter()


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    category: Optional[str] = Query(None, description="Filter by category"),
    transaction_type: Optional[str] = Query(None, description="DEBIT or CREDIT"),
    bank_name: Optional[str] = Query(None, description="Filter by bank name"),
    card_type: Optional[str] = Query(None, description="ACCOUNT, CREDIT_CARD, or DEBIT_CARD"),
    search: Optional[str] = Query(None, description="Search merchant name"),
    date_from: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    exclude_self_transfers: bool = Query(False, description="Exclude self transfers"),
    exclude_investments: bool = Query(False, description="Exclude investment transactions"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List transactions with comprehensive filtering and pagination."""
    logger.info("Transaction list request: user_id=%s, category=%s, type=%s, bank=%s, card=%s, search=%s, date_from=%s, date_to=%s", current_user.id, category, transaction_type, bank_name, card_type, search, date_from, date_to)
    query = (
        db.query(Transaction, BankAccount.bank_name)
        .join(BankAccount, Transaction.bank_account_id == BankAccount.id, isouter=True)
        .filter(Transaction.user_id == current_user.id)
    )

    if category:
        query = query.filter(Transaction.category == category)
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type.upper())
    if bank_name:
        query = query.filter(BankAccount.bank_name.ilike(f"%{bank_name}%"))
    if card_type:
        query = query.filter(Transaction.card_type == card_type.upper())
    if search:
        query = query.filter(Transaction.merchant.ilike(f"%{search}%"))
    if date_from:
        query = query.filter(Transaction.transaction_date >= date_from)
    if date_to:
        query = query.filter(Transaction.transaction_date <= date_to)
    if exclude_self_transfers:
        query = query.filter(Transaction.is_self_transfer == False)
    if exclude_investments:
        query = query.filter(Transaction.is_investment == False)

    # Total count before pagination
    total = query.count()

    # Fetch paginated results
    rows = (
        query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    transactions = []
    for txn, b_name in rows:
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
                bank_name=b_name,
                statement_id=txn.statement_id,
                created_at=txn.created_at,
            )
        )

    return TransactionListResponse(
        transactions=transactions,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/summary")
async def get_transaction_summary(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return aggregate totals: expenses, income, investments, self-transfers, count."""
    logger.info("Transaction summary request: user_id=%s, date_from=%s, date_to=%s", current_user.id, date_from, date_to)
    filters = [Transaction.user_id == current_user.id]
    if date_from:
        filters.append(Transaction.transaction_date >= date_from)
    if date_to:
        filters.append(Transaction.transaction_date <= date_to)

    row = (
        db.query(
            # Total expenses: DEBIT transactions that are NOT excluded
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Transaction.transaction_type == "DEBIT",
                                Transaction.is_excluded == False,
                            ),
                            Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_expenses"),
            # Total income: CREDIT transactions from bank accounts only (not credit cards)
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Transaction.transaction_type == "CREDIT",
                                Transaction.card_type != "CREDIT_CARD",
                                Transaction.is_self_transfer == False,
                                Transaction.is_excluded == False,
                            ),
                            Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_income"),
            # Total investments
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Transaction.is_investment == True,
                                Transaction.transaction_type == "DEBIT",
                            ),
                            Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_investments"),
            # Total self-transfers
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Transaction.is_self_transfer == True,
                                Transaction.transaction_type == "DEBIT",
                            ),
                            Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_self_transfers"),
            # Transaction count
            func.count(Transaction.id).label("transaction_count"),
        )
        .filter(and_(*filters))
        .first()
    )

    return {
        "total_expenses": round(float(row.total_expenses or 0), 2),
        "total_income": round(float(row.total_income or 0), 2),
        "total_investments": round(float(row.total_investments or 0), 2),
        "total_self_transfers": round(float(row.total_self_transfers or 0), 2),
        "transaction_count": row.transaction_count or 0,
    }


@router.put("/{transaction_id}")
async def update_transaction(
    transaction_id: int,
    body: TransactionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a transaction's category, sub_category, or is_excluded flag."""
    logger.info("Transaction update request: user_id=%s, transaction_id=%s", current_user.id, transaction_id)
    txn = (
        db.query(Transaction)
        .filter(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id,
        )
        .first()
    )

    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if body.category is not None:
        txn.category = body.category
    if body.sub_category is not None:
        txn.sub_category = body.sub_category
    if body.is_excluded is not None:
        txn.is_excluded = body.is_excluded

    db.commit()
    db.refresh(txn)

    # Fetch bank name for response
    bank_name = None
    if txn.bank_account_id:
        acct = db.query(BankAccount).filter(BankAccount.id == txn.bank_account_id).first()
        if acct:
            bank_name = acct.bank_name

    return TransactionResponse(
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
        bank_name=bank_name,
        statement_id=txn.statement_id,
        created_at=txn.created_at,
    )
