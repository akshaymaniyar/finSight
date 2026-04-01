"""
AI-powered financial chat service.

Extracts context from the user's transactions and uses the Anthropic
Claude API to answer financial questions conversationally.
"""

from __future__ import annotations


import logging
import re
import uuid
from datetime import date, datetime
from typing import Optional

from dateutil.relativedelta import relativedelta
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.config import settings
from app.models.bank_account import BankAccount
from app.models.chat_history import ChatHistory
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
    "oct": 10, "nov": 11, "dec": 12,
}

CATEGORY_KEYWORDS = [
    "food", "dining", "shopping", "groceries", "transportation", "transport",
    "bills", "utilities", "entertainment", "health", "education", "rent",
    "emi", "insurance", "subscriptions", "atm", "salary", "income",
    "investments", "mutual fund", "self transfer",
]


def _extract_filters(message: str) -> dict:
    """Extract query filters from a natural-language message.

    Looks for month names, category keywords, bank names, merchant names,
    and card-type indicators.

    Returns:
        Dict with optional keys: date_from, date_to, category, card_type,
        merchant_search, transaction_type.
    """
    msg_lower = message.lower()
    filters: dict = {}

    # Extract month references
    current_year = date.today().year
    for month_name, month_num in MONTH_MAP.items():
        if month_name in msg_lower:
            # Check for year mention
            year = current_year
            year_match = re.search(r"\b(20\d{2})\b", message)
            if year_match:
                year = int(year_match.group(1))

            first_day = date(year, month_num, 1)
            last_day = (first_day + relativedelta(months=1)) - relativedelta(days=1)
            filters["date_from"] = first_day
            filters["date_to"] = last_day
            break

    # Handle "last month", "this month"
    if "last month" in msg_lower:
        first_day = (date.today().replace(day=1)) - relativedelta(months=1)
        last_day = date.today().replace(day=1) - relativedelta(days=1)
        filters["date_from"] = first_day
        filters["date_to"] = last_day
    elif "this month" in msg_lower:
        first_day = date.today().replace(day=1)
        filters["date_from"] = first_day
        filters["date_to"] = date.today()

    # Extract category
    for cat_kw in CATEGORY_KEYWORDS:
        if cat_kw in msg_lower:
            # Map keyword back to proper category name
            cat_map = {
                "food": "Food & Dining", "dining": "Food & Dining",
                "shopping": "Shopping", "groceries": "Groceries",
                "transportation": "Transportation", "transport": "Transportation",
                "bills": "Bills & Utilities", "utilities": "Bills & Utilities",
                "entertainment": "Entertainment", "health": "Health",
                "education": "Education", "rent": "Rent", "emi": "EMI",
                "insurance": "Insurance", "subscriptions": "Subscriptions",
                "atm": "ATM Withdrawal", "salary": "Salary/Income",
                "income": "Salary/Income", "investments": "Investments",
                "mutual fund": "Investments", "self transfer": "Self Transfer",
            }
            if cat_kw in cat_map:
                filters["category"] = cat_map[cat_kw]
                break

    # Extract card type
    if "credit card" in msg_lower:
        filters["card_type"] = "CREDIT_CARD"
    elif "debit card" in msg_lower:
        filters["card_type"] = "DEBIT_CARD"

    # Extract transaction type
    if "expense" in msg_lower or "spent" in msg_lower or "debit" in msg_lower:
        filters["transaction_type"] = "DEBIT"
    elif "income" in msg_lower or "earned" in msg_lower or "credit" in msg_lower:
        filters["transaction_type"] = "CREDIT"

    return filters


def _query_transactions(user_id: int, db: Session, filters: dict) -> list:
    """Query transactions based on extracted filters."""
    query = (
        db.query(Transaction, BankAccount.bank_name)
        .join(BankAccount, Transaction.bank_account_id == BankAccount.id, isouter=True)
        .filter(Transaction.user_id == user_id)
    )

    if "date_from" in filters:
        query = query.filter(Transaction.transaction_date >= filters["date_from"])
    if "date_to" in filters:
        query = query.filter(Transaction.transaction_date <= filters["date_to"])
    if "category" in filters:
        query = query.filter(Transaction.category == filters["category"])
    if "card_type" in filters:
        query = query.filter(Transaction.card_type == filters["card_type"])
    if "transaction_type" in filters:
        query = query.filter(Transaction.transaction_type == filters["transaction_type"])
    if "merchant_search" in filters:
        query = query.filter(
            Transaction.merchant.ilike(f"%{filters['merchant_search']}%")
        )

    query = query.order_by(Transaction.transaction_date.desc())
    return query.limit(200).all()


