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


class ICICIParser(BaseBankParser):
    bank_name = "ICICI Bank"
    sender_emails = ["alert@icicibank.com", "noreply@icicibank.com"]

    def can_parse(self, from_email: str, subject: str) -> bool:
        return from_email.lower() in [e.lower() for e in self.sender_emails]

    def parse_email(
        self, subject: str, body_html: str, body_text: str
    ) -> List[ParsedTransaction]:
        text = body_text or clean_html(body_html)
        transactions: List[ParsedTransaction] = []

        # Pattern 1: "A/C {acct} debited with Rs {amt} on {date}"
        debit_match = re.search(
            r"(?:A/C|a/c|Account)\s*([*Xx]*\d{4,6})\s+(?:has been\s+)?debited\s+(?:with|for)\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)",
            text,
            re.IGNORECASE,
        )
        if debit_match:
            acct_raw = debit_match.group(1)
            amount_str = debit_match.group(2).replace(",", "")
            acct_num = re.sub(r"[*Xx]+", "", acct_raw)
            merchant = ""
            merch_match = re.search(
                r"(?:to|towards|at|Info)[:\s]+([A-Za-z0-9\s&.\-/]+?)(?:\s+on\s+|\s+Ref\s+|\s*\.\s*|$)",
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

        # Pattern 2: "Rs {amt} debited from your ICICI Bank A/C {acct}"
        debit_alt = re.search(
            r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+(?:has been\s+)?debited\s+from\s+(?:your\s+)?(?:ICICI\s+Bank\s+)?(?:A/C|a/c|Account)\s*([*Xx]*\d{4,6})",
            text,
            re.IGNORECASE,
        )
        if debit_alt:
            amount_str = debit_alt.group(1).replace(",", "")
            acct_raw = debit_alt.group(2)
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
            r"(?:A/C|a/c|Account)\s*([*Xx]*\d{4,6})\s+(?:has been\s+)?credited\s+(?:with|for)\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)",
            text,
            re.IGNORECASE,
        )
        if credit_match:
            acct_raw = credit_match.group(1)
            amount_str = credit_match.group(2).replace(",", "")
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
        """Parse ICICI Bank savings account PDF statement.

        Real ICICI format:
          DATE MODE PARTICULARS DEPOSITS WITHDRAWALS BALANCE
          02-02-2026 BANK/102596957278/... 5,050.16 49,36,324.41
          09-02-2026 CMS TRANSACTION 528.93 48,13,275.92

        Multi-line particulars are common. Text-based extraction works best.
        """
        from ..pdf_utils import extract_text_from_pdf

        text = extract_text_from_pdf(pdf_bytes, password)
        if not text:
            return parse_bank_account_pdf(pdf_bytes, password)

        transactions: List[ParsedTransaction] = []

        # Split text into lines and process
        lines = text.split("\n")

        # ICICI pattern: lines starting with DD-MM-YYYY
        # Each transaction may span multiple lines
        # Amounts at the end: DEPOSITS WITHDRAWALS BALANCE (right-aligned numbers)
        # We need to collect all lines for a transaction, then extract amounts

        current_date = None
        current_lines: list[str] = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            date_match = re.match(r"^(\d{2}-\d{2}-\d{4})\s+(.*)$", line)
            if date_match:
                # Process previous transaction
                if current_date and current_lines:
                    txn = self._parse_icici_txn_block(current_date, current_lines)
                    if txn:
                        transactions.append(txn)

                current_date = date_match.group(1)
                current_lines = [date_match.group(2)]
            elif current_date:
                # Continuation line
                current_lines.append(line)

        # Process last transaction
        if current_date and current_lines:
            txn = self._parse_icici_txn_block(current_date, current_lines)
            if txn:
                transactions.append(txn)

        return transactions

    def _parse_icici_txn_block(
        self, date_str: str, lines: list[str]
    ) -> Optional[ParsedTransaction]:
        """Parse a single ICICI bank transaction block (may span multiple lines)."""
        # Join all lines
        full_text = " ".join(lines)

        # Skip B/F (brought forward) rows
        if "B/F" in full_text and not re.search(r"\b(?:UPI|NEFT|IMPS|RTGS|CMS|ACH)\b", full_text):
            return None
        # Skip header rows
        if "PARTICULARS" in full_text.upper() or "DEPOSITS" in full_text.upper():
            return None

        # Extract amounts from the end of the text
        # Pattern: amounts are comma-separated numbers like 5,050.16 49,36,324.41
        amounts = re.findall(r"([\d,]+\.\d{2})", full_text)
        if len(amounts) < 2:
            return None

        # Last amount is balance, second-to-last is the transaction amount
        # Need to determine if it's a deposit or withdrawal
        balance_str = amounts[-1].replace(",", "")
        txn_amount_str = amounts[-2].replace(",", "")

        # If there are 3+ amounts, check positions to determine deposit vs withdrawal
        # ICICI format: DEPOSITS column comes before WITHDRAWALS column
        txn_type = "DEBIT"  # default

        # The description is everything before the amounts
        desc_text = full_text
        for amt in amounts:
            desc_text = desc_text.replace(amt, "", 1)
        description = re.sub(r"\s+", " ", desc_text).strip()
        # Remove trailing slashes and whitespace
        description = description.rstrip("/ ")

        # Heuristic: if there are exactly 3 amounts and the first occurrence
        # of the txn amount is in the "deposits" position (before withdrawal column)
        # OR use keywords to determine
        credit_keywords = [
            "CMS TRANSACTION", "CMS/", "ACH/", "NEFT-", "SALARY",
            "CREDIT", "INTEREST", "DIVIDEND", "CASHBACK", "REVERSAL",
            "FLIPKART INTERNET PRIVATE", "REFUND",
        ]
        for kw in credit_keywords:
            if kw.upper() in description.upper():
                txn_type = "CREDIT"
                break

        # If 3 amounts: positions matter - middle is deposit OR withdrawal
        if len(amounts) >= 3:
            # Check if deposit column or withdrawal column has the value
            # The deposit appears before withdrawal in the text
            # If the first non-balance amount position is before the last non-balance amount,
            # the first is deposit, second is withdrawal (or vice versa)
            pass  # Use keyword heuristic above

        txn_date = extract_date(date_str)
        if not txn_date:
            return None

        try:
            amount = Decimal(txn_amount_str)
        except Exception:
            return None

        if amount <= 0:
            return None

        try:
            balance = Decimal(balance_str)
        except Exception:
            balance = None

        return ParsedTransaction(
            transaction_type=txn_type,
            amount=amount,
            merchant=description[:200],
            raw_description=description[:500],
            transaction_date=txn_date,
            balance_after=balance,
            card_type="ACCOUNT",
        )


def _extract_balance(text: str) -> Optional[Decimal]:
    match = re.search(
        r"(?:Avl\.?\s*Bal|Available\s+Balance|Bal)[:\s]+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)",
        text,
        re.IGNORECASE,
    )
    if match:
        return Decimal(match.group(1).replace(",", ""))
    return None
