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

        IDFC format: Transaction Date | Transaction Details | EMI | FX | Amount
        Sections: YOUR TRANSACTIONS, PURCHASES, EMIs, etc.
        """
        transactions: List[ParsedTransaction] = []

        tables = extract_tables_from_pdf(pdf_bytes, password)
        if tables:
            for table in tables:
                for row in table:
                    if len(row) < 3:
                        continue
                    date_str = (row[0] or "").strip()
                    if not re.match(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", date_str):
                        continue

                    description = (row[1] or "").strip()
                    txn_type = "DEBIT"
                    amount_str = ""

                    for cell in reversed(row[2:]):
                        cell_val = (cell or "").strip()
                        if not cell_val:
                            continue
                        cleaned = cell_val.upper()
                        if cleaned.endswith("CR"):
                            txn_type = "CREDIT"
                            cleaned = cleaned[:-2].strip()
                        elif cleaned.endswith("DR"):
                            txn_type = "DEBIT"
                            cleaned = cleaned[:-2].strip()
                        cleaned = cleaned.replace(",", "").replace(" ", "")
                        if re.match(r"^\d+\.?\d*$", cleaned):
                            amount_str = cleaned
                            break

                    if not amount_str:
                        continue
                    txn_date = extract_date(date_str)
                    if not txn_date:
                        continue
                    try:
                        amount = Decimal(amount_str)
                    except Exception:
                        continue

                    if re.search(r"\b(?:PAYMENT|REFUND|CREDIT|CR)\b", description, re.IGNORECASE):
                        txn_type = "CREDIT"

                    transactions.append(
                        ParsedTransaction(
                            transaction_type=txn_type,
                            amount=amount,
                            merchant=description,
                            raw_description=description,
                            transaction_date=txn_date,
                            card_type="CREDIT_CARD",
                        )
                    )

        if not transactions:
            text = extract_text_from_pdf(pdf_bytes, password)
            if text:
                line_pattern = re.compile(
                    r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+(.+?)\s+([\d,]+\.\d{2})\s*(Cr|Dr)?",
                    re.IGNORECASE,
                )
                for match in line_pattern.finditer(text):
                    d = match.group(1)
                    desc = match.group(2).strip()
                    amt = match.group(3).replace(",", "")
                    cr_dr = (match.group(4) or "").upper()

                    txn_date = extract_date(d)
                    if not txn_date:
                        continue
                    try:
                        amount = Decimal(amt)
                    except Exception:
                        continue

                    t = "CREDIT" if cr_dr == "CR" else "DEBIT"
                    transactions.append(
                        ParsedTransaction(
                            transaction_type=t,
                            amount=amount,
                            merchant=desc,
                            raw_description=desc,
                            transaction_date=txn_date,
                            card_type="CREDIT_CARD",
                        )
                    )

        return transactions
