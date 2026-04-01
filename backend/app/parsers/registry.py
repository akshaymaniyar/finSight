"""
Parser registry: imports all parser classes and provides
lookup functions for matching emails to the correct bank parser.
"""
from __future__ import annotations

from typing import List, Optional

from app.parsers.base import BaseBankParser

# Debit / savings account parsers
from app.parsers.debit.hdfc import HDFCParser
from app.parsers.debit.sbi import SBIParser
from app.parsers.debit.icici import ICICIParser
from app.parsers.debit.axis import AxisParser
from app.parsers.debit.kotak import KotakParser
from app.parsers.debit.yes_bank import YesBankParser
from app.parsers.debit.indusind import IndusIndParser
from app.parsers.debit.pnb import PNBParser
from app.parsers.debit.bob import BOBParser
from app.parsers.debit.canara import CanaraParser
from app.parsers.debit.idfc import IDFCParser
from app.parsers.debit.indian_bank import IndianBankParser

# Credit card parsers
from app.parsers.credit_card.hdfc_cc import HDFCCCParser
from app.parsers.credit_card.sbi_cc import SBICCParser
from app.parsers.credit_card.icici_cc import ICICICCParser
from app.parsers.credit_card.axis_cc import AxisCCParser
from app.parsers.credit_card.kotak_cc import KotakCCParser
from app.parsers.credit_card.amex import AmexParser
from app.parsers.credit_card.yes_bank_cc import YesBankCCParser
from app.parsers.credit_card.indusind_cc import IndusIndCCParser
from app.parsers.credit_card.idfc_cc import IDFCCCParser

# Credit card parsers listed first so subject-based disambiguation
# takes priority over email-only matching (e.g., alerts@axisbank.com
# can be either debit or credit card).
ALL_PARSERS: List[BaseBankParser] = [
    # Credit card parsers
    HDFCCCParser(),
    SBICCParser(),
    ICICICCParser(),
    AxisCCParser(),
    KotakCCParser(),
    AmexParser(),
    YesBankCCParser(),
    IndusIndCCParser(),
    IDFCCCParser(),
    # Debit / savings account parsers
    HDFCParser(),
    SBIParser(),
    ICICIParser(),
    AxisParser(),
    KotakParser(),
    YesBankParser(),
    IndusIndParser(),
    PNBParser(),
    BOBParser(),
    CanaraParser(),
    IDFCParser(),
    IndianBankParser(),
]


def _extract_email_address(from_header: str) -> str:
    """Extract the bare email address from a From header.

    Handles formats like:
      - 'alerts@hdfcbank.net'
      - '<alerts@hdfcbank.net>'
      - 'HDFC Bank <alerts@hdfcbank.net>'
      - '"HDFC Bank" <alerts@hdfcbank.net>'
    """
    import re
    match = re.search(r'<([^>]+)>', from_header)
    if match:
        return match.group(1).strip()
    # No angle brackets — return as-is (strip whitespace)
    return from_header.strip()


# Order matters: more specific patterns first (credit card before generic bank)
_FORWARDED_SUBJECT_PATTERNS = [
    ("icici bank credit card", "ICICI Bank Credit Card"),
    ("icici bank statement", "ICICI Bank"),  # account statement, not CC
    ("hdfc bank credit card", "HDFC Bank Credit Card"),
    ("hdfc bank statement", "HDFC Bank"),
    ("axis bank credit card", "Axis Bank Credit Card"),
    ("axis bank statement", "Axis Bank"),
    ("idfc first credit card", "IDFC First Credit Card"),
    ("idfc first bank statement", "IDFC First Bank"),
    ("sbi credit card", "SBI Credit Card"),
    ("sbi statement", "State Bank of India"),
    ("kotak credit card", "Kotak Mahindra Credit Card"),
    ("kotak bank statement", "Kotak Mahindra Bank"),
]


def find_parser(from_email: str, subject: str) -> Optional[BaseBankParser]:
    """Return the first parser that can handle this email, or None.

    Also handles forwarded emails (Fwd:) by matching subject patterns
    to detect the originating bank.
    """
    # Normalize the from_email to bare address
    bare_email = _extract_email_address(from_email)

    # First try direct email match
    for parser in ALL_PARSERS:
        if parser.can_parse(bare_email, subject):
            return parser

    # If no direct match, check if this is a forwarded bank statement
    subject_lower = subject.lower()
    if subject_lower.startswith("fwd:") or subject_lower.startswith("fw:"):
        clean_subject = subject_lower.split(":", 1)[1].strip()
        for pattern, bank_name in _FORWARDED_SUBJECT_PATTERNS:
            if pattern in clean_subject:
                # Match against exact bank_name in parsers
                for parser in ALL_PARSERS:
                    if parser.bank_name == bank_name:
                        return parser
                # Fallback to partial match
                matched = find_parser_by_bank_name(bank_name)
                if matched:
                    return matched

    return None


def get_all_parsers() -> List[BaseBankParser]:
    """Return all registered parser instances."""
    return list(ALL_PARSERS)


def find_parser_by_bank_name(bank_name: str) -> Optional[BaseBankParser]:
    """Return a parser matching the given bank name (partial match)."""
    bank_lower = bank_name.lower()
    for parser in ALL_PARSERS:
        if bank_lower in parser.bank_name.lower():
            return parser
    return None


def get_all_sender_emails() -> List[str]:
    """Return a flat, deduplicated list of every sender email recognized by any parser."""
    seen: set[str] = set()
    emails: List[str] = []
    for parser in ALL_PARSERS:
        for email in parser.sender_emails:
            lower = email.lower()
            if lower not in seen:
                seen.add(lower)
                emails.append(email)
    return emails
