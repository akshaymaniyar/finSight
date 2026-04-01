import re
from decimal import Decimal
from typing import List

from ..base import BaseBankParser, ParsedTransaction
from ..pdf_utils import extract_tables_from_pdf, extract_text_from_pdf
from ..email_utils import (
    clean_html,
    extract_account_number,
    extract_amount,
    extract_date,
    extract_reference,
)


class IndusIndCCParser(BaseBankParser):
    bank_name = "IndusInd Bank Credit Card"
    sender_emails = ["alerts@indusind.com"]

    def can_parse(self, from_email: str, subject: str) -> bool:
        email_match = from_email.lower() in [e.lower() for e in self.sender_emails]
        if not email_match:
            return False
        return "credit card" in subject.lower()

    def parse_email(
        self, subject: str, body_html: str, body_text: str
    ) -> List[ParsedTransaction]:
        text = body_text or clean_html(body_html)
        transactions: List[ParsedTransaction] = []

        # Pattern 1: "Rs.{amt} spent on your IndusInd Bank Credit Card ending {card}"
        spend_match = re.search(
            r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+(?:has been\s+)?spent\s+on\s+(?:your\s+)?(?:IndusInd\s+Bank\s+)?[Cc]redit\s+[Cc]ard\s+(?:ending\s+)?(\d{4})",
            text,
            re.IGNORECASE,
        )
        if spend_match:
            amount_str = spend_match.group(1).replace(",", "")
            card = spend_match.group(2)
            merchant = ""
            merch_match = re.search(
                r"(?:at|to|towards)\s+([A-Za-z0-9\s&.\-/]+?)(?:\s+on\s+|\s*\.\s*|$)",
                text[spend_match.end() :],
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

        # Pattern 2: "Transaction of Rs.{amt} on IndusInd Credit Card ending {card}"
        txn_match = re.search(
            r"[Tt]ransaction\s+of\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+(?:on|using)\s+(?:your\s+)?(?:IndusInd\s+(?:Bank\s+)?)?[Cc]redit\s+[Cc]ard\s+(?:ending\s+)?(\d{4})",
            text,
            re.IGNORECASE,
        )
        if txn_match:
            amount_str = txn_match.group(1).replace(",", "")
            card = txn_match.group(2)
            merchant = ""
            merch_match = re.search(
                r"(?:at|to|towards)\s+([A-Za-z0-9\s&.\-/]+?)(?:\s+on\s+|\s*\.\s*|$)",
                text[txn_match.end() :],
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

        # Pattern 3: "IndusInd Credit Card ending {card} used for Rs.{amt}"
        used_match = re.search(
            r"(?:IndusInd\s+(?:Bank\s+)?)?[Cc]redit\s+[Cc]ard\s+(?:ending\s+)?(\d{4})\s+(?:has been\s+)?used\s+for\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)",
            text,
            re.IGNORECASE,
        )
        if used_match:
            card = used_match.group(1)
            amount_str = used_match.group(2).replace(",", "")
            merchant = ""
            merch_match = re.search(
                r"(?:at|to|towards)\s+([A-Za-z0-9\s&.\-/]+?)(?:\s+on\s+|\s*\.\s*|$)",
                text[used_match.end() :],
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

        # Pattern 4: Payment / refund
        payment_match = re.search(
            r"(?:payment|refund)\s+of\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+(?:has been\s+)?(?:received|credited)\s+(?:on|to)\s+(?:your\s+)?(?:IndusInd\s+(?:Bank\s+)?)?[Cc]redit\s+[Cc]ard\s+(?:ending\s+)?(\d{4})",
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
        """Parse credit card PDF statement."""
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
                        cell_val = (cell or "").strip().upper()
                        if not cell_val:
                            continue
                        if cell_val in ("CR", "DR"):
                            txn_type = "CREDIT" if cell_val == "CR" else "DEBIT"
                            continue
                        cleaned = cell_val.replace(",", "").replace(" ", "")
                        if cleaned.endswith("CR"):
                            txn_type = "CREDIT"
                            cleaned = cleaned[:-2].strip()
                        elif cleaned.endswith("DR"):
                            txn_type = "DEBIT"
                            cleaned = cleaned[:-2].strip()
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
