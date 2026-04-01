import re
from decimal import Decimal
from typing import List, Optional

from ..base import BaseBankParser, ParsedTransaction
from ..pdf_bank_statement import parse_bank_account_pdf
from ..email_utils import (
    clean_html,
    extract_account_number,
    extract_amount,
    extract_date,
    extract_reference,
)


class HDFCParser(BaseBankParser):
    bank_name = "HDFC Bank"
    sender_emails = ["alerts@hdfcbank.net", "noreply@hdfcbank.net"]

    def can_parse(self, from_email: str, subject: str) -> bool:
        return from_email.lower() in [e.lower() for e in self.sender_emails]

    def parse_email(
        self, subject: str, body_html: str, body_text: str
    ) -> List[ParsedTransaction]:
        text = body_text or clean_html(body_html)
        transactions: List[ParsedTransaction] = []

        # Pattern 1: "Rs.{amt} debited from a/c *{acct}"
        debit_match = re.search(
            r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+(?:has been\s+)?debited\s+from\s+(?:a/c|account|A/C)\s*[*Xx]*(\d{4,6})",
            text,
            re.IGNORECASE,
        )
        if debit_match:
            amount_str = debit_match.group(1).replace(",", "")
            acct = debit_match.group(2)
            merchant = ""
            merch_match = re.search(
                r"(?:to|towards|at|for)\s+([A-Za-z0-9\s&.\-/]+?)(?:\s+on\s+|\s+via\s+|\s*\.\s*|$)",
                text[debit_match.end() :],
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
                    account_number_masked=f"XX{acct}",
                    balance_after=_extract_balance(text),
                    card_type="ACCOUNT",
                )
            )
            return transactions

        # Pattern 2: "Rs {amt} spent on HDFC Bank Card ending {acct} at {merchant}"
        spend_match = re.search(
            r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+spent\s+on\s+HDFC\s+Bank\s+(?:Debit\s+)?Card\s+ending\s+(\d{4})\s+at\s+(.+?)(?:\s+on\s+|\.\s*|$)",
            text,
            re.IGNORECASE,
        )
        if spend_match:
            amount_str = spend_match.group(1).replace(",", "")
            acct = spend_match.group(2)
            merchant = spend_match.group(3).strip()
            transactions.append(
                ParsedTransaction(
                    transaction_type="DEBIT",
                    amount=Decimal(amount_str),
                    merchant=merchant,
                    raw_description=text[:500],
                    transaction_date=extract_date(text),
                    reference_id=extract_reference(text),
                    account_number_masked=f"XX{acct}",
                    card_type="DEBIT_CARD",
                )
            )
            return transactions

        # Pattern 3: Credit - "Rs.{amt} credited to a/c *{acct}"
        credit_match = re.search(
            r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+(?:has been\s+)?credited\s+to\s+(?:a/c|account|A/C)\s*[*Xx]*(\d{4,6})",
            text,
            re.IGNORECASE,
        )
        if credit_match:
            amount_str = credit_match.group(1).replace(",", "")
            acct = credit_match.group(2)
            sender = ""
            sender_match = re.search(
                r"(?:from|by)\s+([A-Za-z0-9\s&.\-/]+?)(?:\s+on\s+|\s+via\s+|\s*\.\s*|$)",
                text[credit_match.end() :],
                re.IGNORECASE,
            )
            if sender_match:
                sender = sender_match.group(1).strip()

            transactions.append(
                ParsedTransaction(
                    transaction_type="CREDIT",
                    amount=Decimal(amount_str),
                    merchant=sender,
                    raw_description=text[:500],
                    transaction_date=extract_date(text),
                    reference_id=extract_reference(text),
                    account_number_masked=f"XX{acct}",
                    balance_after=_extract_balance(text),
                    card_type="ACCOUNT",
                )
            )
            return transactions

        # Fallback: generic debit/credit detection
        amount = extract_amount(text)
        if amount:
            txn_type = "DEBIT"
            if re.search(r"\bcredit(?:ed)?\b", text, re.IGNORECASE):
                txn_type = "CREDIT"
            transactions.append(
                ParsedTransaction(
                    transaction_type=txn_type,
                    amount=amount,
                    raw_description=text[:500],
                    transaction_date=extract_date(text),
                    reference_id=extract_reference(text),
                    account_number_masked=extract_account_number(text),
                    balance_after=_extract_balance(text),
                    card_type="ACCOUNT",
                )
            )

        return transactions


    def parse_pdf(
        self, pdf_bytes: bytes, password: str = ""
    ) -> List[ParsedTransaction]:
        """Parse HDFC bank account PDF statement."""
        return parse_bank_account_pdf(pdf_bytes, password)


def _extract_balance(text: str) -> Optional[Decimal]:
    """Extract available balance from HDFC alert text."""
    match = re.search(
        r"(?:Avl\.?\s*Bal|Available\s+Balance|Bal)[:\s]+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)",
        text,
        re.IGNORECASE,
    )
    if match:
        return Decimal(match.group(1).replace(",", ""))
    return None
