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


class ICICICCParser(BaseBankParser):
    bank_name = "ICICI Bank Credit Card"
    sender_emails = ["creditcards@icicibank.com", "credit_cards@icicibank.com"]

    def can_parse(self, from_email: str, subject: str) -> bool:
        return from_email.lower() in [e.lower() for e in self.sender_emails]

    def parse_email(
        self, subject: str, body_html: str, body_text: str
    ) -> List[ParsedTransaction]:
        text = body_text or clean_html(body_html)
        transactions: List[ParsedTransaction] = []

        # Pattern 1: "Rs.{amt} has been spent on your ICICI Bank Credit Card ending {card} at {merchant}"
        spend_match = re.search(
            r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+has\s+been\s+(?:spent|charged)\s+on\s+(?:your\s+)?(?:ICICI\s+Bank\s+)?[Cc]redit\s+[Cc]ard\s+(?:ending\s+)?(\d{4})",
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

        # Pattern 2: "ICICI Bank Credit Card ending {card} used for Rs.{amt} at {merchant}"
        used_match = re.search(
            r"(?:ICICI\s+Bank\s+)?[Cc]redit\s+[Cc]ard\s+(?:ending\s+)?(\d{4})\s+(?:has been\s+)?used\s+for\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+at\s+([A-Za-z0-9\s&.\-/]+?)(?:\s+on\s+|\s*\.\s*|$)",
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

        # Pattern 3: "Transaction of Rs.{amt} on ICICI Credit Card {card}"
        txn_match = re.search(
            r"[Tt]ransaction\s+of\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+on\s+(?:your\s+)?(?:ICICI\s+(?:Bank\s+)?)?[Cc]redit\s+[Cc]ard\s+(?:ending\s+)?(\d{4})",
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

        # Pattern 4: Payment / refund
        payment_match = re.search(
            r"(?:payment|refund)\s+of\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+(?:has been\s+)?(?:received|credited)\s+(?:on|to)\s+(?:your\s+)?(?:ICICI\s+(?:Bank\s+)?)?[Cc]redit\s+[Cc]ard\s+(?:ending\s+)?(\d{4})",
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
        """Parse ICICI credit card PDF statement.

        ICICI CC actual format (from real statements):
        - Table columns: Date | SerNo. | Transaction Details | Reward Points | Intl. amount | Amount (in `)
        - pdfplumber may extract each row as a separate table
        - Text format: DD/MM/YYYY REFNO DESCRIPTION [REWARD_PTS] AMOUNT [CR]
        """
        transactions: List[ParsedTransaction] = []

        # Strategy 1: Table extraction (handles per-row tables)
        tables = extract_tables_from_pdf(pdf_bytes, password)
        if tables:
            for table in tables:
                for row in table:
                    if not row or len(row) < 3:
                        continue
                    date_str = (row[0] or "").strip()
                    if not re.match(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", date_str):
                        continue

                    # ICICI table: [Date, SerNo, Description, RewardPts, IntlAmt, Amount]
                    # SerNo is a long digit string (reference ID)
                    ref_id = ""
                    description = ""
                    if len(row) >= 6:
                        ref_id = (row[1] or "").strip()
                        description = (row[2] or "").strip().replace("\n", " ")
                    elif len(row) >= 3:
                        # Fewer columns — try to parse from available data
                        description = (row[1] or "").strip().replace("\n", " ")

                    # Get amount from last column
                    amount_str = ""
                    txn_type = "DEBIT"
                    for cell in reversed(row):
                        cell_val = (cell or "").strip()
                        if not cell_val:
                            continue
                        cleaned = cell_val.replace(",", "").replace(" ", "").replace("`", "")
                        if cleaned.upper().endswith("CR"):
                            txn_type = "CREDIT"
                            cleaned = cleaned[:-2].strip()
                        if re.match(r"^\d+\.\d{2}$", cleaned):
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

                    transactions.append(
                        ParsedTransaction(
                            transaction_type=txn_type,
                            amount=amount,
                            merchant=description,
                            raw_description=description,
                            transaction_date=txn_date,
                            reference_id=ref_id,
                            card_type="CREDIT_CARD",
                        )
                    )

        # Strategy 2: Text-based extraction (more reliable for ICICI)
        text = extract_text_from_pdf(pdf_bytes, password)
        if text:
            text_txns = self._parse_statement_text(text)
            # Use text results if we got more transactions
            if len(text_txns) > len(transactions):
                transactions = text_txns

        return transactions

    def _parse_statement_text(self, text: str) -> List[ParsedTransaction]:
        """Parse ICICI CC statement from extracted text.

        Actual ICICI format from real PDFs:
          23/11/2025 12388149969 AMAZON PAY IN E COMMERC BANGALORE 42 845.38
          02/12/2025 12434409166 BBPS Payment received 0 6,982.47 CR

        Pattern: DATE REFNO(11+ digits) DESCRIPTION [REWARD_PTS] AMOUNT [CR]
        """
        transactions: List[ParsedTransaction] = []

        # Primary pattern: date + long reference number + description + amount [CR]
        line_pattern = re.compile(
            r"(\d{2}/\d{2}/\d{4})\s+"     # Date DD/MM/YYYY
            r"(\d{10,})\s+"                # Reference number (10+ digits)
            r"(.+?)\s+"                    # Description (non-greedy)
            r"([\d,]+\.\d{2})"             # Amount
            r"\s*(CR)?$",                  # Optional CR suffix
            re.MULTILINE,
        )
        for match in line_pattern.finditer(text):
            date_str = match.group(1)
            ref_id = match.group(2)
            raw_desc = match.group(3).strip()
            amount_str = match.group(4).replace(",", "")
            is_credit = bool(match.group(5))

            txn_date = extract_date(date_str)
            if not txn_date:
                continue

            try:
                amount = Decimal(amount_str)
            except Exception:
                continue

            # Clean description: remove trailing reward points (single number at end)
            merchant = re.sub(r"\s+[-]?\d{1,3}$", "", raw_desc).strip()

            txn_type = "CREDIT" if is_credit else "DEBIT"
            if re.search(r"\b(?:Payment received|REFUND|CR-)\b", merchant, re.IGNORECASE):
                txn_type = "CREDIT"

            transactions.append(
                ParsedTransaction(
                    transaction_type=txn_type,
                    amount=amount,
                    merchant=merchant,
                    raw_description=raw_desc,
                    transaction_date=txn_date,
                    reference_id=ref_id,
                    card_type="CREDIT_CARD",
                )
            )

        # Fallback: generic pattern if ICICI-specific pattern finds nothing
        if not transactions:
            fallback_pattern = re.compile(
                r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+(.+?)\s+([\d,]+\.\d{2})\s*(Cr|Dr)?",
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
