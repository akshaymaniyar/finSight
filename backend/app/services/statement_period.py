"""
Extract statement period/month from credit card and bank statement PDFs.

Parses the billing period or statement date from the first page text
to determine the correct month the statement belongs to.
"""

from __future__ import annotations

import re
import logging
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)

MONTH_NAMES = {
    'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
    'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6,
    'jul': 7, 'july': 7, 'aug': 8, 'august': 8, 'sep': 9, 'september': 9,
    'oct': 10, 'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12,
}


def _parse_date_flexible(date_str: str) -> Optional[date]:
    """Parse various date formats found in Indian bank statements."""
    date_str = date_str.strip().rstrip('.')

    # DD/Mon/YYYY (IDFC): 19/Dec/2025
    m = re.match(r'(\d{1,2})/(\w{3,9})/(\d{4})', date_str)
    if m:
        month = MONTH_NAMES.get(m.group(2).lower())
        if month:
            return date(int(m.group(3)), month, int(m.group(1)))

    # DD Mon, YYYY (HDFC): 15 Mar, 2026
    m = re.match(r'(\d{1,2})\s+(\w{3,9}),?\s+(\d{4})', date_str)
    if m:
        month = MONTH_NAMES.get(m.group(2).lower())
        if month:
            return date(int(m.group(3)), month, int(m.group(1)))

    # Month DD, YYYY (ICICI/Axis): December 18, 2025
    m = re.match(r'(\w{3,9})\s+(\d{1,2}),?\s+(\d{4})', date_str)
    if m:
        month = MONTH_NAMES.get(m.group(1).lower())
        if month:
            return date(int(m.group(3)), month, int(m.group(2)))

    # DD-MM-YYYY
    m = re.match(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', date_str)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))

    # YYYY-MM-DD
    m = re.match(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', date_str)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    return None


def extract_statement_month(text: str, subject: str = "") -> Optional[date]:
    """Extract the statement month from PDF text or email subject.

    Returns the first day of the statement's billing month.
    """

    # --- Try PDF text patterns ---

    # HDFC: "Billing Period 16 Feb, 2026 - 15 Mar, 2026"
    m = re.search(
        r'Billing\s+Period\s+(.+?)\s*[-–]\s*(.+?)(?:\n|$)',
        text, re.IGNORECASE,
    )
    if m:
        end_date = _parse_date_flexible(m.group(2).strip())
        if end_date:
            return end_date.replace(day=1)

    # HDFC: "Statement Date 15 Mar, 2026"
    m = re.search(
        r'Statement\s+Date\s+(\d{1,2}\s+\w{3,9},?\s+\d{4})',
        text, re.IGNORECASE,
    )
    if m:
        stmt_date = _parse_date_flexible(m.group(1))
        if stmt_date:
            return stmt_date.replace(day=1)

    # IDFC: "20/Nov/2025 - 19/Dec/2025" at the top
    m = re.search(
        r'(\d{1,2}/\w{3,9}/\d{4})\s*[-–]\s*(\d{1,2}/\w{3,9}/\d{4})',
        text,
    )
    if m:
        end_date = _parse_date_flexible(m.group(2))
        if end_date:
            return end_date.replace(day=1)

    # ICICI: "Statement for the period November 19, 2025 to December 18, 2025"
    m = re.search(
        r'(?:period|from)\s+(\w+\s+\d{1,2},?\s+\d{4})\s+to\s+(\w+\s+\d{1,2},?\s+\d{4})',
        text, re.IGNORECASE,
    )
    if m:
        end_date = _parse_date_flexible(m.group(2))
        if end_date:
            return end_date.replace(day=1)

    # ICICI bank: "Statement...from February 01, 2026 to February 28, 2026"
    m = re.search(
        r'from\s+(\w+\s+\d{1,2},?\s+\d{4})\s+to\s+(\w+\s+\d{1,2},?\s+\d{4})',
        text, re.IGNORECASE,
    )
    if m:
        end_date = _parse_date_flexible(m.group(2))
        if end_date:
            return end_date.replace(day=1)

    # ICICI: "as on February 28, 2026"
    m = re.search(r'as\s+on\s+(\w+\s+\d{1,2},?\s+\d{4})', text, re.IGNORECASE)
    if m:
        d = _parse_date_flexible(m.group(1))
        if d:
            return d.replace(day=1)

    # Axis: "Statement Period 16-Dec-2025 to 15-Jan-2026"
    m = re.search(
        r'Statement\s+Period\s+(.+?)\s+to\s+(.+?)(?:\n|$)',
        text, re.IGNORECASE,
    )
    if m:
        end_date = _parse_date_flexible(m.group(2).strip())
        if end_date:
            return end_date.replace(day=1)

    # --- Try email subject patterns ---
    if subject:
        subj_lower = subject.lower()

        # "Statement - March-2026" or "Statement - February-2026"
        m = re.search(r'(\w+)[-\s]+(\d{4})\s*$', subject)
        if m:
            month = MONTH_NAMES.get(m.group(1).lower())
            if month:
                return date(int(m.group(2)), month, 1)

        # "period November 19, 2025 to December 18, 2025"
        m = re.search(
            r'period\s+\w+\s+\d{1,2},?\s+\d{4}\s+to\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})',
            subj_lower,
        )
        if m:
            month = MONTH_NAMES.get(m.group(1))
            if month:
                return date(int(m.group(3)), month, 1)

        # "January 2026" or "December 2025" in subject
        m = re.search(r'(\w+)\s+(\d{4})', subject)
        if m:
            month = MONTH_NAMES.get(m.group(1).lower())
            if month:
                return date(int(m.group(2)), month, 1)

    return None
