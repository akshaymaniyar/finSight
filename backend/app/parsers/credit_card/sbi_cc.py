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


class SBICCParser(BaseBankParser):
    bank_name = "SBI Credit Card"
    sender_emails = ["sbicard@sbicard.com"]

    def can_parse(self, from_email: str, subject: str) -> bool:
        return from_email.lower() in [e.lower() for e in self.sender_emails]

    def parse_email(
        self, subject: str, body_html: str, body_text: str
    ) -> List[ParsedTransaction]:
        text = body_text or clean_html(body_html)
        transactions: List[ParsedTransaction] = []

        # Pattern 1: "Rs {amt} was spent on your SBI Credit Card ending {card} at {merchant}"
        spend_match = re.search(
            r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+(?:was|has been)\s+spent\s+on\s+(?:your\s+)?(?:SBI\s+)?[Cc]redit\s+[Cc]ard\s+(?:ending\s+)?(\d{4})\s+at\s+([A-Za-z0-9\s&.\-/]+?)(?:\s+on\s+|\s*\.\s*|$)",
            text,
            re.IGNORECASE,
        )
        if spend_match:
            amount_str = spend_match.group(1).replace(",", "")
            card = spend_match.group(2)
            merchant = spend_match.group(3).strip()
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

        # Pattern 2: "Transaction of Rs.{amt} on SBI Card ending {card}"
        txn_match = re.search(
            r"[Tt]ransaction\s+of\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+(?:on|using)\s+(?:your\s+)?(?:SBI\s+)?(?:Credit\s+)?[Cc]ard\s+(?:ending\s+)?(\d{4})",
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

        # Pattern 3: "SBI Card ending {card} has been used for Rs.{amt} at {merchant}"
        used_match = re.search(
            r"(?:SBI\s+)?[Cc]ard\s+(?:ending\s+)?(\d{4})\s+has\s+been\s+used\s+for\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+at\s+([A-Za-z0-9\s&.\-/]+?)(?:\s+on\s+|\s*\.\s*|$)",
            text,
            re.IGNORECASE,
        )
        if used_match:
            card = used_match.group(1)
            amount_str = used_match.group(2).replace(",", "")
            merchant = used_match.group(3).strip()
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

        # Pattern 4: Payment received
        payment_match = re.search(
            r"(?:payment|refund)\s+of\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+(?:has been\s+)?(?:received|credited)\s+(?:on|to|for)\s+(?:your\s+)?(?:SBI\s+)?[Cc](?:redit\s+)?[Cc]ard\s+(?:ending\s+)?(\d{4})",
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
        """Parse SBI Card credit card PDF statement.

        SBI CC format: Transaction Date | Transaction Details | Debit Amount | Credit Amount
        Separate columns for debit and credit — cleanest format.
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
                    debit_str = (row[2] or "").strip().replace(",", "") if len(row) > 2 else ""
                    credit_str = (row[3] or "").strip().replace(",", "") if len(row) > 3 else ""

                    txn_date = extract_date(date_str)
                    if not txn_date:
                        continue

                    if debit_str and re.match(r"^\d+\.?\d*$", debit_str):
                        try:
                            amount = Decimal(debit_str)
                            transactions.append(
                                ParsedTransaction(
                                    transaction_type="DEBIT",
                                    amount=amount,
                                    merchant=description,
                                    raw_description=description,
                                    transaction_date=txn_date,
                                    card_type="CREDIT_CARD",
                                )
                            )
                        except Exception:
                            pass
                    elif credit_str and re.match(r"^\d+\.?\d*$", credit_str):
                        try:
                            amount = Decimal(credit_str)
                            transactions.append(
                                ParsedTransaction(
                                    transaction_type="CREDIT",
                                    amount=amount,
                                    merchant=description,
                                    raw_description=description,
                                    transaction_date=txn_date,
                                    card_type="CREDIT_CARD",
                                )
                            )
                        except Exception:
                            pass

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
