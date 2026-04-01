from __future__ import annotations
import base64
import logging
from datetime import datetime
from typing import Optional
from dateutil.relativedelta import relativedelta

import httpx

logger = logging.getLogger(__name__)

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

# Known Indian bank sender email addresses
ALL_BANK_SENDERS = [
    # HDFC
    "alerts@hdfcbank.net",
    "noreply@hdfcbank.net",
    "creditcard.alerts@hdfcbank.net",
    "statements@hdfcbank.net",
    "Emailstatements.cards@hdfcbank.net",
    # SBI
    "donotreply@sbi.co.in",
    "alerts@sbi.co.in",
    "sbicard.alert@sbicard.com",
    "noreply@sbicard.com",
    # ICICI
    "alerts@icicibank.com",
    "noreply@icicibank.com",
    "credit_cards@icicibank.com",
    "creditcards@icicibank.com",
    "statement@icicibank.com",
    # Axis
    "alerts@axisbank.com",
    "noreply@axisbank.com",
    "AxisCard.Statements@axisbank.com",
    "creditcards@axisbank.com",
    "cc.statements@axisbank.com",
    # Kotak
    "alerts@kotak.com",
    "noreply@kotak.com",
    "creditcards@kotak.com",
    "cardstatement@kotak.com",
    # Yes Bank
    "alerts@yesbank.in",
    "noreply@yesbank.in",
    # IndusInd
    "alerts@indusind.com",
    "noreply@indusind.com",
    "creditcards@indusind.com",
    # PNB
    "alerts@pnb.co.in",
    "noreply@pnb.co.in",
    # Bank of Baroda
    "alerts@bankofbaroda.co.in",
    "noreply@bankofbaroda.co.in",
    # Canara Bank
    "alerts@canarabank.in",
    "noreply@canarabank.in",
    # IDFC First
    "alerts@idfcfirstbank.com",
    "noreply@idfcfirstbank.com",
    "creditcard@idfcfirstbank.com",
    "statement@idfcfirstbank.com",
    # Indian Bank
    "alerts@indianbank.co.in",
    "noreply@indianbank.co.in",
    # American Express
    "alerts@aexp.com",
    "noreply@americanexpress.com",
    "statements@americanexpress.com",
    # SBI Card
    "noreply@sbicard.com",
    "alerts@sbicard.com",
    "statements@sbicard.com",
    # AU Small Finance Bank
    "alerts@aubank.in",
    "noreply@aubank.in",
    # Federal Bank
    "alerts@federalbank.co.in",
    "noreply@federalbank.co.in",
    # RBL Bank
    "alerts@rblbank.com",
    "noreply@rblbank.com",
    # HSBC
    "alerts@hsbc.co.in",
    "noreply@hsbc.co.in",
    # Standard Chartered
    "alerts@sc.com",
    "noreply@sc.com",
    # Citibank
    "alerts@citibank.com",
    "noreply@citibank.com",
]


def build_search_query(month: str) -> str:
    """Build Gmail search query for bank emails in a given month.

    Searches for:
    1. Emails from known bank senders
    2. Forwarded bank statements (subject contains "Bank Statement" or "Credit Card Statement")

    Args:
        month: Month string in YYYY-MM format (e.g. "2025-11").

    Returns:
        Gmail search query string.
    """
    dt = datetime.strptime(month, "%Y-%m")
    next_month = dt + relativedelta(months=1)

    after = dt.strftime("%Y/%m/%d")
    before = next_month.strftime("%Y/%m/%d")

    unique_senders = sorted(set(ALL_BANK_SENDERS))
    from_clause = " OR ".join(unique_senders)

    # Also catch forwarded bank statements
    fwd_clause = 'subject:"Bank Statement" OR subject:"Credit Card Statement"'

    query = f"(from:({from_clause}) OR ({fwd_clause})) after:{after} before:{before}"
    logger.info("Built Gmail search query for month=%s, after=%s, before=%s", month, after, before)
    return query


