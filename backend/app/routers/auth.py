from __future__ import annotations
import logging
import random
from datetime import datetime, date, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user, create_jwt_token
from app.models.user import User
from app.models.bank_account import BankAccount
from app.models.transaction import Transaction
from app.config import settings
from app.services import auth_service

router = APIRouter()


@router.get("/login")
async def login(
    email: str = Query(default=""),
    db: Session = Depends(get_db),
):
    """Generate OAuth login URL.

    If the email belongs to an existing user with a refresh token,
    we skip the consent screen (just account selection).
    First-time users get the full consent screen to grant Gmail access.
    """
    force_consent = True
    if email:
        existing = db.query(User).filter(User.email == email).first()
        if existing and existing.google_refresh_token:
            logger.info("Returning user detected: %s — skipping consent", email)
            force_consent = False

    logger.info("Login attempt - generating OAuth URL, force_consent=%s", force_consent)
    authorization_url = auth_service.get_auth_url(
        force_consent=force_consent,
        login_hint=email,
    )
    return {"authorization_url": authorization_url}


@router.get("/callback")
async def callback(code: str = Query(...), db: Session = Depends(get_db)):
    logger.info("OAuth callback received, code length=%d", len(code))
    try:
        token_data = await auth_service.exchange_code_for_token(code)
    except Exception:
        logger.error("Failed to exchange authorization code")
        raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

    access_token = token_data.get("access_token")
    if not access_token:
        logger.error("No access token in token exchange response")
        raise HTTPException(status_code=400, detail="No access token in response")

    try:
        user_info = await auth_service.get_user_info(access_token)
    except Exception:
        logger.error("Failed to fetch user info from Google")
        raise HTTPException(status_code=400, detail="Failed to fetch user info from Google")

    email = user_info.get("email")
    if not email:
        logger.error("No email returned from Google user info")
        raise HTTPException(status_code=400, detail="No email returned from Google")

    user = db.query(User).filter(User.email == email).first()
    if user:
        logger.info("Updating existing user: %s", email)
        user.name = user_info.get("name", user.name)
        user.picture = user_info.get("picture", user.picture)
        user.google_access_token = access_token
        if token_data.get("refresh_token"):
            user.google_refresh_token = token_data["refresh_token"]
        user.google_token_expiry = datetime.utcnow() + timedelta(
            seconds=token_data.get("expires_in", 3600)
        )
    else:
        logger.info("Creating new user: %s", email)
        user = User(
            email=email,
            name=user_info.get("name", ""),
            picture=user_info.get("picture", ""),
            google_access_token=access_token,
            google_refresh_token=token_data.get("refresh_token", ""),
            google_token_expiry=datetime.utcnow() + timedelta(
                seconds=token_data.get("expires_in", 3600)
            ),
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    jwt_token = create_jwt_token(user.id, user.email)
    redirect_url = f"{settings.frontend_url}/#token={jwt_token}"
    return RedirectResponse(url=redirect_url)


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "picture": current_user.picture,
        "has_gmail_access": bool(current_user.google_refresh_token),
        "profile_completed": bool(current_user.profile_completed),
    }


@router.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}


# ---------------------------------------------------------------------------
# Demo endpoint -- seeds a demo user with realistic Indian transactions
# ---------------------------------------------------------------------------

DEMO_BANK_ACCOUNTS = [
    {"bank_name": "HDFC Bank", "account_type": "SAVINGS", "account_number_masked": "XXXX1234", "card_network": None, "nickname": "HDFC Savings"},
    {"bank_name": "HDFC Bank", "account_type": "CREDIT_CARD", "account_number_masked": "XXXX5678", "card_network": "VISA", "nickname": "HDFC Millennia"},
    {"bank_name": "ICICI Bank", "account_type": "SAVINGS", "account_number_masked": "XXXX4321", "card_network": None, "nickname": "ICICI Salary"},
    {"bank_name": "ICICI Bank", "account_type": "CREDIT_CARD", "account_number_masked": "XXXX8765", "card_network": "MASTERCARD", "nickname": "ICICI Amazon Pay"},
    {"bank_name": "SBI", "account_type": "SAVINGS", "account_number_masked": "XXXX9012", "card_network": None, "nickname": "SBI Main"},
    {"bank_name": "Axis Bank", "account_type": "CREDIT_CARD", "account_number_masked": "XXXX3456", "card_network": "VISA", "nickname": "Axis Flipkart"},
]

