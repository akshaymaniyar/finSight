import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def get_auth_url(force_consent: bool = True, login_hint: str = "") -> str:
    """Generate OAuth authorization URL.

    Args:
        force_consent: If True, forces consent screen (needed for first-time to get
            refresh_token). If False, uses 'select_account' prompt so returning
            users skip the permission screen.
        login_hint: Optional email to pre-fill the Google account selector.
    """
    logger.info("Generating OAuth URL: force_consent=%s, login_hint=%s", force_consent, login_hint)
    params = {
        "client_id": settings.gmail_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "include_granted_scopes": "true",
    }

    if force_consent:
        # First-time users: need consent to get refresh_token
        params["prompt"] = "consent"
    else:
        # Returning users: just pick account, skip permission screen
        params["prompt"] = "select_account"

    if login_hint:
        params["login_hint"] = login_hint

    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict:
    logger.info("Starting token exchange for authorization code")
    payload = {
        "code": code,
        "client_id": settings.gmail_client_id,
        "client_secret": settings.gmail_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data=payload)
        resp.raise_for_status()
        logger.info("Token exchange succeeded")
        return resp.json()


async def get_user_info(access_token: str) -> dict:
    logger.info("Fetching user info from Google")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_access_token(refresh_token: str) -> dict:
    logger.info("Attempting to refresh access token")
    payload = {
        "client_id": settings.gmail_client_id,
        "client_secret": settings.gmail_client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data=payload)
        resp.raise_for_status()
        data = resp.json()
        logger.info("Token refresh succeeded")
        return data


async def get_valid_access_token(user: User, db: Session) -> str:
    logger.info("Getting valid access token for user_id=%s", user.id)
    if not user.google_access_token:
        raise ValueError("User has no Google access token")

    now = datetime.utcnow()
    expiry = user.google_token_expiry

    # If token is still valid (with 5-minute buffer), return it
    if expiry and expiry > now + timedelta(minutes=5):
        logger.debug("Access token still valid, returning cached token")
        return user.google_access_token

    # Token expired or about to expire -- refresh it
    if not user.google_refresh_token:
        raise ValueError("User has no refresh token; re-authentication required")

    token_data = await refresh_access_token(user.google_refresh_token)

    user.google_access_token = token_data["access_token"]
    user.google_token_expiry = now + timedelta(seconds=token_data.get("expires_in", 3600))

    # Google may issue a new refresh token; persist it if so
    if "refresh_token" in token_data:
        user.google_refresh_token = token_data["refresh_token"]

    db.add(user)
    db.commit()
    db.refresh(user)

    return user.google_access_token
