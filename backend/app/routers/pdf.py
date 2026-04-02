"""
PDF router: serve statement PDFs for browser viewing.

PDFs are saved decrypted on disk during sync, so we can serve them directly.
Falls back to on-the-fly decryption if the file is still encrypted.
"""

from __future__ import annotations

import io
import logging
import re
from pathlib import Path

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


def _find_pdf_for_statement(statement: Statement) -> "Path | None":
    """Find the saved PDF file for a statement."""
    if not statement.gmail_message_id:
        return None

    msg_id = statement.gmail_message_id.split("__pdf__")[0]
    prefix = msg_id[:8]

    # Search all month directories
    if SAVED_ATTACHMENTS_DIR.exists():
        for month_dir in sorted(SAVED_ATTACHMENTS_DIR.iterdir(), reverse=True):
            if not month_dir.is_dir():
                continue
            user_dir = month_dir / str(statement.user_id)
            if user_dir.exists():
                for pdf in user_dir.glob(f"{prefix}_*.pdf"):
                    return pdf

    return None


@router.get("/{statement_id}")
async def get_statement_pdf(
    statement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Serve the PDF for a statement. Files are saved decrypted during sync."""
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

    pdf_path = _find_pdf_for_statement(stmt)
    if not pdf_path or not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    logger.info("Serving PDF: statement_id=%s, path=%s", statement_id, pdf_path)
    pdf_bytes = pdf_path.read_bytes()

    # Check if PDF is already decrypted (try opening without password)
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pdf.pages[0].extract_text()
        # Already decrypted — serve as-is
    except Exception:
        # Still encrypted — decrypt on the fly
        logger.info("PDF still encrypted, decrypting on the fly")
        decrypted = _decrypt_on_fly(pdf_bytes, stmt, current_user, db)
        if decrypted:
            pdf_bytes = decrypted
            # Overwrite with decrypted version for next time
            try:
                pdf_path.write_bytes(pdf_bytes)
            except Exception:
                pass
        else:
            raise HTTPException(status_code=422, detail="Could not decrypt PDF")

    safe_subject = re.sub(r'[^\w\s-]', '', stmt.email_subject or 'statement')[:60].strip()
    filename = f"{safe_subject}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


def _decrypt_on_fly(
    pdf_bytes: bytes, stmt: Statement, user: User, db: Session
) -> "bytes | None":
    """Decrypt a PDF on the fly as a fallback."""
    from pikepdf import Pdf, PasswordError

    subject_lower = (stmt.email_subject or "").lower()
    stmt_type = "credit_card" if "credit card" in subject_lower else "account"

    bank_name = ""
    if stmt.bank_account_id:
        acct = db.query(BankAccount).filter(BankAccount.id == stmt.bank_account_id).first()
        if acct:
            bank_name = acct.bank_name or ""

    all_banks = ["hdfc", "icici", "axis", "idfc", "sbi", "kotak", "amex", "yes", "indusind", "first"]
    names_to_try = [bank_name] if bank_name else []
    for kw in all_banks:
        if kw in subject_lower or kw in bank_name.lower():
            names_to_try.append(kw)

    passwords: list[str] = []
    for bn in names_to_try:
        extra = generate_passwords(
            bank_name=bn, statement_type=stmt_type,
            first_name=user.first_name, last_name=user.last_name,
            dob=user.dob, pan_first5=user.pan_first5,
            mobile_last5=user.mobile_last5, customer_ids=user.customer_ids or {},
        )
        passwords.extend(p for p in extra if p not in passwords)

    for pwd in [""] + passwords:
        try:
            src = Pdf.open(io.BytesIO(pdf_bytes), password=pwd)
            out = io.BytesIO()
            src.save(out)
            src.close()
            return out.getvalue()
        except (PasswordError, Exception):
            continue

    return None
