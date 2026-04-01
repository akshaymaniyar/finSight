"""
Bank-specific PDF password generation.

Each Indian bank uses a different password pattern for their statement PDFs.
This service generates all possible password candidates for a given bank
using the user's profile information.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


def generate_passwords(
    bank_name: str,
    statement_type: str,  # "credit_card" or "account"
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    dob: Optional[date] = None,
    pan_first5: Optional[str] = None,
    mobile_last5: Optional[str] = None,
    customer_ids: Optional[dict] = None,
    card_last4: Optional[str] = None,
) -> list[str]:
    """Generate a list of possible passwords for a bank statement PDF.

    Returns multiple candidates in order of likelihood. The caller should
    try each one until the PDF opens successfully.
    """
    passwords: list[str] = []
    customer_ids = customer_ids or {}

    # Pre-compute common fragments
    name4_upper = (first_name or "")[:4].upper()
    name4_lower = (first_name or "")[:4].lower()
    dob_ddmm = dob.strftime("%d%m") if dob else ""
    dob_ddmmyyyy = dob.strftime("%d%m%Y") if dob else ""
    dob_ddmmyy = dob.strftime("%d%m%y") if dob else ""

    bank = bank_name.upper()

    # ----- HDFC -----
    if "HDFC" in bank:
        if statement_type == "credit_card":
            # Primary: First 4 letters (UPPER) + Last 4 digits of card
            if name4_upper and card_last4:
                passwords.append(f"{name4_upper}{card_last4}")
            # Alternate: First 4 letters (UPPER) + DOB DDMM
            if name4_upper and dob_ddmm:
                passwords.append(f"{name4_upper}{dob_ddmm}")
            if name4_upper and dob_ddmmyyyy:
                passwords.append(f"{name4_upper}{dob_ddmmyyyy}")
        else:
            # HDFC bank account: Customer ID (8-digit) or DOB DDMMYYYY
            cid = customer_ids.get("HDFC") or customer_ids.get("hdfc")
            if cid:
                passwords.append(str(cid))
            if dob_ddmmyyyy:
                passwords.append(dob_ddmmyyyy)
            if name4_upper and dob_ddmm:
                passwords.append(f"{name4_upper}{dob_ddmm}")

    # ----- ICICI -----
    elif "ICICI" in bank:
        # Both CC and account: First 4 letters (UPPER) + DOB DDMM
        if name4_upper and dob_ddmm:
            passwords.append(f"{name4_upper}{dob_ddmm}")
        if name4_upper and dob_ddmmyyyy:
            passwords.append(f"{name4_upper}{dob_ddmmyyyy}")
        # Also try lowercase
        if name4_lower and dob_ddmm:
            passwords.append(f"{name4_lower}{dob_ddmm}")

    # ----- IDFC First -----
    elif "IDFC" in bank:
        # Both CC and account: DOB in DDMMYYYY
        if dob_ddmmyyyy:
            passwords.append(dob_ddmmyyyy)
        if dob_ddmm:
            passwords.append(dob_ddmm)

    # ----- Axis Bank -----
    elif "AXIS" in bank:
        # Both CC and account: First 4 letters (UPPER) + DOB DDMM
        if name4_upper and dob_ddmm:
            passwords.append(f"{name4_upper}{dob_ddmm}")
        # Alternate: First 4 + last 4 of card
        if name4_upper and card_last4:
            passwords.append(f"{name4_upper}{card_last4}")
        if dob_ddmmyyyy:
            passwords.append(dob_ddmmyyyy)

    # ----- SBI / SBI Card -----
    elif "SBI" in bank:
        if statement_type == "credit_card":
            # First 4 letters (UPPER) + DOB DDMM or DDMMYYYY
            if name4_upper and dob_ddmm:
                passwords.append(f"{name4_upper}{dob_ddmm}")
            if name4_upper and dob_ddmmyyyy:
                passwords.append(f"{name4_upper}{dob_ddmmyyyy}")
        else:
            # SBI account: Last 5 mobile + DOB DDMMYY
            if mobile_last5 and dob_ddmmyy:
                passwords.append(f"{mobile_last5}{dob_ddmmyy}")
            if dob_ddmm:
                passwords.append(dob_ddmm)
            # YONO format: DDMM@last4mobile
            if dob_ddmm and mobile_last5:
                passwords.append(f"{dob_ddmm}@{mobile_last5[-4:]}")

    # ----- Kotak -----
    elif "KOTAK" in bank:
        if statement_type == "credit_card":
            # Kotak CC: lowercase name4 + DOB DDMM
            if name4_lower and dob_ddmm:
                passwords.append(f"{name4_lower}{dob_ddmm}")
            if name4_upper and dob_ddmm:
                passwords.append(f"{name4_upper}{dob_ddmm}")
        else:
            # Kotak account: CRN (8-9 digit)
            cid = customer_ids.get("Kotak") or customer_ids.get("kotak")
            if cid:
                passwords.append(str(cid))
            if name4_lower and dob_ddmm:
                passwords.append(f"{name4_lower}{dob_ddmm}")

    # ----- Amex -----
    elif "AMEX" in bank or "AMERICAN EXPRESS" in bank:
        # First 4 letters (UPPER) + DOB DDMM
        if name4_upper and dob_ddmm:
            passwords.append(f"{name4_upper}{dob_ddmm}")
        if name4_upper and dob_ddmmyyyy:
            passwords.append(f"{name4_upper}{dob_ddmmyyyy}")

    # ----- Yes Bank -----
    elif "YES" in bank:
        # CIF + DOB DDMMYYYY (long password)
        cid = customer_ids.get("Yes Bank") or customer_ids.get("yes_bank")
        if cid and dob_ddmmyyyy:
            passwords.append(f"{cid}{dob_ddmmyyyy}")
        if name4_upper and dob_ddmm:
            passwords.append(f"{name4_upper}{dob_ddmm}")

    # ----- IndusInd -----
    elif "INDUSIND" in bank:
        if statement_type == "credit_card":
            # CC: lowercase name4 + DOB DDMM
            if name4_lower and dob_ddmm:
                passwords.append(f"{name4_lower}{dob_ddmm}")
            if name4_upper and dob_ddmm:
                passwords.append(f"{name4_upper}{dob_ddmm}")
        else:
            # Account: UPPER name4 + DOB DDMM
            if name4_upper and dob_ddmm:
                passwords.append(f"{name4_upper}{dob_ddmm}")
            if name4_lower and dob_ddmm:
                passwords.append(f"{name4_lower}{dob_ddmm}")

    # ----- PNB -----
    elif "PNB" in bank or "PUNJAB NATIONAL" in bank:
        cid = customer_ids.get("PNB") or customer_ids.get("pnb")
        if cid:
            passwords.append(str(cid))
        if dob_ddmmyyyy:
            passwords.append(dob_ddmmyyyy)

    # ----- Bank of Baroda -----
    elif "BARODA" in bank or "BOB" in bank:
        # lowercase name4 + DOB DDMM
        if name4_lower and dob_ddmm:
            passwords.append(f"{name4_lower}{dob_ddmm}")
        if name4_upper and dob_ddmm:
            passwords.append(f"{name4_upper}{dob_ddmm}")

    # ----- Canara -----
    elif "CANARA" in bank:
        cid = customer_ids.get("Canara") or customer_ids.get("canara")
        if cid:
            passwords.append(str(cid))
        if dob_ddmmyyyy:
            passwords.append(dob_ddmmyyyy)

    # ----- Federal Bank -----
    elif "FEDERAL" in bank:
        if name4_upper and dob_ddmm:
            passwords.append(f"{name4_upper}{dob_ddmm}")

    # ----- Indian Bank -----
    elif "INDIAN BANK" in bank:
        if dob_ddmmyyyy:
            passwords.append(dob_ddmmyyyy)
        if name4_upper and dob_ddmm:
            passwords.append(f"{name4_upper}{dob_ddmm}")

    # Generic fallbacks — try common patterns
    if not passwords:
        if name4_upper and dob_ddmm:
            passwords.append(f"{name4_upper}{dob_ddmm}")
        if dob_ddmmyyyy:
            passwords.append(dob_ddmmyyyy)
        if name4_lower and dob_ddmm:
            passwords.append(f"{name4_lower}{dob_ddmm}")

    logger.info(
        "Generated %d password candidates for bank=%s, type=%s",
        len(passwords), bank_name, statement_type,
    )
    return passwords


def try_open_pdf(pdf_bytes: bytes, passwords: list[str]) -> tuple[str, bool]:
    """Try opening a PDF with multiple passwords.

    Returns (working_password, success). If the PDF is not encrypted,
    returns ("", True).
    """
    import io
    import pdfplumber

    # First try without password
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            # Try reading first page to confirm it works
            if pdf.pages:
                pdf.pages[0].extract_text()
            return "", True
    except Exception:
        pass

    # Try each password
    for pwd in passwords:
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes), password=pwd) as pdf:
                if pdf.pages:
                    pdf.pages[0].extract_text()
                logger.info("PDF opened with password pattern (index %d)", passwords.index(pwd))
                return pwd, True
        except Exception:
            continue

    logger.warning("Failed to open PDF with any of %d password candidates", len(passwords))
    return "", False
