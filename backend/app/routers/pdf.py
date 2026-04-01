"""
PDF router: serve decrypted PDF statements for browser viewing.
"""

from __future__ import annotations

import io
import logging
import re
from pathlib import Path

import pdfplumber
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.bank_account import BankAccount
from app.models.statement import Statement
from app.models.user import User
from app.services.pdf_password import generate_passwords

logger = logging.getLogger(__name__)

router = APIRouter()

SAVED_ATTACHMENTS_DIR = Path(__file__).parent.parent.parent / "saved_attachments"


def _find_pdf_for_statement(statement: Statement) -> Path | None:
    """Find the saved PDF file for a statement."""
    if not statement.gmail_message_id:
        return None

    # Handle PDF_ATTACHMENT type gmail_message_ids like "abc123__pdf__filename.pdf"
    msg_id = statement.gmail_message_id.split("__pdf__")[0]
    prefix = msg_id[:8]

    # Search in the month directory
    month_str = statement.statement_month.strftime("%Y-%m") if statement.statement_month else None
    if not month_str:
        return None

    search_dir = SAVED_ATTACHMENTS_DIR / month_str / str(statement.user_id)
    if not search_dir.exists():
        # Also check other months (forwarded emails may be in different month)
        for month_dir in SAVED_ATTACHMENTS_DIR.iterdir():
            candidate = month_dir / str(statement.user_id)
            if candidate.exists():
                for pdf in candidate.glob(f"{prefix}_*.pdf"):
                    return pdf
        return None

    for pdf in search_dir.glob(f"{prefix}_*.pdf"):
        return pdf

    # Search all months as fallback
    for month_dir in SAVED_ATTACHMENTS_DIR.iterdir():
        if not month_dir.is_dir():
            continue
        user_dir = month_dir / str(statement.user_id)
        if user_dir.exists():
            for pdf in user_dir.glob(f"{prefix}_*.pdf"):
                return pdf

    return None


def _decrypt_pdf(pdf_bytes: bytes, passwords: list[str]) -> bytes | None:
    """Open a password-protected PDF and return an unprotected version."""
    from pikepdf import Pdf, PasswordError

    # Try without password first
    try:
        with Pdf.open(io.BytesIO(pdf_bytes)) as pdf:
            output = io.BytesIO()
            pdf.save(output)
            return output.getvalue()
    except PasswordError:
        pass
    except Exception:
        pass

    # Try each password
    for pwd in passwords:
        try:
            with Pdf.open(io.BytesIO(pdf_bytes), password=pwd) as pdf:
                output = io.BytesIO()
                pdf.save(output)
                return output.getvalue()
        except PasswordError:
            continue
        except Exception:
            continue

    return None


@router.get("/{statement_id}")
async def get_statement_pdf(
    statement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Serve the decrypted PDF for a statement."""
    stmt = (
        db.query(Statement)
        .filter(
            Statement.id == statement_id,
            Statement.user_id == current_user.id,
        )
        .first()
    )
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    # Find the PDF file
    pdf_path = _find_pdf_for_statement(stmt)
    if not pdf_path or not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    logger.info("Serving PDF: statement_id=%s, path=%s", statement_id, pdf_path)
    pdf_bytes = pdf_path.read_bytes()

    # Detect bank name and statement type
    subject_lower = (stmt.email_subject or "").lower()
    stmt_type = "credit_card" if "credit card" in subject_lower else "account"

    # Get bank name from bank_account or subject
    bank_name = ""
    if stmt.bank_account_id:
        acct = db.query(BankAccount).filter(BankAccount.id == stmt.bank_account_id).first()
        if acct:
            bank_name = acct.bank_name or ""

    # Extract card last4 from filename
    card_last4 = None
    fname = pdf_path.name
    card_match = re.search(r"(?:XXXX|XX)(\d{4})", fname)
    if card_match:
        card_last4 = card_match.group(1)

    # Generate passwords using bank name and all keyword-matched banks
    all_bank_keywords = ["hdfc", "icici", "axis", "idfc", "sbi", "kotak", "amex", "yes", "indusind", "first"]
    bank_names_to_try = [bank_name] if bank_name else []

    for kw in all_bank_keywords:
        if kw in subject_lower or kw in bank_name.lower():
            bank_names_to_try.append(kw)

    passwords: list[str] = []
    for bn in bank_names_to_try:
        extra = generate_passwords(
            bank_name=bn,
            statement_type=stmt_type,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            dob=current_user.dob,
            pan_first5=current_user.pan_first5,
            mobile_last5=current_user.mobile_last5,
            customer_ids=current_user.customer_ids or {},
            card_last4=card_last4,
        )
        passwords.extend(p for p in extra if p not in passwords)

    # Decrypt
    decrypted = _decrypt_pdf(pdf_bytes, passwords)
    if decrypted is None:
        raise HTTPException(status_code=422, detail="Could not decrypt PDF with available passwords")

    # Build a nice filename
    safe_subject = re.sub(r'[^\w\s-]', '', stmt.email_subject or 'statement')[:60].strip()
    filename = f"{safe_subject}.pdf"

    return Response(
        content=decrypted,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
        },
    )
