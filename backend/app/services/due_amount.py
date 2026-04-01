"""
Extract Total Amount Due and Minimum Amount Due from credit card statement PDFs.

Supports actual formats from:
- ICICI: `3,669.53 on next line after "Total Amount due"
- HDFC: C1,09,282.00 with C prefix instead of rupee symbol
- IDFC: r5,050.16 DR after "Total Amount Due ="
- Axis: Amount on the same or next line after "Total Payment Due"
"""

from __future__ import annotations

import re
import logging
from decimal import Decimal
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def _clean_amount(raw: str) -> Optional[Decimal]:
    """Clean an amount string and convert to Decimal."""
    cleaned = raw.strip()
    # Remove currency prefixes (`, C, r, Rs., INR, etc.)
    cleaned = re.sub(r'^[`₹CrRs.INR\s]+', '', cleaned)
    # Remove DR/CR suffix
    cleaned = re.sub(r'\s*(DR|CR)\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace(',', '').strip()
    if not cleaned or not re.match(r'^\d+\.?\d*$', cleaned):
        return None
    try:
        val = Decimal(cleaned)
        return val if val >= 0 else None
    except Exception:
        return None


def extract_due_amounts(text: str) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    """Extract total amount due and minimum amount due from statement text.

    Returns (total_due, min_due). Either can be None if not found.
    """
    total_due: Optional[Decimal] = None
    min_due: Optional[Decimal] = None

    lines = text.split('\n')

    for i, line in enumerate(lines):
        line_upper = line.upper().strip()

        # --- TOTAL AMOUNT DUE ---
        if total_due is None:
            # Pattern 1 (IDFC): "Total Amount Due = r5,050.16 DR"
            m = re.search(
                r'Total\s+Amount\s+Due\s*[=:]\s*[`₹CrRs.]*\s*([\d,]+\.?\d*)\s*(?:DR)?',
                line, re.IGNORECASE,
            )
            if m:
                total_due = _clean_amount(m.group(1))

            # Pattern 2 (ICICI): "Total Amount due" on this line, amount on next line
            if total_due is None and 'TOTAL AMOUNT DUE' in line_upper:
                # Check same line for amount
                amounts = re.findall(r'[`₹CrRs.]*\s*([\d,]+\.\d{2})', line)
                if amounts:
                    total_due = _clean_amount(amounts[0])

                # Check next line
                if total_due is None and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    amounts = re.findall(r'[`₹CrRs.]*\s*([\d,]+\.\d{2})', next_line)
                    if amounts:
                        total_due = _clean_amount(amounts[0])

            # Pattern 3 (Axis): "Total Payment Due"
            if total_due is None and 'TOTAL PAYMENT DUE' in line_upper:
                amounts = re.findall(r'[`₹CrRs.]*\s*([\d,]+\.\d{2})', line)
                if amounts:
                    total_due = _clean_amount(amounts[0])
                if total_due is None and i + 1 < len(lines):
                    amounts = re.findall(r'[`₹CrRs.]*\s*([\d,]+\.\d{2})', lines[i + 1])
                    if amounts:
                        total_due = _clean_amount(amounts[0])

        # --- MINIMUM AMOUNT DUE ---
        if min_due is None:
            m = re.search(
                r'(?:Minimum\s+Amount\s+Due|Min\.?\s+(?:Amt\.?\s+)?Due|Minimum\s+Due|MINIMUM\s+DUE)[:\s=]*'
                r'[`₹CrRs.]*\s*([\d,]+\.?\d*)',
                line, re.IGNORECASE,
            )
            if m:
                min_due = _clean_amount(m.group(1))

            # ICICI: min due on separate line
            if min_due is None and 'MINIMUM AMOUNT DUE' in line_upper:
                if i + 1 < len(lines):
                    amounts = re.findall(r'[`₹CrRs.]*\s*([\d,]+\.\d{2})', lines[i + 1])
                    if amounts:
                        min_due = _clean_amount(amounts[0])

    logger.debug("Due amounts extracted: total=%s, min=%s", total_due, min_due)
    return total_due, min_due
