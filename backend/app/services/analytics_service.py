"""
Analytics query service.

Provides aggregated financial analytics: category breakdowns, monthly
trends, top merchants, and card-type comparisons.
"""

from __future__ import annotations

import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)
from typing import Optional

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, case, and_
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.transaction import Transaction


def get_category_breakdown(
    user_id: int,
    db: Session,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    card_type: Optional[str] = None,
) -> list[dict]:
    """Get spending breakdown by category.

    Returns a list of dicts sorted by total_amount descending:
        {category, total_amount, count, percentage}
    """
    logger.info("get_category_breakdown: user_id=%s, date_from=%s, date_to=%s, card_type=%s", user_id, date_from, date_to, card_type)
    filters = [
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
        Transaction.is_excluded == False,
    ]
    if date_from:
        filters.append(Transaction.transaction_date >= date_from)
    if date_to:
        filters.append(Transaction.transaction_date <= date_to)
    if card_type:
        filters.append(Transaction.card_type == card_type)

    rows = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount).label("total_amount"),
            func.count(Transaction.id).label("count"),
        )
        .filter(and_(*filters))
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )

    grand_total = sum(float(r.total_amount or 0) for r in rows)

    result = []
    for row in rows:
        total = float(row.total_amount or 0)
        result.append({
            "category": row.category or "Uncategorized",
            "total_amount": round(total, 2),
            "count": row.count,
            "percentage": round((total / grand_total * 100) if grand_total > 0 else 0, 2),
        })

    return result


def get_monthly_trend(
    user_id: int,
    db: Session,
    months: int = 12,
) -> list[dict]:
    """Get monthly income/expense trend for the last N months.

    Returns a list of dicts ordered by month ascending:
        {month, total_spent, total_income, count}
    """
    logger.info("get_monthly_trend: user_id=%s, months=%d", user_id, months)
    cutoff = date.today() - relativedelta(months=months)

    rows = (
        db.query(
            func.date_format(Transaction.transaction_date, "%Y-%m").label("month"),
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
            ).label("total_spent"),
            func.sum(
                case(
                    (Transaction.transaction_type == "CREDIT", Transaction.amount),
                    else_=0,
                )
            ).label("total_income"),
            func.count(Transaction.id).label("count"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= cutoff,
        )
        .group_by(func.date_format(Transaction.transaction_date, "%Y-%m"))
        .order_by(func.date_format(Transaction.transaction_date, "%Y-%m").asc())
        .all()
    )

    return [
        {
            "month": row.month,
            "total_spent": round(float(row.total_spent or 0), 2),
            "total_income": round(float(row.total_income or 0), 2),
            "count": row.count,
        }
        for row in rows
    ]


def get_top_merchants(
    user_id: int,
    db: Session,
    limit: int = 20,
) -> list[dict]:
    """Get top merchants by total spend.

    Returns a list of dicts sorted by total_amount descending:
        {merchant, total_amount, count}
    """
    logger.info("get_top_merchants: user_id=%s, limit=%d", user_id, limit)
    rows = (
        db.query(
            Transaction.merchant,
            func.sum(Transaction.amount).label("total_amount"),
            func.count(Transaction.id).label("count"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "DEBIT",
            Transaction.is_excluded == False,
            Transaction.merchant != None,
            Transaction.merchant != "",
        )
        .group_by(Transaction.merchant)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "merchant": row.merchant,
            "total_amount": round(float(row.total_amount or 0), 2),
            "count": row.count,
        }
        for row in rows
    ]


def get_card_comparison(
    user_id: int,
    db: Session,
) -> dict:
    """Compare spending across card types.

    Returns:
        {
            credit_card_spend: float,
            debit_spend: float,
            account_spend: float,
            per_card_breakdown: [{bank_name, card_type, total_amount, count}]
        }
    """
    logger.info("get_card_comparison: user_id=%s", user_id)
    # Aggregate by card_type
    type_rows = (
        db.query(
            Transaction.card_type,
            func.sum(Transaction.amount).label("total_amount"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "DEBIT",
            Transaction.is_excluded == False,
        )
        .group_by(Transaction.card_type)
        .all()
    )

    type_totals = {row.card_type: float(row.total_amount or 0) for row in type_rows}

    # Per-card breakdown joined with bank accounts
    card_rows = (
        db.query(
            BankAccount.bank_name,
            Transaction.card_type,
            func.sum(Transaction.amount).label("total_amount"),
            func.count(Transaction.id).label("count"),
        )
        .join(BankAccount, Transaction.bank_account_id == BankAccount.id, isouter=True)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "DEBIT",
            Transaction.is_excluded == False,
        )
        .group_by(BankAccount.bank_name, Transaction.card_type)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )

    per_card = [
        {
            "bank_name": row.bank_name or "Unknown",
            "card_type": row.card_type or "ACCOUNT",
            "total_amount": round(float(row.total_amount or 0), 2),
            "count": row.count,
        }
        for row in card_rows
    ]

    return {
        "credit_card_spend": round(type_totals.get("CREDIT_CARD", 0), 2),
        "debit_spend": round(type_totals.get("DEBIT_CARD", 0), 2),
        "account_spend": round(type_totals.get("ACCOUNT", 0), 2),
        "per_card_breakdown": per_card,
    }
