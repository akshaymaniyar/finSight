"""
Shared PDF parsing logic for bank account statements.

Most Indian bank account PDFs follow a similar table format:
  Date | Narration/Description | Chq/Ref | Withdrawal | Deposit | Balance

This module provides a shared parser that handles multi-line narrations
and various date formats.
"""

import re
from decimal import Decimal
from typing import List, Optional

from .base import ParsedTransaction
from .email_utils import extract_date
from .pdf_utils import extract_tables_from_pdf, extract_text_from_pdf


def parse_bank_account_pdf(
    pdf_bytes: bytes,
    password: str = "",
    date_format: str = "DD/MM/YY",  # or DD/MM/YYYY
) -> List[ParsedTransaction]:
    """Parse a bank account statement PDF into transactions.

    Works for most Indian bank statement formats that use table layout with
    separate Withdrawal and Deposit columns.
    """
    transactions: List[ParsedTransaction] = []

    # Try table extraction first
    tables = extract_tables_from_pdf(pdf_bytes, password)
    if tables:
        for table in tables:
            transactions.extend(_parse_table_rows(table))

    # Fallback to text extraction
    if not transactions:
        text = extract_text_from_pdf(pdf_bytes, password)
        if text:
            transactions.extend(_parse_text_lines(text))

    return transactions