def _format_transactions_table(rows: list) -> str:
    """Format transaction rows as a compact text table for the LLM context."""
    if not rows:
        return "No transactions found matching the query."

    lines = ["Date | Merchant | Amount | Category | Bank | Type"]
    lines.append("-" * 70)

    for txn, bank_name in rows:
        txn_date = txn.transaction_date.strftime("%Y-%m-%d") if txn.transaction_date else "N/A"
        merchant = (txn.merchant or "N/A")[:30]
        amount = f"{txn.amount:,.2f}"
        category = (txn.category or "N/A")[:20]
        bank = (bank_name or "N/A")[:15]
        txn_type = txn.transaction_type or "N/A"
        lines.append(f"{txn_date} | {merchant} | {amount} | {category} | {bank} | {txn_type}")

    return "\n".join(lines)


def _build_system_prompt(transaction_context: str) -> str:
    """Build the system prompt that instructs Claude how to respond."""
    return (
        "You are FinSight, an AI financial assistant for Indian bank transactions. "
        "You help users understand their spending patterns, income, and financial habits.\n\n"
        "Guidelines:\n"
        "- Format all amounts in INR using the Rupee symbol (e.g., Rs 1,234.56)\n"
        "- Be concise and direct in your answers\n"
        "- When summarizing, provide totals, averages, and key insights\n"
        "- If the user asks about data you don't have, say so clearly\n"
        "- Support questions about categories, merchants, trends, and comparisons\n"
        "- Never make up transaction data that isn't in the context below\n\n"
        "Here are the user's relevant transactions:\n\n"
        f"{transaction_context}"
    )


async def process_chat(
    user_id: int,
    message: str,
    session_id: Optional[str],
    db: Session,
) -> str:
    """Process a user chat message and return the assistant's response.

    Args:
        user_id: The authenticated user's ID.
        message: The user's chat message.
        session_id: Optional chat session ID for conversation continuity.
        db: SQLAlchemy session.

    Returns:
        The assistant's response string.
    """
    logger.info("Incoming chat question: user_id=%s, message=%.100s", user_id, message)

    if not session_id:
        session_id = str(uuid.uuid4())

    # Check for API key
    if not settings.anthropic_api_key:
        return (
            "The Anthropic API key is not configured. Please set the "
            "ANTHROPIC_API_KEY environment variable to enable AI-powered chat. "
            "You can get an API key at https://console.anthropic.com/"
        )

    # Extract filters from the message
    filters = _extract_filters(message)
    logger.info("Extracted filters: %s", filters)

    # Query matching transactions
    rows = _query_transactions(user_id, db, filters)
    logger.info("Number of matching transactions: %d", len(rows))
    transaction_context = _format_transactions_table(rows)

    # Build system prompt
    system_prompt = _build_system_prompt(transaction_context)

    # Get recent chat history for this session (last 10 messages)
    history_records = (
        db.query(ChatHistory)
        .filter(
            ChatHistory.user_id == user_id,
            ChatHistory.session_id == session_id,
        )
        .order_by(ChatHistory.created_at.desc())
        .limit(10)
        .all()
    )
    # Reverse to chronological order
    history_records = list(reversed(history_records))

    # Build messages list for the API
    messages = []
    for record in history_records:
        messages.append({"role": record.role, "content": record.content})
    messages.append({"role": "user", "content": message})

    # Call Anthropic Claude API
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        logger.info("Calling Claude API: model=claude-sonnet-4-20250514, max_tokens=1024, messages_count=%d", len(messages))
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )

        assistant_message = response.content[0].text
        logger.info("Claude response length: %d chars", len(assistant_message))

    except ImportError:
        assistant_message = (
            "The anthropic Python package is not installed. "
            "Please run: pip install anthropic"
        )
    except Exception as e:
        logger.exception("Anthropic API error")
        assistant_message = (
            f"I encountered an error processing your request. "
            f"Please try again. Error: {str(e)}"
        )

    # Store user message and assistant response in chat history
    user_record = ChatHistory(
        user_id=user_id,
        session_id=session_id,
        role="user",
        content=message,
    )
    assistant_record = ChatHistory(
        user_id=user_id,
        session_id=session_id,
        role="assistant",
        content=assistant_message,
    )
    db.add(user_record)
    db.add(assistant_record)
    db.commit()

    return assistant_message
