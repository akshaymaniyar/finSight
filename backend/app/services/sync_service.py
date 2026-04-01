"""
Sync orchestration service.

Fetches bank emails from Gmail for a given month, parses them using
the parser registry, categorizes transactions, and persists everything
to the database.  Now also handles PDF attachments with password-protected
statement parsing.
"""

from __future__ import annotations


import logging
import os
import re
from datetime import datetime, date
from pathlib import Path
from typing import Optional

SAVED_ATTACHMENTS_DIR = Path(__file__).parent.parent.parent / "saved_attachments"

from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.statement import Statement
from app.models.sync_history import SyncHistory
from app.models.transaction import Transaction
from app.models.user import User
from app.models.category import Category
from app.models.category_rule import CategoryRule
from app.parsers.registry import find_parser, find_parser_by_bank_name
from app.services.auth_service import get_valid_access_token
from app.services.categorization import categorize_transaction
from app.services.gmail_service import (
    build_search_query,
    search_emails,
    get_email_detail,
    extract_pdf_attachments,
)
from app.services.pdf_password import generate_passwords, try_open_pdf
from app.services.due_amount import extract_due_amounts
from app.schemas.sync import SyncResultResponse

logger = logging.getLogger(__name__)


def _parse_month(month_str: str) -> date:
    """Parse 'YYYY-MM' into the first day of that month."""
    return datetime.strptime(month_str, "%Y-%m").date()


def _get_or_create_bank_account(
    db: Session,
    user_id: int,
    bank_name: str,
    account_number_masked: str,
    account_type: str = "SAVINGS",
) -> BankAccount:
    """Find an existing bank account or create a new one."""
    account = (
        db.query(BankAccount)
        .filter(
            BankAccount.user_id == user_id,
            BankAccount.bank_name == bank_name,
            BankAccount.account_number_masked == account_number_masked,
        )
        .first()
    )
    if account:
        return account

    account = BankAccount(
        user_id=user_id,
        bank_name=bank_name,
        account_number_masked=account_number_masked or "UNKNOWN",
        account_type=account_type,
    )
    db.add(account)
    db.flush()
    return account


def _detect_bank_from_filename(filename: str) -> Optional[str]:
    """Try to detect bank name from PDF filename."""
    fname = filename.upper()
    if "HDFC" in fname:
        return "HDFC"
    if "ICICI" in fname:
        return "ICICI"
    if "IDFC" in fname:
        return "IDFC"
    if "AXIS" in fname:
        return "Axis"
    if "SBI" in fname:
        return "SBI"
    if "KOTAK" in fname:
        return "Kotak"
    if "AMEX" in fname or "AMERICAN" in fname:
        return "Amex"
    if "YES" in fname:
        return "Yes Bank"
    if "INDUSIND" in fname:
        return "IndusInd"
    if "PNB" in fname or "PUNJAB" in fname:
        return "PNB"
    if "BARODA" in fname or "BOB" in fname:
        return "BOB"
    if "CANARA" in fname:
        return "Canara"
    if "FEDERAL" in fname:
        return "Federal"
    return None


def _detect_statement_type(filename: str, subject: str) -> str:
    """Detect if this is a credit card or bank account statement."""
    combined = (filename + " " + subject).lower()
    cc_keywords = ["credit card", "creditcard", "cc statement", "card statement"]
    for kw in cc_keywords:
        if kw in combined:
            return "credit_card"
    return "account"


def _extract_card_last4(filename: str, subject: str, body_text: str) -> Optional[str]:
    """Try to extract last 4 digits of card from context."""
    combined = filename + " " + subject + " " + (body_text or "")
    # Look for patterns like XX1234, ending 1234, xxxx1234
    match = re.search(r"(?:ending|xxxx|XX)\s*(\d{4})", combined)
    if match:
        return match.group(1)
    return None


