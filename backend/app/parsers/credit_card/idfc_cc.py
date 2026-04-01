import re
from decimal import Decimal
from typing import List

from ..base import BaseBankParser, ParsedTransaction
from ..email_utils import (
    clean_html,
    extract_account_number,
    extract_amount,
    extract_date,
    extract_reference,
)
from ..pdf_utils import extract_tables_from_pdf, extract_text_from_pdf


class IDFCCCParser(BaseBankParser):
    bank_name = "IDFC First Credit Card"
    sender_emails = [
        "creditcard@idfcfirstbank.com",
        "alerts@idfcfirstbank.com",
        "noreply@idfcfirstbank.com",
        "statement@idfcfirstbank.com",
    ]

    def can_parse(self, from_email: str, subject: str) -> bool:
        email_lower = from_email.lower()
        email_match = email_lower in [e.lower() for e in self.sender_emails]
        if not email_match:
            return False
        # statement@ sends CC statements with "Credit Card" in subject
        if email_lower == "statement@idfcfirstbank.com":
            return "credit card" in subject.lower()
        # For generic alerts@, require "credit card" in subject
        if email_lower == "alerts@idfcfirstbank.com":
            return "credit card" in subject.lower()
        return True

    def parse_email(
        self, subject: str, body_html: str, body_text: str
    ) -> List[ParsedTransaction]:
        text = body_text or clean_html(body_html)
        transactions: List[ParsedTransaction] = []

        # Pattern 1: "Rs.{amt} spent on IDFC FIRST Bank Credit Card ending {card}"
        spend_match = re.search(
            r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+(?:has been\s+)?(?:spent|used|charged)\s+(?:on|from)\s+(?:your\s+)?(?:IDFC\s+(?:FIRST\s+)?(?:Bank\s+)?)?[Cc]redit\s+[Cc]ard\s+(?:ending\s+)?(\d{4})",
            text,
            re.IGNORECASE,
        )
        if spend_match:
            amount_str = spend_match.group(1).replace(",", "")
            card = spend_match.group(2)
            merchant = ""
            merch_match = re.search(
                r"(?:at|to|towards)\s+([A-Za-z0-9\s&.\-/]+?)(?:\s+on\s+|\s*\.\s*|$)",
                text[spend_match.end():],
                re.IGNORECASE,
            )
            if merch_match:
                merchant = merch_match.group(1).strip()

            transactions.append(
                ParsedTransaction(
                    transaction_type="DEBIT",
                    amount=Decimal(amount_str),
                    merchant=merchant,
                    raw_description=text[:500],
                    transaction_date=extract_date(text),
                    reference_id=extract_reference(text),
                    account_number_masked=f"XX{card}",
                    card_type="CREDIT_CARD",
                )
            )
            return transactions

        # Pattern 2: "IDFC FIRST Bank Credit Card ending {card} for Rs.{amt}"
        used_match = re.search(
            r"(?:IDFC\s+(?:FIRST\s+)?(?:Bank\s+)?)?[Cc]redit\s+[Cc]ard\s+(?:ending\s+)?(\d{4})\s+(?:has been\s+)?(?:used\s+)?for\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)",
            text,
            re.IGNORECASE,
        )
        if used_match:
            card = used_match.group(1)
            amount_str = used_match.group(2).replace(",", "")
            merchant = ""
            merch_match = re.search(
                r"(?:at|to|towards)\s+([A-Za-z0-9\s&.\-/]+?)(?:\s+on\s+|\s*\.\s*|$)",
                text[used_match.end():],
                re.IGNORECASE,
            )
            if merch_match:
                merchant = merch_match.group(1).strip()

            transactions.append(
                ParsedTransaction(
                    transaction_type="DEBIT",
                    amount=Decimal(amount_str),
                    merchant=merchant,
                    raw_description=text[:500],
                    transaction_date=extract_date(text),
                    reference_id=extract_reference(text),
                    account_number_masked=f"XX{card}",
                    card_type="CREDIT_CARD",
                )
            )
            return transactions

        # Pattern 3: Payment / refund credited
        payment_match = re.search(
            r"(?:payment|refund)\s+of\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+(?:has been\s+)?(?:received|credited)\s+(?:on|to)\s+(?:your\s+)?(?:IDFC\s+(?:FIRST\s+)?(?:Bank\s+)?)?[Cc]redit\s+[Cc]ard\s+(?:ending\s+)?(\d{4})",
            text,
            re.IGNORECASE,
        )
        if payment_match:
            amount_str = payment_match.group(1).replace(",", "")
            card = payment_match.group(2)
            transactions.append(
                ParsedTransaction(
                    transaction_type="CREDIT",
                    amount=Decimal(amount_str),
                    raw_description=text[:500],
                    transaction_date=extract_date(text),
                    reference_id=extract_reference(text),
                    account_number_masked=f"XX{card}",
                    card_type="CREDIT_CARD",
                )
            )
            return transactions

        # Fallback
        amount = extract_amount(text)
        if amount:
            txn_type = "DEBIT"
            if re.search(r"\b(?:payment|refund|credit(?:ed)?)\b", text, re.IGNORECASE):
                txn_type = "CREDIT"
            transactions.append(
                ParsedTransaction(
                    transaction_type=txn_type,
                    amount=amount,
                    raw_description=text[:500],
                    transaction_date=extract_date(text),
                    reference_id=extract_reference(text),
                    account_number_masked=extract_account_number(text),
                    card_type="CREDIT_CARD",
                )
            )

        return transactions

    def parse_pdf(
        self, pdf_bytes: bytes, password: str = ""
    ) -> List[ParsedTransaction]:
        """Parse IDFC First credit card PDF statement.

        Real IDFC format (2025-2026):
          01 Dec 25 HP PAY CREDIT CARD Convert 5,050.16 DR
          02 Dec 25 BillDesk BBPS CC Payment/... 1,243.00 CR

        Date format: DD Mon YY (e.g., "01 Dec 25")
        Amount: AMOUNT DR/CR at end of line
        Multi-line descriptions possible.
        """
        text = extract_text_from_pdf(pdf_bytes, password)
        if not text:
            return []

        transactions: List[ParsedTransaction] = []

        # IDFC-specific pattern: DD Mon YY [DESCRIPTION] AMOUNT DR/CR
        # Description may be empty (on multi-line entries) or present
        idfc_pattern = re.compile(
            r"(\d{2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{2})\s+"
            r"(.*?)"                          # Description (may be empty)
            r"([\d,]+\.\d{2})\s+"
            r"(DR|CR)",
            re.MULTILINE,
        )

        for match in idfc_pattern.finditer(text):
            date_str = match.group(1).strip()
            raw_desc = match.group(2).strip()
            amount_str = match.group(3).replace(",", "")
            dr_cr = match.group(4).upper()

            # Parse "DD Mon YY" date
            from datetime import datetime as dt
            txn_date = None
            try:
                txn_date = dt.strptime(date_str, "%d %b %y").date()
            except ValueError:
                continue

            try:
                amount = Decimal(amount_str)
            except Exception:
                continue

            txn_type = "CREDIT" if dr_cr == "CR" else "DEBIT"

            # Clean description: remove "Convert" suffix (EMI convert prompt)
            merchant = re.sub(r"\s*Convert\s*$", "", raw_desc).strip()

            transactions.append(
                ParsedTransaction(
                    transaction_type=txn_type,
                    amount=amount,
                    merchant=merchant,
                    raw_description=raw_desc,
                    transaction_date=txn_date,
                    card_type="CREDIT_CARD",
                )
            )

        return transactions
