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


class SBIParser(BaseBankParser):
    bank_name = "State Bank of India"
    sender_emails = ["alerts@sbi.co.in", "donotreply@sbi.co.in"]

    def can_parse(self, from_email: str, subject: str) -> bool:
        return from_email.lower() in [e.lower() for e in self.sender_emails]

    def parse_email(
        self, subject: str, body_html: str, body_text: str
    ) -> List[ParsedTransaction]:
        text = body_text or clean_html(body_html)
        transactions: List[ParsedTransaction] = []

        # Pattern 1: "Your a/c no. XX1234 is debited by Rs 1,000.00 on 01-04-2026"
        debit_match = re.search(
            r"(?:a/c|account)\s*(?:no\.?\s*)?([*Xx]+\d{4,6})\s+(?:is|has been)\s+debited\s+(?:by|for|with)\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)",
            text,
            re.IGNORECASE,
        )
        if debit_match:
            acct = debit_match.group(1)
            amount_str = debit_match.group(2).replace(",", "")
            merchant = ""
            merch_match = re.search(
                r"(?:transfer\s+to|to|towards)\s+([A-Za-z0-9\s&.\-/]+?)(?:\s+on\s+|\s+ref\s+|\s*\.\s*|$)",
                text[debit_match.end() :],
                re.IGNORECASE,
            )
            if merch_match:
                merchant = merch_match.group(1).strip()

            acct_num = re.sub(r"[*Xx]+", "", acct)
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

        # Pattern 2: "debited by Rs {amt}" (simpler)
        debit_simple = re.search(
            r"debited\s+(?:by|for|with)\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)",
            text,
            re.IGNORECASE,
        )
        if debit_simple:
            amount_str = debit_simple.group(1).replace(",", "")
            transactions.append(
                ParsedTransaction(
                    transaction_type="DEBIT",
                    amount=Decimal(amount_str),
                    raw_description=text[:500],
                    transaction_date=extract_date(text),
                    reference_id=extract_reference(text),
                    account_number_masked=extract_account_number(text),
                    balance_after=_extract_balance(text),
                    card_type="ACCOUNT",
                )
            )
            return transactions

        # Pattern 3: "Rs.{amt} credited to your a/c"
        credit_match = re.search(
            r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+(?:has been\s+)?credited\s+(?:to\s+)?(?:your\s+)?(?:a/c|account)",
            text,
            re.IGNORECASE,
        )
        if credit_match:
            amount_str = credit_match.group(1).replace(",", "")
            sender = ""
            sender_match = re.search(
                r"(?:from|by)\s+([A-Za-z0-9\s&.\-/]+?)(?:\s+on\s+|\s+ref\s+|\s*\.\s*|$)",
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
                    account_number_masked=extract_account_number(text),
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
        """Parse State Bank of India bank account PDF statement."""
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