def _process_parsed_transactions(
    db: Session,
    user_id: int,
    statement: Statement,
    parsed_transactions: list,
    parser,
    month_date: date,
    user_rules: Optional[list] = None,
    db_categories: Optional[list] = None,
) -> int:
    """Insert parsed transactions into DB. Returns count of transactions created."""
    account_type_map = {
        "CREDIT_CARD": "CREDIT_CARD",
        "DEBIT_CARD": "SAVINGS",
        "ACCOUNT": "SAVINGS",
    }
    txn_count = 0

    for parsed_txn in parsed_transactions:
        acct_type = account_type_map.get(parsed_txn.card_type, "SAVINGS")
        bank_account = _get_or_create_bank_account(
            db=db,
            user_id=user_id,
            bank_name=parser.bank_name,
            account_number_masked=parsed_txn.account_number_masked or "UNKNOWN",
            account_type=acct_type,
        )

        if not statement.bank_account_id:
            statement.bank_account_id = bank_account.id

        cat_result = categorize_transaction(
            merchant=parsed_txn.merchant,
            description=parsed_txn.raw_description,
            card_type=parsed_txn.card_type,
            transaction_type=parsed_txn.transaction_type,
            user_rules=user_rules,
            db_categories=db_categories,
        )

        txn_date = parsed_txn.transaction_date or month_date

        # Duplicate check by reference_id
        if parsed_txn.reference_id:
            existing_txn = (
                db.query(Transaction)
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.reference_id == parsed_txn.reference_id,
                )
                .first()
            )
            if existing_txn:
                continue

        # Duplicate check by amount + date + description (for PDF-parsed txns without reference_id)
        if not parsed_txn.reference_id and parsed_txn.transaction_date:
            existing_txn = (
                db.query(Transaction)
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.statement_id == statement.id,
                    Transaction.amount == parsed_txn.amount,
                    Transaction.transaction_date == txn_date,
                    Transaction.raw_description == (parsed_txn.raw_description or None),
                )
                .first()
            )
            if existing_txn:
                continue

        transaction = Transaction(
            user_id=user_id,
            statement_id=statement.id,
            bank_account_id=bank_account.id,
            transaction_type=parsed_txn.transaction_type,
            amount=parsed_txn.amount,
            merchant=parsed_txn.merchant or None,
            raw_description=parsed_txn.raw_description or None,
            category=cat_result["category"],
            sub_category=cat_result["sub_category"],
            transaction_date=txn_date,
            reference_id=parsed_txn.reference_id or None,
            balance_after=parsed_txn.balance_after,
            is_self_transfer=cat_result["is_self_transfer"],
            is_investment=cat_result["is_investment"],
            is_mutual_fund=cat_result["is_mutual_fund"],
            is_zerodha=cat_result["is_zerodha"],
            is_excluded=cat_result["is_excluded"],
            card_type=parsed_txn.card_type,
        )
        db.add(transaction)
        txn_count += 1
        logger.debug(
            "Inserted transaction: merchant=%s, amount=%s, category=%s",
            parsed_txn.merchant, parsed_txn.amount, cat_result["category"],
        )

    return txn_count