def _parse_table_rows(table: List[List[str]]) -> List[ParsedTransaction]:
    """Parse a table extracted by pdfplumber."""
    transactions: List[ParsedTransaction] = []

    # Try to detect header row to identify column positions
    header_idx = _find_header_row(table)
    withdrawal_col = -1
    deposit_col = -1
    balance_col = -1

    if header_idx >= 0 and header_idx < len(table):
        header = [c.upper().strip() if c else "" for c in table[header_idx]]
        for i, h in enumerate(header):
            if any(w in h for w in ["WITHDRAWAL", "DEBIT", "DR", "WITHDRAW"]):
                withdrawal_col = i
            elif any(d in h for d in ["DEPOSIT", "CREDIT", "CR", "AMOUNT"]):
                deposit_col = i
            elif "BALANCE" in h or "BAL" in h:
                balance_col = i

    pending_description = ""

    for row_idx, row in enumerate(table):
        if row_idx <= header_idx:
            continue
        if len(row) < 3:
            continue

        date_str = (row[0] or "").strip()

        # Check if this row starts with a date
        if not re.match(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", date_str):
            # Multi-line narration continuation
            if pending_description and len(row) > 1:
                extra = (row[1] or "").strip()
                if extra and not re.match(r"[\d,]+\.?\d*$", extra.replace(",", "")):
                    pending_description += " " + extra
            continue

        # This row has a date — process any pending transaction first would need
        # more context. For simplicity, process current row directly.
        description = (row[1] or "").strip()

        # Find amounts
        withdrawal_str = ""
        deposit_str = ""
        balance_str = ""

        if withdrawal_col >= 0 and withdrawal_col < len(row):
            withdrawal_str = _clean_amount(row[withdrawal_col])
        if deposit_col >= 0 and deposit_col < len(row):
            deposit_str = _clean_amount(row[deposit_col])
        if balance_col >= 0 and balance_col < len(row):
            balance_str = _clean_amount(row[balance_col])

        # If columns weren't detected, use position heuristics
        if not withdrawal_str and not deposit_str:
            numeric_cells = []
            for i in range(2, len(row)):
                val = _clean_amount(row[i])
                if val:
                    numeric_cells.append((i, val))

            if len(numeric_cells) >= 2:
                # Assume: ..., Withdrawal, Deposit, Balance
                withdrawal_str = numeric_cells[0][1] if len(numeric_cells) > 0 else ""
                deposit_str = numeric_cells[1][1] if len(numeric_cells) > 1 else ""
                if len(numeric_cells) > 2:
                    balance_str = numeric_cells[-1][1]
            elif len(numeric_cells) == 1:
                # Single amount - determine direction from context
                withdrawal_str = numeric_cells[0][1]

        txn_date = extract_date(date_str)
        if not txn_date:
            continue

        balance_after: Optional[Decimal] = None
        if balance_str:
            try:
                balance_after = Decimal(balance_str)
            except Exception:
                pass

        # Create transaction(s)
        if withdrawal_str:
            try:
                amount = Decimal(withdrawal_str)
                if amount > 0:
                    transactions.append(
                        ParsedTransaction(
                            transaction_type="DEBIT",
                            amount=amount,
                            merchant=description,
                            raw_description=description,
                            transaction_date=txn_date,
                            balance_after=balance_after,
                            card_type="ACCOUNT",
                        )
                    )
            except Exception:
                pass

        if deposit_str and deposit_str != withdrawal_str:
            try:
                amount = Decimal(deposit_str)
                if amount > 0:
                    transactions.append(
                        ParsedTransaction(
                            transaction_type="CREDIT",
                            amount=amount,
                            merchant=description,
                            raw_description=description,
                            transaction_date=txn_date,
                            balance_after=balance_after,
                            card_type="ACCOUNT",
                        )
                    )
            except Exception:
                pass

    return transactions


def _parse_text_lines(text: str) -> List[ParsedTransaction]:
    """Parse bank statement from raw text extraction."""
    transactions: List[ParsedTransaction] = []

    # Pattern: date followed by description and amounts
    # e.g., "22/06/17  NEFT-SALARY  50,000.00  1,25,000.00"
    line_pattern = re.compile(
        r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+"  # date
        r"(.+?)\s+"                               # description (non-greedy)
        r"([\d,]+\.\d{2})\s*"                     # first amount
        r"(?:([\d,]+\.\d{2})\s*)?"                # second amount (optional)
        r"(?:([\d,]+\.\d{2})\s*)?",               # third amount (optional, balance)
    )

    for match in line_pattern.finditer(text):
        date_str = match.group(1)
        description = match.group(2).strip()
        amt1 = match.group(3).replace(",", "")
        amt2 = (match.group(4) or "").replace(",", "")
        amt3 = (match.group(5) or "").replace(",", "")

        txn_date = extract_date(date_str)
        if not txn_date:
            continue

        balance_after: Optional[Decimal] = None
        if amt3:
            try:
                balance_after = Decimal(amt3)
            except Exception:
                pass

        if amt2:
            # Two amounts: withdrawal and deposit (one should be 0 or empty)
            try:
                w = Decimal(amt1) if amt1 else Decimal(0)
                d = Decimal(amt2) if amt2 else Decimal(0)
                if w > 0:
                    transactions.append(
                        ParsedTransaction(
                            transaction_type="DEBIT",
                            amount=w,
                            merchant=description,
                            raw_description=description,
                            transaction_date=txn_date,
                            balance_after=balance_after,
                            card_type="ACCOUNT",
                        )
                    )
                elif d > 0:
                    transactions.append(
                        ParsedTransaction(
                            transaction_type="CREDIT",
                            amount=d,
                            merchant=description,
                            raw_description=description,
                            transaction_date=txn_date,
                            balance_after=balance_after,
                            card_type="ACCOUNT",
                        )
                    )
            except Exception:
                pass
        else:
            # Single amount — guess direction from description
            try:
                amount = Decimal(amt1)
                txn_type = "DEBIT"
                if re.search(r"\b(?:CREDIT|SALARY|NEFT CR|IMPS CR|UPI CR|DEPOSIT|REFUND)\b", description, re.IGNORECASE):
                    txn_type = "CREDIT"
                transactions.append(
                    ParsedTransaction(
                        transaction_type=txn_type,
                        amount=amount,
                        merchant=description,
                        raw_description=description,
                        transaction_date=txn_date,
                        balance_after=balance_after,
                        card_type="ACCOUNT",
                    )
                )
            except Exception:
                pass

    return transactions


def _find_header_row(table: List[List[str]]) -> int:
    """Find the header row index in a table."""
    header_keywords = {"DATE", "NARRATION", "DESCRIPTION", "WITHDRAWAL", "DEPOSIT",
                       "DEBIT", "CREDIT", "BALANCE", "PARTICULARS", "AMOUNT",
                       "WITHDRAW", "CHQUE", "CHQ", "VALUE", "REF"}
    for i, row in enumerate(table):
        if i >= 5:  # Header should be in first few rows
            break
        row_text = " ".join((c or "").upper() for c in row)
        matches = sum(1 for kw in header_keywords if kw in row_text)
        if matches >= 2:
            return i
    return -1


def _clean_amount(cell: Optional[str]) -> str:
    """Clean a cell value to extract numeric amount."""
    if not cell:
        return ""
    cleaned = cell.strip().replace(",", "").replace(" ", "")
    # Remove Cr/Dr suffix
    if cleaned.upper().endswith(("CR", "DR")):
        cleaned = cleaned[:-2].strip()
    if re.match(r"^\d+\.?\d*$", cleaned) and cleaned != "0" and cleaned != "0.00":
        return cleaned
    return ""
