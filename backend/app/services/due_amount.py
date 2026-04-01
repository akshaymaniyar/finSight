"""
Extract Total Amount Due and Minimum Amount Due from credit card statement PDFs.

Supports actual formats from:
- HDFC: "TOTAL AMOUNT DUE" header, amount 2 lines later as "_ C3,03,369.00"
        "MINIMUM DUE" header, amount on next data line as "C15,170.00"
- ICICI: `3,669.53 on next line after "Total Amount due"
- IDFC: "Total Amount Due = r5,050.16 DR"
- Axis: Amount on the same or next line after "Total Payment Due"
"""

from __future__ import annotations

import re
import logging
from decimal import Decimal
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Match amounts with various Indian currency prefixes
_AMOUNT_RE = re.compile(r'[`₹CrRs._ ]*?([\d,]+\.\d{2})')
# HDFC specific: C-prefixed amounts like C3,03,369.00
_HDFC_AMOUNT_RE = re.compile(r'C([\d,]+\.\d{2})')


def _clean_amount(raw: str) -> Optional[Decimal]:
    """Clean an amount string and convert to Decimal."""
    cleaned = raw.strip().replace(',', '')
    cleaned = re.sub(r'^[`₹CrRs._ ]+', '', cleaned)
    cleaned = re.sub(r'\s*(DR|CR)\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    if not cleaned or not re.match(r'^\d+\.?\d*$', cleaned):
        return None
    try:
        val = Decimal(cleaned)
        return val if val >= 0 else None
    except Exception:
        return None


def _find_amounts_in_line(line: str) -> list[str]:
    """Extract all amount strings from a line (handles C-prefix, backtick, r-prefix)."""
    amounts = []
    # HDFC C-prefix: C3,03,369.00
    for m in _HDFC_AMOUNT_RE.finditer(line):
        amounts.append(m.group(1))
    if amounts:
        return amounts
    # Generic: backtick or r or Rs prefix
    for m in _AMOUNT_RE.finditer(line):
        amounts.append(m.group(1))
    return amounts


def extract_due_amounts(text: str) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    """Extract total amount due and minimum amount due from statement text."""
    total_due: Optional[Decimal] = None
    min_due: Optional[Decimal] = None

    lines = text.split('\n')

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        line_upper = line_stripped.upper()

        # ===================== TOTAL AMOUNT DUE =====================
        if total_due is None:

            # IDFC: "Total Amount Due = r5,050.16 DR"
            m = re.search(
                r'Total\s+Amount\s+Due\s*[=:]\s*[`₹CrRs.]*\s*([\d,]+\.?\d*)\s*(?:DR)?',
                line_stripped, re.IGNORECASE,
            )
            if m:
                total_due = _clean_amount(m.group(1))

            # HDFC/ICICI/Axis: "TOTAL AMOUNT DUE" or "TOTAL PAYMENT DUE" as header
            if total_due is None and (
                'TOTAL AMOUNT DUE' in line_upper or 'TOTAL PAYMENT DUE' in line_upper
            ):
                # Check same line for amount
                amounts = _find_amounts_in_line(line_stripped)
                if amounts:
                    total_due = _clean_amount(amounts[-1])  # last amount is usually the total

                # Check next 3 lines (HDFC has amount 2 lines after header)
                if total_due is None:
                    for offset in range(1, 4):
                        if i + offset >= len(lines):
                            break
                        next_line = lines[i + offset].strip()
                        # Skip empty or header-continuation lines
                        if not next_line or next_line.upper().startswith('RECEIVED'):
                            continue
                        amounts = _find_amounts_in_line(next_line)
                        if amounts:
                            # For HDFC: "_ C3,03,369.00" — the first amount on this line
                            total_due = _clean_amount(amounts[0])
                            break

        # ===================== MINIMUM AMOUNT DUE =====================
        if min_due is None:

            # Direct match: "Minimum Amount Due" or "MINIMUM DUE" followed by amount
            m = re.search(
                r'(?:Minimum\s+Amount\s+Due|Min\.?\s+(?:Amt\.?\s+)?Due|MINIMUM\s+DUE)[:\s=]*'
                r'[`₹CrRs.]*\s*([\d,]+\.?\d*)',
                line_stripped, re.IGNORECASE,
            )
            if m and m.group(1):
                min_due = _clean_amount(m.group(1))

            # HDFC: "MINIMUM DUE" in header, amount on next data line
            if min_due is None and 'MINIMUM DUE' in line_upper:
                for offset in range(1, 3):
                    if i + offset >= len(lines):
                        break
                    next_line = lines[i + offset].strip()
                    if not next_line:
                        continue
                    amounts = _find_amounts_in_line(next_line)
                    if amounts:
                        min_due = _clean_amount(amounts[0])
                        break

            # ICICI: "Minimum Amount due" header, amount on next line
            if min_due is None and 'MINIMUM AMOUNT DUE' in line_upper:
                for offset in range(1, 3):
                    if i + offset >= len(lines):
                        break
                    next_line = lines[i + offset].strip()
                    amounts = _find_amounts_in_line(next_line)
                    if amounts:
                        min_due = _clean_amount(amounts[0])
                        break

    logger.debug("Due amounts extracted: total=%s, min=%s", total_due, min_due)
    return total_due, min_due
