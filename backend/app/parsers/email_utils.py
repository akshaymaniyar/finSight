import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from bs4 import BeautifulSoup


def clean_html(html: str) -> str:
    """Extract clean text from HTML content using BeautifulSoup."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    # Remove script and style elements
    for tag in soup(["script", "style", "head"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    # Collapse multiple whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_amount(text: str) -> Optional[Decimal]:
    """Extract monetary amount from text.

    Handles formats like:
    - Rs.1,23,456.78
    - Rs 1,23,456.78
    - INR 1,23,456.78
    - ₹1,23,456.78
    - Rs. 500
    """
    if not text:
        return None

    patterns = [
        r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)",
        r"([\d,]+(?:\.\d{1,2})?)\s*(?:Rs\.?|INR|₹)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(",", "")
            try:
                return Decimal(amount_str)
            except InvalidOperation:
                continue

    return None


def extract_date(text: str) -> Optional[date]:
    """Extract date from text.

    Handles formats:
    - DD-MMM-YYYY (e.g., 01-Apr-2026)
    - DD/MM/YYYY (e.g., 01/04/2026)
    - YYYY-MM-DD (e.g., 2026-04-01)
    - DD-MM-YYYY (e.g., 01-04-2026)
    - DD MMM YYYY (e.g., 01 Apr 2026)
    - DD-MMM-YY (e.g., 01-Apr-26)
    """
    if not text:
        return None

    formats_and_patterns = [
        # DD-MMM-YYYY or DD MMM YYYY
        (
            r"(\d{1,2})[-\s](Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-\s](\d{4})",
            "%d-%b-%Y",
        ),
        # DD-MMM-YY
        (
            r"(\d{1,2})[-\s](Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-\s](\d{2})\b",
            "%d-%b-%y",
        ),
        # YYYY-MM-DD
        (r"(\d{4})-(\d{2})-(\d{2})", None),
        # DD/MM/YYYY
        (r"(\d{1,2})/(\d{1,2})/(\d{4})", None),
        # DD-MM-YYYY
        (r"(\d{1,2})-(\d{1,2})-(\d{4})", None),
    ]

    for pattern, fmt in formats_and_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if fmt:
                # Month-name based formats
                date_str = f"{match.group(1)}-{match.group(2)[:3]}-{match.group(3)}"
                short_fmt = fmt.replace("%B", "%b")
                try:
                    return datetime.strptime(date_str, short_fmt).date()
                except ValueError:
                    continue
            else:
                groups = match.groups()
                try:
                    if len(groups[0]) == 4:
                        # YYYY-MM-DD
                        return date(int(groups[0]), int(groups[1]), int(groups[2]))
                    else:
                        # DD/MM/YYYY or DD-MM-YYYY
                        return date(int(groups[2]), int(groups[1]), int(groups[0]))
                except (ValueError, IndexError):
                    continue

    return None


def extract_account_number(text: str) -> str:
    """Extract masked account number from text.

    Handles formats:
    - XX1234 or xx1234
    - ****5678 or ***5678
    - ending 1234
    - a/c *1234 or a/c **1234
    - A/C XX1234
    - account **1234
    """
    if not text:
        return ""

    patterns = [
        r"[Aa]/[Cc]\s*(?:No\.?\s*)?[*Xx]+\s*(\d{4,6})",
        r"[Aa]ccount\s*(?:No\.?\s*)?[*Xx]+\s*(\d{4,6})",
        r"(?:XX|xx)\s*(\d{4,6})",
        r"\*{2,4}\s*(\d{4,6})",
        r"ending\s+(?:with\s+)?(\d{4,6})",
        r"[Aa]/[Cc]\s*(?:No\.?\s*)?(\d{4,6})\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            digits = match.group(1)
            return f"XX{digits}"

    return ""


def extract_reference(text: str) -> str:
    """Extract transaction reference number from text.

    Handles:
    - UTR numbers (e.g., UTR: UTIB12345678901234)
    - NEFT references (e.g., NEFT Ref No: N12345678901234)
    - RTGS references (e.g., RTGS Ref No: R12345678901234)
    - IMPS references (e.g., IMPS Ref No: 123456789012)
    - UPI references (e.g., UPI Ref No: 123456789012)
    - Generic Ref No / Txn No
    """
    if not text:
        return ""

    patterns = [
        r"UTR[:\s]+([A-Za-z0-9]{16,22})",
        r"NEFT\s*(?:Ref|Reference)\s*(?:No\.?)?[:\s]+([A-Za-z0-9]{10,25})",
        r"RTGS\s*(?:Ref|Reference)\s*(?:No\.?)?[:\s]+([A-Za-z0-9]{10,25})",
        r"IMPS\s*(?:Ref|Reference)\s*(?:No\.?)?[:\s]+(\d{10,15})",
        r"UPI\s*(?:Ref|Reference)\s*(?:No\.?)?[:\s]+(\d{10,15})",
        r"(?:Ref|Reference|Txn|Transaction)\s*(?:No\.?|Number|Id|ID)?[:\s]+([A-Za-z0-9]{6,25})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return ""