# (merchant, category, sub_category, min_amt, max_amt, txn_type, card_type, flags)
# flags: dict with optional is_self_transfer, is_investment, is_mutual_fund, is_zerodha
DEMO_TRANSACTIONS = [
    # Food & Dining
    ("Swiggy", "Food & Dining", "Food Delivery", 150, 850, "DEBIT", "CREDIT_CARD", {}),
    ("Zomato", "Food & Dining", "Food Delivery", 180, 900, "DEBIT", "CREDIT_CARD", {}),
    ("Swiggy Instamart", "Food & Dining", "Groceries", 200, 600, "DEBIT", "CREDIT_CARD", {}),
    ("Starbucks India", "Food & Dining", "Cafe", 300, 750, "DEBIT", "CREDIT_CARD", {}),
    ("Chaayos", "Food & Dining", "Cafe", 120, 350, "DEBIT", "DEBIT_CARD", {}),
    ("Third Wave Coffee", "Food & Dining", "Cafe", 200, 550, "DEBIT", "DEBIT_CARD", {}),
    ("Haldirams", "Food & Dining", "Restaurant", 250, 1200, "DEBIT", "CREDIT_CARD", {}),
    ("Barbeque Nation", "Food & Dining", "Restaurant", 1500, 4000, "DEBIT", "CREDIT_CARD", {}),
    ("Punjab Grill", "Food & Dining", "Restaurant", 2000, 5000, "DEBIT", "CREDIT_CARD", {}),
    ("McDonald's", "Food & Dining", "Fast Food", 150, 500, "DEBIT", "DEBIT_CARD", {}),
    ("Dominos", "Food & Dining", "Fast Food", 250, 800, "DEBIT", "CREDIT_CARD", {}),

    # Shopping
    ("Amazon India", "Shopping", "Online Shopping", 300, 15000, "DEBIT", "CREDIT_CARD", {}),
    ("Flipkart", "Shopping", "Online Shopping", 250, 12000, "DEBIT", "CREDIT_CARD", {}),
    ("Myntra", "Shopping", "Fashion", 500, 5000, "DEBIT", "CREDIT_CARD", {}),
    ("Ajio", "Shopping", "Fashion", 400, 3500, "DEBIT", "CREDIT_CARD", {}),
    ("IKEA", "Shopping", "Home & Furniture", 1500, 25000, "DEBIT", "CREDIT_CARD", {}),
    ("Decathlon", "Shopping", "Sports & Fitness", 500, 8000, "DEBIT", "CREDIT_CARD", {}),
    ("Croma", "Shopping", "Electronics", 1000, 30000, "DEBIT", "CREDIT_CARD", {}),
    ("Reliance Digital", "Shopping", "Electronics", 800, 20000, "DEBIT", "CREDIT_CARD", {}),
    ("DMart", "Shopping", "Supermarket", 800, 3500, "DEBIT", "DEBIT_CARD", {}),
    ("BigBasket", "Shopping", "Groceries", 500, 4000, "DEBIT", "CREDIT_CARD", {}),
    ("Blinkit", "Shopping", "Groceries", 100, 1200, "DEBIT", "CREDIT_CARD", {}),
    ("Zepto", "Shopping", "Groceries", 100, 800, "DEBIT", "CREDIT_CARD", {}),
    ("Nykaa", "Shopping", "Beauty & Personal Care", 300, 3000, "DEBIT", "CREDIT_CARD", {}),

    # Transport
    ("Uber India", "Transport", "Cab", 100, 800, "DEBIT", "CREDIT_CARD", {}),
    ("Ola", "Transport", "Cab", 80, 700, "DEBIT", "CREDIT_CARD", {}),
    ("Rapido", "Transport", "Cab", 50, 250, "DEBIT", "DEBIT_CARD", {}),
    ("Indian Oil IOCL", "Transport", "Fuel", 500, 4000, "DEBIT", "DEBIT_CARD", {}),
    ("HP Petrol Pump", "Transport", "Fuel", 500, 3500, "DEBIT", "DEBIT_CARD", {}),
    ("IRCTC", "Transport", "Train", 300, 3000, "DEBIT", "DEBIT_CARD", {}),
    ("MakeMyTrip", "Transport", "Flight", 3000, 15000, "DEBIT", "CREDIT_CARD", {}),

    # Subscriptions
    ("Netflix", "Subscriptions", "Entertainment", 199, 649, "DEBIT", "CREDIT_CARD", {}),
    ("Spotify India", "Subscriptions", "Music", 119, 179, "DEBIT", "CREDIT_CARD", {}),
    ("Amazon Prime", "Subscriptions", "Entertainment", 299, 1499, "DEBIT", "CREDIT_CARD", {}),
    ("Hotstar", "Subscriptions", "Entertainment", 299, 1499, "DEBIT", "CREDIT_CARD", {}),
    ("YouTube Premium", "Subscriptions", "Entertainment", 129, 189, "DEBIT", "CREDIT_CARD", {}),
    ("Jio Recharge", "Subscriptions", "Mobile Recharge", 239, 999, "DEBIT", "DEBIT_CARD", {}),
    ("Airtel Recharge", "Subscriptions", "Mobile Recharge", 299, 999, "DEBIT", "DEBIT_CARD", {}),

    # Bills & Utilities
    ("BESCOM Electricity", "Bills & Utilities", "Electricity", 500, 3500, "DEBIT", "ACCOUNT", {}),
    ("BWSSB Water", "Bills & Utilities", "Water", 100, 500, "DEBIT", "ACCOUNT", {}),
    ("Tata Play DTH", "Bills & Utilities", "DTH", 200, 500, "DEBIT", "ACCOUNT", {}),
    ("Piped Gas", "Bills & Utilities", "Gas", 300, 900, "DEBIT", "ACCOUNT", {}),
    ("Society Maintenance", "Bills & Utilities", "Housing", 3000, 8000, "DEBIT", "ACCOUNT", {}),

    # Health & Fitness
    ("Apollo Pharmacy", "Health", "Pharmacy", 200, 2000, "DEBIT", "DEBIT_CARD", {}),
    ("Practo", "Health", "Consultation", 300, 1500, "DEBIT", "CREDIT_CARD", {}),
    ("Cult.fit", "Health", "Gym", 500, 2000, "DEBIT", "CREDIT_CARD", {}),

    # Investments
    ("Zerodha", "Investments", "Stock Trading", 5000, 50000, "DEBIT", "ACCOUNT", {"is_investment": True, "is_zerodha": True}),
    ("Groww", "Investments", "Mutual Funds", 1000, 25000, "DEBIT", "ACCOUNT", {"is_investment": True, "is_mutual_fund": True}),
    ("Coin by Zerodha", "Investments", "Mutual Funds", 2000, 15000, "DEBIT", "ACCOUNT", {"is_investment": True, "is_mutual_fund": True, "is_zerodha": True}),
    ("Kuvera MF", "Investments", "Mutual Funds", 1000, 10000, "DEBIT", "ACCOUNT", {"is_investment": True, "is_mutual_fund": True}),

    # Self-transfers
    ("NEFT to ICICI", "Transfer", "Self Transfer", 5000, 50000, "DEBIT", "ACCOUNT", {"is_self_transfer": True}),
    ("IMPS from HDFC", "Transfer", "Self Transfer", 2000, 30000, "CREDIT", "ACCOUNT", {"is_self_transfer": True}),
    ("UPI to SBI", "Transfer", "Self Transfer", 1000, 20000, "DEBIT", "ACCOUNT", {"is_self_transfer": True}),

    # Income / Credits
    ("Salary Credit", "Income", "Salary", 50000, 150000, "CREDIT", "ACCOUNT", {}),
    ("Cashback Reward", "Income", "Cashback", 50, 500, "CREDIT", "CREDIT_CARD", {}),
    ("Refund - Amazon", "Income", "Refund", 200, 5000, "CREDIT", "CREDIT_CARD", {}),
    ("Zerodha Payout", "Income", "Investment", 1000, 20000, "CREDIT", "ACCOUNT", {"is_investment": True, "is_zerodha": True}),
    ("Dividend Credit", "Income", "Dividend", 100, 3000, "CREDIT", "ACCOUNT", {"is_investment": True}),

    # Miscellaneous
    ("BookMyShow", "Entertainment", "Movies", 200, 1500, "DEBIT", "CREDIT_CARD", {}),
    ("PVR Cinemas", "Entertainment", "Movies", 300, 1200, "DEBIT", "CREDIT_CARD", {}),
    ("Urban Company", "Services", "Home Services", 300, 3000, "DEBIT", "CREDIT_CARD", {}),
    ("LensKart", "Shopping", "Eyewear", 1000, 5000, "DEBIT", "CREDIT_CARD", {}),
    ("Pharmeasy", "Health", "Pharmacy", 150, 2500, "DEBIT", "CREDIT_CARD", {}),
    ("Cleartrip", "Transport", "Travel", 2000, 12000, "DEBIT", "CREDIT_CARD", {}),
]


