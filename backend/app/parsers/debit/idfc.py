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


class IDFCParser(BaseBankParser):
    bank_name = "IDFC First Bank"
    sender_emails = ["alerts@idfcfirstbank.com"]

    def can_parse(self, from_email: str, subject: str) -> bool:
        return from_email.lower() in [e.lower() for e in self.sender_emails]

    def parse_email(
        self, subject: str, body_html: str, body_text: str
    ) -> List[ParsedTransaction]:
        text = body_text or clean_html(body_html)
        transactions: List[ParsedTransaction] = []

        # Pattern 1: "Rs.{amt} has been debited from your IDFC FIRST Bank A/c ending {acct}"
        debit_match = re.search(
            r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+has\s+been\s+debited\s+from\s+(?:your\s+)?(?:IDFC\s+FIRST\s+Bank\s+)?(?:A/[Cc]|Account)\s*(?:ending\s+)?([*Xx]*\d{4,6})",
            text,
            re.IGNORECASE,
        )
        if debit_match:
            amount_str = debit_match.group(1).replace(",", "")
            acct_raw = debit_match.group(2)
            acct_num = re.sub(r"[*Xx]+", "", acct_raw)
            merchant = ""
            merch_match = re.search(
                r"(?:to|towards|at|for)\s+([A-Za-z0-9\s&.\-/]+?)(?:\s+on\s+|\s+Ref\s+|\s*\.\s*|$)",
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
                    account_number_masked=f"XX{acct_num}",
                    balance_after=_extract_balance(text),
                    card_type="ACCOUNT",
                )
            )
            return transactions

        # Pattern 2: "A/c {acct} debited with Rs.{amt}"
        debit_alt = re.search(
            r"(?:A/[Cc]|Account)\s*(?:ending\s+)?([*Xx]*\d{4,6})\s+(?:is|has been)\s+debited\s+(?:with|for|by)\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)",
            text,
            re.IGNORECASE,
        )
        if debit_alt:
            acct_raw = debit_alt.group(1)
            amount_str = debit_alt.group(2).replace(",", "")
            acct_num = re.sub(r"[*Xx]+", "", acct_raw)
            transactions.append(
                ParsedTransaction(
                    transaction_type="DEBIT",
                    amount=Decimal(amount_str),
                    raw_description=text[:500],
                    transaction_date=extract_date(text),
                    reference_id=extract_reference(text),
                    account_number_masked=f"XX{acct_num}",
                    balance_after=_extract_balance(text),
                    card_type="ACCOUNT",
                )
            )
            return transactions

        # Pattern 3: Credit
        credit_match = re.search(
            r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+has\s+been\s+credited\s+to\s+(?:your\s+)?(?:IDFC\s+FIRST\s+Bank\s+)?(?:A/[Cc]|Account)\s*(?:ending\s+)?([*Xx]*\d{4,6})",
            text,
            re.IGNORECASE,
        )
        if credit_match:
            amount_str = credit_match.group(1).replace(",", "")
            acct_raw = credit_match.group(2)
            acct_num = re.sub(r"[*Xx]+", "", acct_raw)
            transactions.append(
                ParsedTransaction(
                    transaction_type="CREDIT",
                    amount=Decimal(amount_str),
                    raw_description=text[:500],
                    transaction_date=extract_date(text),
                    reference_id=extract_reference(text),
                    account_number_masked=f"XX{acct_num}",
                    balance_after=_extract_balance(text),
                    card_type="ACCOUNT",
                )
            )
            return transactions

        # Fallback
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
        """Parse IDFC First Bank bank account PDF statement."""
        return parse_bank_account_pdf(pdf_bytes, password)


def _extract_balance(text: str) -> Optional[Decimal]:
    match = re.search(
        r"(?:Avl\.?\s*Bal|Available\s+Balance|Bal)[:\s]+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)",
        text,
        re.IGNORECASE,
    )
    if match:
        return Decimal(match.group(1).replace(",", ""))
    return None