async def search_emails(
    access_token: str,
    query: str,
    max_results: int = 100,
) -> list[dict]:
    """Search Gmail for messages matching query. Handles pagination."""
    logger.info("Searching Gmail with query (first 100 chars): %.100s", query)
    headers = {"Authorization": f"Bearer {access_token}"}
    messages: list[dict] = []
    page_token: Optional[str] = None

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            params: dict = {
                "q": query,
                "maxResults": min(max_results - len(messages), 100),
            }
            if page_token:
                params["pageToken"] = page_token

            resp = await client.get(
                f"{GMAIL_API_BASE}/messages",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            batch = data.get("messages", [])
            messages.extend(batch)

            page_token = data.get("nextPageToken")
            if not page_token or len(messages) >= max_results:
                break

    logger.info("Gmail search found %d emails", len(messages[:max_results]))
    return messages[:max_results]


def extract_email_body(payload: dict) -> dict:
    """Recursively extract text and HTML body from Gmail message payload.

    Returns:
        {"text": str, "html": str}
    """
    text_body = ""
    html_body = ""

    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if body_data and mime_type == "text/plain":
        try:
            text_body = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        except Exception as e:
            logger.error("Error decoding text/plain body: %s", e)
    elif body_data and mime_type == "text/html":
        try:
            html_body = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        except Exception as e:
            logger.error("Error decoding text/html body: %s", e)

    for part in payload.get("parts", []):
        child = extract_email_body(part)
        if child["text"] and not text_body:
            text_body = child["text"]
        if child["html"] and not html_body:
            html_body = child["html"]

    return {"text": text_body, "html": html_body}


def _get_header(headers: list[dict], name: str) -> str:
    """Extract a header value by name (case-insensitive)."""
    name_lower = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name_lower:
            return h.get("value", "")
    return ""


async def get_email_detail(access_token: str, message_id: str) -> dict:
    """Fetch full message details and extract structured data.

    Returns:
        {
            "id": str,
            "from": str,
            "subject": str,
            "date": str,
            "body_text": str,
            "body_html": str,
            "has_attachments": bool,
        }
    """
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{GMAIL_API_BASE}/messages/{message_id}",
            headers=headers,
            params={"format": "full"},
        )
        resp.raise_for_status()
        msg = resp.json()

    payload = msg.get("payload", {})
    msg_headers = payload.get("headers", [])

    body = extract_email_body(payload)

    has_attachments = _check_for_attachments(payload)

    from_addr = _get_header(msg_headers, "From")
    subject = _get_header(msg_headers, "Subject")
    logger.info("Fetched email detail: message_id=%s, from=%s, subject=%.80s", message_id, from_addr, subject)

    return {
        "id": msg.get("id", ""),
        "from": from_addr,
        "subject": subject,
        "date": _get_header(msg_headers, "Date"),
        "body_text": body["text"],
        "body_html": body["html"],
        "has_attachments": has_attachments,
        "payload": payload,
    }


def _check_for_attachments(payload: dict) -> bool:
    """Check if any part has a PDF attachment."""
    if payload.get("filename") and payload.get("body", {}).get("attachmentId"):
        return True
    for part in payload.get("parts", []):
        if _check_for_attachments(part):
            return True
    return False


def _collect_pdf_parts(payload: dict) -> list[dict]:
    """Recursively collect all PDF attachment parts."""
    pdf_parts: list[dict] = []
    filename = payload.get("filename", "")
    mime_type = payload.get("mimeType", "")
    attachment_id = payload.get("body", {}).get("attachmentId")

    if attachment_id and filename and (
        mime_type == "application/pdf" or filename.lower().endswith(".pdf")
    ):
        pdf_parts.append({
            "filename": filename,
            "attachmentId": attachment_id,
        })

    for part in payload.get("parts", []):
        pdf_parts.extend(_collect_pdf_parts(part))

    return pdf_parts


async def extract_pdf_attachments(
    access_token: str,
    message_id: str,
    payload: dict,
) -> list[tuple[str, bytes]]:
    """Download PDF attachments from a Gmail message.

    Args:
        access_token: Valid Google access token.
        message_id: Gmail message ID.
        payload: Message payload dict (from full message fetch).

    Returns:
        List of (filename, pdf_bytes) tuples.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    pdf_parts = _collect_pdf_parts(payload)

    logger.info("Extracting PDF attachments from message_id=%s, found %d PDF parts", message_id, len(pdf_parts))
    results: list[tuple[str, bytes]] = []

    async with httpx.AsyncClient(timeout=60) as client:
        for part in pdf_parts:
            resp = await client.get(
                f"{GMAIL_API_BASE}/messages/{message_id}/attachments/{part['attachmentId']}",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json().get("data", "")
            pdf_bytes = base64.urlsafe_b64decode(data)
            logger.info("Extracted PDF attachment: filename=%s, size=%d bytes", part["filename"], len(pdf_bytes))
            results.append((part["filename"], pdf_bytes))

    return results