def _random_date_in_range(start: date, end: date) -> date:
    delta = (end - start).days
    if delta <= 0:
        return start
    return start + timedelta(days=random.randint(0, delta))


def _pick_account_for_txn(accounts: list[BankAccount], card_type: str) -> BankAccount:
    """Pick a matching bank account for the given card_type."""
    if card_type == "CREDIT_CARD":
        cc = [a for a in accounts if a.account_type == "CREDIT_CARD"]
        return random.choice(cc) if cc else random.choice(accounts)
    elif card_type == "DEBIT_CARD":
        savings = [a for a in accounts if a.account_type == "SAVINGS"]
        return random.choice(savings) if savings else random.choice(accounts)
    else:
        savings = [a for a in accounts if a.account_type == "SAVINGS"]
        return random.choice(savings) if savings else random.choice(accounts)


@router.post("/demo")
async def demo_login(db: Session = Depends(get_db)):
    logger.info("Demo login requested")
    demo_email = "demo@finsight.app"

    user = db.query(User).filter(User.email == demo_email).first()
    if user:
        jwt_token = create_jwt_token(user.id, user.email)
        return {"token": jwt_token, "user": {"id": user.id, "email": user.email, "name": user.name, "picture": user.picture or ""}, "message": "Demo session resumed"}

    user = User(
        email=demo_email,
        name="Demo User",
        picture="",
        google_access_token=None,
        google_refresh_token=None,
        google_token_expiry=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create bank accounts
    accounts: list[BankAccount] = []
    for acct_info in DEMO_BANK_ACCOUNTS:
        acct = BankAccount(user_id=user.id, **acct_info)
        db.add(acct)
        accounts.append(acct)
    db.commit()
    for a in accounts:
        db.refresh(a)

    # Seed transactions across the last 6 months
    today = date.today()
    six_months_ago = today - timedelta(days=180)

    transactions: list[Transaction] = []
    running_balance = Decimal("125000.00")

    # Generate ~85 transactions
    # Monthly recurring items: salary, rent/maintenance, subscriptions, investments
    for month_offset in range(6):
        month_start = (today - timedelta(days=180)) + timedelta(days=30 * month_offset)
        month_end = month_start + timedelta(days=29)
        if month_end > today:
            month_end = today

        # Salary on 1st of each month
        salary_date = date(month_start.year, month_start.month, 1)
        if salary_date < six_months_ago:
            salary_date = six_months_ago
        if salary_date <= today:
            salary_amount = Decimal(str(random.choice([75000, 85000, 95000, 105000, 115000])))
            running_balance += salary_amount
            transactions.append(Transaction(
                user_id=user.id,
                bank_account_id=accounts[2].id,  # ICICI Salary
                transaction_type="CREDIT",
                amount=salary_amount,
                merchant="Salary Credit",
                raw_description=f"NEFT-EMPLOYER-SAL-{salary_date.strftime('%b').upper()}",
                category="Income",
                sub_category="Salary",
                transaction_date=salary_date,
                reference_id=f"SAL{salary_date.strftime('%Y%m')}001",
                balance_after=running_balance,
                card_type="ACCOUNT",
            ))

        # Society maintenance on 5th
        maint_date = date(month_start.year, month_start.month, 5)
        if six_months_ago <= maint_date <= today:
            maint_amt = Decimal("5500.00")
            running_balance -= maint_amt
            transactions.append(Transaction(
                user_id=user.id,
                bank_account_id=accounts[0].id,
                transaction_type="DEBIT",
                amount=maint_amt,
                merchant="Society Maintenance",
                raw_description="NACH-SOCIETY-MAINT-DEBIT",
                category="Bills & Utilities",
                sub_category="Housing",
                transaction_date=maint_date,
                reference_id=f"MAINT{maint_date.strftime('%Y%m')}",
                balance_after=running_balance,
                card_type="ACCOUNT",
            ))

        # SIP investment on 7th
        sip_date = date(month_start.year, month_start.month, 7)
        if six_months_ago <= sip_date <= today:
            sip_amt = Decimal(str(random.choice([5000, 10000, 15000])))
            running_balance -= sip_amt
            transactions.append(Transaction(
                user_id=user.id,
                bank_account_id=accounts[0].id,
                transaction_type="DEBIT",
                amount=sip_amt,
                merchant="Groww",
                raw_description=f"SIP-GROWW-MF-{sip_date.strftime('%b').upper()}",
                category="Investments",
                sub_category="Mutual Funds",
                transaction_date=sip_date,
                reference_id=f"SIP{sip_date.strftime('%Y%m')}",
                balance_after=running_balance,
                is_investment=True,
                is_mutual_fund=True,
                card_type="ACCOUNT",
            ))

    # Random transactions from the pool
    num_random = random.randint(65, 75)
    for _ in range(num_random):
        template = random.choice(DEMO_TRANSACTIONS)
        merchant, category, sub_category, min_amt, max_amt, txn_type, card_type, flags = template

        amount = Decimal(str(random.randint(min_amt, max_amt)))
        txn_date = _random_date_in_range(six_months_ago, today)
        account = _pick_account_for_txn(accounts, card_type)

        if txn_type == "DEBIT":
            running_balance -= amount
        else:
            running_balance += amount

        txn = Transaction(
            user_id=user.id,
            bank_account_id=account.id,
            transaction_type=txn_type,
            amount=amount,
            merchant=merchant,
            raw_description=f"{merchant.upper().replace(' ', '-')}-{txn_type}-{txn_date.strftime('%d%m%y')}",
            category=category,
            sub_category=sub_category,
            transaction_date=txn_date,
            reference_id=f"TXN{random.randint(100000, 999999)}",
            balance_after=max(running_balance, Decimal("1000.00")),
            is_self_transfer=flags.get("is_self_transfer", False),
            is_investment=flags.get("is_investment", False),
            is_mutual_fund=flags.get("is_mutual_fund", False),
            is_zerodha=flags.get("is_zerodha", False),
            card_type=card_type,
        )
        transactions.append(txn)

    # Sort by date and bulk insert
    transactions.sort(key=lambda t: t.transaction_date)
    db.add_all(transactions)
    db.commit()

    jwt_token = create_jwt_token(user.id, user.email)
    return {
        "token": jwt_token,
        "user": {"id": user.id, "email": user.email, "name": user.name, "picture": user.picture or ""},
        "message": "Demo account created with sample transactions",
        "transactions_count": len(transactions),
    }