async def sync_month(
    user_id: int,
    month_str: str,
    force_resync: bool,
    db: Session,
) -> SyncResultResponse:
    """Sync bank statement emails for a specific month.

    Now also downloads and parses PDF attachments from emails.
    """
    logger.info("Sync started: user_id=%s, month=%s, force_resync=%s", user_id, month_str, force_resync)
    month_date = _parse_month(month_str)

    # Create SyncHistory record
    sync_record = SyncHistory(
        user_id=user_id,
        sync_month=month_date,
        sync_status="IN_PROGRESS",
        started_at=datetime.utcnow(),
    )
    db.add(sync_record)
    db.commit()
    db.refresh(sync_record)

    try:
        # Get valid access token
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        access_token = await get_valid_access_token(user, db)
        logger.info("Token refresh status: access token obtained for user_id=%s", user_id)

        # Load user's category rules and DB categories for auto-categorization
        user_rules = db.query(CategoryRule).filter(CategoryRule.user_id == user_id).all()
        db_categories = db.query(Category).filter(Category.user_id == user_id).all()

        # If force resync, delete existing statements for this month
        # CASCADE will delete associated transactions
        if force_resync:
            existing_statements = (
                db.query(Statement)
                .filter(
                    Statement.user_id == user_id,
                    Statement.statement_month == month_date,
                )
                .all()
            )
            deleted_count = len(existing_statements)
            for stmt in existing_statements:
                db.delete(stmt)
            db.commit()
            logger.info("Force resync: deleted %d existing statements for month=%s", deleted_count, month_str)

        # Build Gmail search query and fetch emails
        query = build_search_query(month_str)
        logger.info("Gmail search query: %.100s", query)
        email_results = await search_emails(access_token, query)

        logger.info("Number of emails found: %d", len(email_results))
        sync_record.emails_found = len(email_results)
        db.commit()

        emails_parsed = 0
        total_transactions_created = 0

        for email_ref in email_results:
            gmail_message_id = email_ref.get("id", "")
            if not gmail_message_id:
                continue

            # Skip if already processed (unless force resync)
            if not force_resync:
                existing = (
                    db.query(Statement)
                    .filter(
                        Statement.user_id == user_id,
                        Statement.gmail_message_id == gmail_message_id,
                    )
                    .first()
                )
                if existing:
                    logger.debug("Skipping already processed email: %s", gmail_message_id)
                    continue

            try:
                # Fetch full email details
                email_detail = await get_email_detail(access_token, gmail_message_id)

                from_email = email_detail.get("from", "")
                subject = email_detail.get("subject", "")
                logger.info("Processing email: message_id=%s, from=%s, subject=%.80s", gmail_message_id, from_email, subject)
                body_html = email_detail.get("body_html", "")
                body_text = email_detail.get("body_text", "")
                email_date_str = email_detail.get("date", "")
                has_attachments = email_detail.get("has_attachments", False)
                payload = email_detail.get("payload", {})

                # Parse email date
                email_dt = None
                if email_date_str:
                    try:
                        from email.utils import parsedate_to_datetime
                        email_dt = parsedate_to_datetime(email_date_str)
                    except Exception:
                        email_dt = None

                # Create Statement record
                statement = Statement(
                    user_id=user_id,
                    source_type="EMAIL",
                    gmail_message_id=gmail_message_id,
                    email_from=from_email[:255] if from_email else None,
                    email_subject=subject,
                    email_date=email_dt,
                    statement_month=month_date,
                    raw_content=(body_text or body_html)[:65000],
                    parse_status="PENDING",
                )
                db.add(statement)
                db.flush()

                # Find appropriate parser
                parser = find_parser(from_email, subject)
                if parser:
                    logger.info("Parser selected: %s for from=%s", parser.__class__.__name__, from_email)
                if not parser:
                    logger.info("No parser found for from=%s, subject=%.80s", from_email, subject)
                    statement.parse_status = "SKIPPED"
                    statement.parse_error = "No parser found for this sender"
                    db.commit()
                    continue

                # ---- PHASE 1: Parse the email body ----
                parsed_transactions = parser.parse_email(subject, body_html, body_text)
                logger.info(
                    "Email body parse: parser=%s, transactions=%d",
                    parser.__class__.__name__,
                    len(parsed_transactions) if parsed_transactions else 0,
                )

                txn_count = 0
                if parsed_transactions:
                    txn_count = _process_parsed_transactions(
                        db, user_id, statement, parsed_transactions, parser, month_date, user_rules, db_categories
                    )

                # ---- PHASE 2: Parse PDF attachments ----
                pdf_txn_count = 0
                if has_attachments:
                    try:
                        pdf_attachments = await extract_pdf_attachments(
                            access_token, gmail_message_id, payload
                        )
                        logger.info(
                            "PDF attachments found: %d for message_id=%s",
                            len(pdf_attachments), gmail_message_id,
                        )

                        for filename, pdf_bytes in pdf_attachments:
                            logger.info("Processing PDF: filename=%s, size=%d bytes", filename, len(pdf_bytes))

                            # Save PDF to disk for debugging
                            try:
                                save_dir = SAVED_ATTACHMENTS_DIR / month_str / str(user_id)
                                save_dir.mkdir(parents=True, exist_ok=True)
                                safe_name = re.sub(r'[^\w.\-]', '_', filename)
                                save_path = save_dir / f"{gmail_message_id[:8]}_{safe_name}"
                                save_path.write_bytes(pdf_bytes)
                                logger.info("Saved PDF to disk: %s", save_path)
                            except Exception as save_err:
                                logger.warning("Failed to save PDF to disk: %s", save_err)

                            # Determine statement type and bank from context
                            stmt_type = _detect_statement_type(filename, subject)
                            card_last4 = _extract_card_last4(filename, subject, body_text)

                            # Generate password candidates
                            passwords = generate_passwords(
                                bank_name=parser.bank_name,
                                statement_type=stmt_type,
                                first_name=user.first_name,
                                last_name=user.last_name,
                                dob=user.dob,
                                pan_first5=user.pan_first5,
                                mobile_last5=user.mobile_last5,
                                customer_ids=user.customer_ids or {},
                                card_last4=card_last4,
                            )

                            # Try opening the PDF
                            working_password, success = try_open_pdf(pdf_bytes, passwords)
                            if not success:
                                logger.warning(
                                    "Cannot open PDF %s - all %d passwords failed. "
                                    "User may need to update their profile.",
                                    filename, len(passwords),
                                )
                                if not parsed_transactions:
                                    statement.parse_error = (
                                        f"PDF password failed for {filename}. "
                                        "Please update your profile with correct details."
                                    )
                                continue

                            # Parse the PDF
                            pdf_transactions = parser.parse_pdf(pdf_bytes, working_password)
                            logger.info(
                                "PDF parse result: filename=%s, transactions=%d",
                                filename, len(pdf_transactions),
                            )

                            if pdf_transactions:
                                # Attach PDF transactions to the parent email statement
                                count = _process_parsed_transactions(
                                    db, user_id, statement, pdf_transactions, parser, month_date, user_rules
                                )
                                pdf_txn_count += count
                                logger.info("PDF transactions created: %d from %s", count, filename)

                            # Extract due amounts from CC statements
                            if stmt_type == "credit_card" or "credit card" in parser.bank_name.lower():
                                from app.parsers.pdf_utils import extract_text_from_pdf
                                pdf_text = extract_text_from_pdf(pdf_bytes, working_password)
                                if pdf_text:
                                    total_due, min_due = extract_due_amounts(pdf_text)
                                    if total_due is not None:
                                        statement.total_amount_due = total_due
                                        logger.info("Due amount extracted: total=%s, min=%s", total_due, min_due)
                                    if min_due is not None:
                                        statement.minimum_amount_due = min_due

                    except Exception as pdf_err:
                        logger.exception("Error processing PDF attachments for message %s", gmail_message_id)
                        if not parsed_transactions:
                            statement.parse_error = f"PDF processing error: {str(pdf_err)[:200]}"

                total_txn = txn_count + pdf_txn_count
                statement.parse_status = "PARSED"
                statement.transaction_count = total_txn
                # Update source_type if we parsed PDFs too
                if pdf_txn_count > 0:
                    statement.source_type = "EMAIL+PDF"
                if total_txn == 0 and not parsed_transactions:
                    logger.info(
                        "No transactions from email or PDF for message_id=%s, parser=%s",
                        gmail_message_id, parser.__class__.__name__,
                    )
                db.commit()

                emails_parsed += 1
                total_transactions_created += total_txn

            except Exception as e:
                logger.exception(
                    "Failed to process email %s", gmail_message_id
                )
                try:
                    stmt = (
                        db.query(Statement)
                        .filter(
                            Statement.user_id == user_id,
                            Statement.gmail_message_id == gmail_message_id,
                        )
                        .first()
                    )
                    if stmt:
                        stmt.parse_status = "FAILED"
                        stmt.parse_error = str(e)[:500]
                        db.commit()
                except Exception:
                    db.rollback()
                continue

        # Update SyncHistory to COMPLETED
        sync_record.sync_status = "COMPLETED"
        sync_record.emails_parsed = emails_parsed
        sync_record.transactions_created = total_transactions_created
        sync_record.completed_at = datetime.utcnow()
        db.commit()

        logger.info("Sync completed: month=%s, emails_parsed=%d, transactions_created=%d", month_str, emails_parsed, total_transactions_created)

        return SyncResultResponse(
            status="COMPLETED",
            month=month_str,
            emails_found=sync_record.emails_found,
            emails_parsed=emails_parsed,
            transactions_created=total_transactions_created,
            message=f"Successfully synced {month_str}",
        )

    except Exception as e:
        logger.exception("Sync failed for month %s", month_str)
        sync_record.sync_status = "FAILED"
        sync_record.error_message = str(e)[:1000]
        sync_record.completed_at = datetime.utcnow()
        db.commit()

        return SyncResultResponse(
            status="FAILED",
            month=month_str,
            emails_found=sync_record.emails_found,
            emails_parsed=0,
            transactions_created=0,
            message=f"Sync failed: {str(e)}",
        )
