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


class HDFCCCParser(BaseBankParser):
    bank_name = "HDFC Bank Credit Card"
    sender_emails = [
        "creditcardalerts@hdfcbank.net",
        "creditcard.alerts@hdfcbank.net",
        "alerts@hdfcbank.net",
        "emailstatements.cards@hdfcbank.net",
    ]

    def can_parse(self, from_email: str, subject: str) -> bool:
        email_lower = from_email.lower()
        email_match = email_lower in [e.lower() for e in self.sender_emails]
        if not email_match:
            return False
        # For alerts@hdfcbank.net, require "credit card" in subject
        if email_lower == "alerts@hdfcbank.net":
            return "credit card" in subject.lower()
        # emailstatements.cards@ is always CC statements
        # creditcardalerts@ is always CC
        return True

    def parse_email(
        self, subject: str, body_html: str, body_text: str
    ) -> List[ParsedTransaction]:
        text = body_text or clean_html(body_html)
        transactions: List[ParsedTransaction] = []

        # Pattern 1: "Rs {amt} spent on your HDFC Bank Credit Card ending {card}"
        spend_match = re.search(
            r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+(?:has been\s+)?spent\s+on\s+(?:your\s+)?(?:HDFC\s+Bank\s+)?[Cc]redit\s+[Cc]ard\s+(?:ending\s+)?(\d{4})",
            text,
            re.IGNORECASE,
        )
        if spend_match:
            amount_str = spend_match.group(1).replace(",", "")
            card = spend_match.group(2)
            merchant = ""
            merch_match = re.search(
                r"(?:at|to|towards)\s+([A-Za-z0-9\s&.\-/]+?)(?:\s+on\s+|\s+Ref\s+|\s*\.\s*|$)",
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

        # Pattern 2: "Thank you for using your HDFC Bank Credit Card ending {card} for Rs.{amt} at {merchant}"
        thank_match = re.search(
            r"[Cc]redit\s+[Cc]ard\s+(?:ending\s+)?(\d{4})\s+for\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+at\s+([A-Za-z0-9\s&.\-/]+?)(?:\s+on\s+|\s*\.\s*|$)",
            text,
            re.IGNORECASE,
        )
        if thank_match:
            card = thank_match.group(1)
            amount_str = thank_match.group(2).replace(",", "")
            merchant = thank_match.group(3).strip()
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

        # Pattern 3: "A transaction of Rs.{amt} has been made on your HDFC Bank Credit Card ending {card}"
        txn_match = re.search(
            r"transaction\s+of\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+has\s+been\s+made\s+on\s+(?:your\s+)?(?:HDFC\s+Bank\s+)?[Cc]redit\s+[Cc]ard\s+(?:ending\s+)?(\d{4})",
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

        # Pattern 4: Payment / credit on card
        credit_match = re.search(
            r"(?:payment|refund)\s+of\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+(?:has been\s+)?(?:received|credited)\s+(?:on|to)\s+(?:your\s+)?(?:HDFC\s+Bank\s+)?[Cc]redit\s+[Cc]ard\s+(?:ending\s+)?(\d{4})",
            text,
            re.IGNORECASE,
        )
        if credit_match:
            amount_str = credit_match.group(1).replace(",", "")
            card = credit_match.group(2)
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
        """Parse HDFC credit card PDF statement.

        Real HDFC CC PDF format (2025-2026):
          17/01/2026| 11:57 RAINBOW CHILDRENS MEDIBANGALORE + 25 C 792.00 l
          02/02/2026| 03:54 BPPY CC PAYMENT ... + C 1,05,974.00 l
          03/02/2026| 00:00 FLIPKART PAYMENTSGURGAON - 440 + C 13,337.00 l

        Text-based extraction is more reliable than tables for HDFC.
        """
        text = extract_text_from_pdf(pdf_bytes, password)
        if not text:
            return []
        return self._parse_statement_text(text)

    def _parse_statement_text(self, text: str) -> List[ParsedTransaction]:
        """Parse HDFC CC statement from extracted text."""
        transactions: List[ParsedTransaction] = []

        # Primary pattern for actual HDFC CC statements:
        # DD/MM/YYYY| HH:MM DESCRIPTION [+/-] [REWARD_PTS] C AMOUNT l
        # The "C" before amount means charge. Credits have "Cr" suffix on amount.
        hdfc_pattern = re.compile(
            r"(\d{2}/\d{2}/\d{4})\|\s*"      # Date with pipe separator
            r"\d{2}:\d{2}\s+"                  # Time HH:MM
            r"(.+?)\s+"                        # Description (non-greedy)
            r"C\s+"                             # "C" marker before amount
            r"([\d,]+\.\d{2})"                 # Amount (with Indian comma format)
            r"\s*l",                            # Trailing "l" bullet
            re.MULTILINE,
        )
        for match in hdfc_pattern.finditer(text):
            date_str = match.group(1)
            raw_desc = match.group(2).strip()
            amount_str = match.group(3).replace(",", "")

            txn_date = extract_date(date_str)
            if not txn_date:
                continue
            try:
                amount = Decimal(amount_str)
            except Exception:
                continue

            # Detect credits: CC PAYMENT, CASHBACK, REVERSAL, Cr in desc
            txn_type = "DEBIT"
            if re.search(
                r"\b(?:CC PAYMENT|PAYMENT RECEIVED|CASHBACK|REVERSAL|REFUND|CR)\b",
                raw_desc, re.IGNORECASE,
            ):
                txn_type = "CREDIT"

            # Clean description: remove trailing reward points like "+ 25" or "- 440 +"
            merchant = re.sub(r"\s*[-+]\s*\d*\s*[-+]?\s*$", "", raw_desc).strip()
            # Remove city at end (words in ALL CAPS at very end)
            # Keep the full description as raw_description

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

        # Fallback: generic DD/MM/YYYY pattern (older HDFC format or Cr/Dr style)
        if not transactions:
            fallback_pattern = re.compile(
                r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+([\d,]+\.\d{2})\s*(Cr|Dr)?",
                re.IGNORECASE,
            )
            for match in fallback_pattern.finditer(text):
                date_str = match.group(1)
                description = match.group(2).strip()
                amount_str = match.group(3).replace(",", "")
                cr_dr = (match.group(4) or "").upper()

                txn_date = extract_date(date_str)
                if not txn_date:
                    continue
                try:
                    amount = Decimal(amount_str)
                except Exception:
                    continue

                txn_type = "CREDIT" if cr_dr == "CR" else "DEBIT"
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

        return transactions
