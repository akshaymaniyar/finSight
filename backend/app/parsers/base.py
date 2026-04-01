from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional
from decimal import Decimal


@dataclass
class ParsedTransaction:
    transaction_type: str  # DEBIT or CREDIT
    amount: Decimal
    merchant: str = ""
    raw_description: str = ""
    transaction_date: Optional[date] = None
    reference_id: str = ""
    account_number_masked: str = ""
    balance_after: Optional[Decimal] = None
    card_type: str = "ACCOUNT"  # ACCOUNT, CREDIT_CARD, DEBIT_CARD


class BaseBankParser(ABC):
    bank_name: str = ""
    sender_emails: List[str] = []

    @abstractmethod
    def can_parse(self, from_email: str, subject: str) -> bool:
        ...

    @abstractmethod
    def parse_email(
        self, subject: str, body_html: str, body_text: str
    ) -> List[ParsedTransaction]:
        ...

    def parse_pdf(
        self, pdf_bytes: bytes, password: str = ""
    ) -> List[ParsedTransaction]:
        return []
