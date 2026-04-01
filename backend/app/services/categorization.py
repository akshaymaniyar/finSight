"""
Transaction categorization engine.

Classifies transactions by matching merchant names and descriptions
against keyword rules. Also flags self-transfers, investments, mutual
funds, and Zerodha transactions.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

CATEGORY_RULES: Dict[str, list[str]] = {
    "Food & Dining": [
        "swiggy", "zomato", "dominos", "pizza hut", "mcdonalds", "burger king",
        "kfc", "subway", "starbucks", "cafe coffee day", "ccd", "barbeque nation",
        "haldiram", "restaurant", "food", "dining", "biryani", "chai", "tea post",
        "chaayos", "behrouz", "faasos", "eatfit", "dineout", "eatsure",
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "ajio", "meesho", "nykaa", "tata cliq",
        "snapdeal", "shoppers stop", "westside", "reliance", "croma", "vijay sales",
        "decathlon", "ikea", "h&m", "zara", "uniqlo", "lifestyle", "pantaloons",
        "mall", "mart",
    ],
    "Groceries": [
        "bigbasket", "blinkit", "zepto", "instamart", "jiomart", "dunzo",
        "dmart", "more supermarket", "grofers", "nature basket", "spencers",
        "grocery", "supermarket", "fresh", "vegetables", "fruits",
    ],
    "Transportation": [
        "uber", "ola", "rapido", "metro", "irctc", "makemytrip", "goibibo",
        "cleartrip", "yatra", "indigo", "spicejet", "air india", "vistara",
        "akasa", "redbus", "abhibus", "fuel", "petrol", "diesel", "hp ",
        "indian oil", "bpcl", "shell", "fastag", "toll", "parking",
    ],
    "Bills & Utilities": [
        "electricity", "water bill", "gas bill", "broadband", "wifi",
        "airtel", "jio", "vi ", "vodafone", "bsnl", "tata sky", "dish tv",
        "d2h", "postpaid", "prepaid", "recharge", "mobile bill",
        "internet", "piped gas", "adani gas", "mahanagar gas", "torrent power",
        "bescom", "msedcl", "tata power", "reliance energy",
    ],
    "Entertainment": [
        "netflix", "amazon prime", "hotstar", "disney", "spotify", "gaana",
        "youtube", "zee5", "sonyliv", "jiocinema", "apple music", "audible",
        "bookmyshow", "pvr", "inox", "cinepolis", "movie", "gaming",
        "playstation", "xbox", "steam", "epic games",
    ],
    "Health": [
        "pharmacy", "medical", "hospital", "doctor", "apollo", "medplus",
        "netmeds", "pharmeasy", "1mg", "practo", "tata 1mg", "diagnostic",
        "lab", "pathology", "dentist", "clinic", "healthcare", "wellness",
        "gym", "cult.fit", "cultfit",
    ],
    "Education": [
        "school", "college", "university", "udemy", "coursera", "unacademy",
        "byju", "upgrad", "simplilearn", "education", "tuition", "coaching",
        "exam", "books", "library", "kindle",
    ],
    "Rent": [
        "rent", "house rent", "flat rent", "pg rent", "rental",
        "nobroker", "magicbricks", "99acres",
    ],
    "Loans": [
        "loan", "bajaj finserv", "home credit",
        "hdfc ltd", "lic housing", "pnb housing", "loan repayment",
    ],
    "Insurance": [
        "insurance", "lic ", "max life", "hdfc life", "icici prudential",
        "sbi life", "star health", "policy", "premium", "policybazaar",
        "digit insurance", "acko", "tata aia",
    ],
    "Subscriptions": [
        "subscription", "membership", "annual fee", "renewal", "recurring",
        "apple", "google storage", "icloud", "dropbox", "notion", "chatgpt",
        "github", "linkedin premium",
    ],
    "ATM Withdrawal": [
        "atm", "cash withdrawal", "atm withdrawal", "cash wdl",
        "nfs withdrawal", "self withdrawal",
    ],
    "Salary/Income": [
        "salary", "payroll", "stipend", "dividend", "interest credited",
        "cashback", "refund", "reversal", "credit interest",
    ],
}

MUTUAL_FUND_KEYWORDS: list[str] = [
    "sip", "groww", "kuvera", "coin", "mf purchase", "mutual fund",
    "nippon", "hdfc mf", "icici pru", "aditya birla", "dsp",
    "kotak mf", "axis mf", "tata mf", "parag parikh",
]

ZERODHA_KEYWORDS: list[str] = [
    "zerodha", "coin by zerodha", "razorpay zerodha",
]

INVESTMENT_KEYWORDS: list[str] = (
    MUTUAL_FUND_KEYWORDS
    + ZERODHA_KEYWORDS
    + [
        "fd ", "fixed deposit", "ppf", "nps", "stocks", "upstox",
        "smallcase", "angel broking", "angel one", "indiabulls",
    ]
)

SELF_TRANSFER_KEYWORDS: list[str] = [
    "self", "own account", "self transfer", "neft-self", "imps-self", "upi-self",
]


CC_PAYMENT_KEYWORDS: list[str] = [
    "cc payment", "credit card payment", "cc bill", "card bill payment",
    "billpay", "bill payment", "bppy cc payment", "cc pymt",
    "payment received", "payment thank", "autopay",
]

CC_REFUND_KEYWORDS: list[str] = [
    "refund", "reversal", "cashback", "reward", "milestone",
    "discount", "rebate", "credit adjustment", "emi cancel",
]


def categorize_transaction(
    merchant: str,
    description: str = "",
    card_type: str = "ACCOUNT",
    transaction_type: str = "DEBIT",
    user_rules: Optional[list] = None,
    db_categories: Optional[list] = None,
) -> dict:
    """Categorize a transaction based on merchant name and raw description.

    Uses DB categories for leaf-level matching when available:
    1. User-defined rules (highest priority)
    2. DB subcategory keyword matching (leaf level)
    3. DB parent category keyword matching (if no subcategory matched)
    4. Hardcoded CATEGORY_RULES fallback

    Args:
        merchant: The merchant/payee name.
        description: The raw transaction description text.
        card_type: ACCOUNT, CREDIT_CARD, or DEBIT_CARD.
        transaction_type: DEBIT or CREDIT.
        user_rules: User's CategoryRule records.
        db_categories: All Category records for the user (parents + children).

    Returns:
        Dict with keys: category, sub_category, is_investment, is_mutual_fund,
        is_zerodha, is_self_transfer, is_excluded.
    """
    combined = f"{merchant} {description}".lower().strip()

    result = {
        "category": "Uncategorized",
        "sub_category": None,
        "is_investment": False,
        "is_mutual_fund": False,
        "is_zerodha": False,
        "is_self_transfer": False,
        "is_excluded": False,
    }

    # --- Check user-defined rules first (highest priority) ---
    if user_rules:
        merchant_lower = (merchant or "").strip().lower()
        for rule in user_rules:
            if rule.merchant_pattern and (
                rule.merchant_pattern in merchant_lower or merchant_lower == rule.merchant_pattern
            ):
                result["category"] = rule.category
                result["sub_category"] = rule.sub_category
                return result

    # --- Credit card CREDIT transactions: never income ---
    if card_type == "CREDIT_CARD" and transaction_type == "CREDIT":
        # Check if it's a bill payment
        for kw in CC_PAYMENT_KEYWORDS:
            if kw in combined:
                result["category"] = "CC Bill Payment"
                result["is_excluded"] = True
                return result

        # Check if it's a refund/cashback
        for kw in CC_REFUND_KEYWORDS:
            if kw in combined:
                result["category"] = "Refund/Cashback"
                result["sub_category"] = "Credit Card"
                return result

        # Default: categorize CC credits as Refund/Cashback (not income)
        result["category"] = "Refund/Cashback"
        result["sub_category"] = "Credit Card"
        return result

    if not combined.strip():
        return result

    # Check self-transfers first
    for kw in SELF_TRANSFER_KEYWORDS:
        if kw in combined:
            result["is_self_transfer"] = True
            result["is_excluded"] = True
            result["category"] = "Self Transfer"
            break

    # Check investments
    for kw in MUTUAL_FUND_KEYWORDS:
        if kw in combined:
            result["is_mutual_fund"] = True
            result["is_investment"] = True
            result["category"] = "Investments"
            result["sub_category"] = "Mutual Fund"
            break

    for kw in ZERODHA_KEYWORDS:
        if kw in combined:
            result["is_zerodha"] = True
            result["is_investment"] = True
            result["category"] = "Investments"
            result["sub_category"] = "Zerodha"
            break

    if not result["is_investment"]:
        for kw in INVESTMENT_KEYWORDS:
            if kw in combined:
                result["is_investment"] = True
                result["category"] = "Investments"
                break

    # If already categorized as self-transfer or investment, skip rule matching
    if result["category"] not in ("Uncategorized",):
        return result

    # --- DB category matching (leaf-level first) ---
    if db_categories:
        # Build parent lookup
        parents = {c.id: c for c in db_categories if c.parent_id is None}
        children = [c for c in db_categories if c.parent_id is not None]

        # Pass 1: Try subcategory keywords (leaf level — most specific)
        for child in children:
            if not child.keywords:
                continue
            for kw in child.keywords.split(","):
                kw = kw.strip().lower()
                if kw and kw in combined:
                    parent = parents.get(child.parent_id)
                    if parent:
                        result["category"] = parent.name
                        result["sub_category"] = child.name
                        return result

        # Pass 2: No subcategory matched — try parent-level (broader)
        # (parents don't have keywords by default, but just in case)
        for parent in parents.values():
            if parent.keywords:
                for kw in parent.keywords.split(","):
                    kw = kw.strip().lower()
                    if kw and kw in combined:
                        result["category"] = parent.name
                        return result

    # --- Fallback: hardcoded CATEGORY_RULES ---
    for category, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw in combined:
                result["category"] = category
                # Try to find matching subcategory from DB for this parent
                if db_categories:
                    parent_match = next(
                        (c for c in db_categories if c.parent_id is None and c.name == category),
                        None,
                    )
                    if parent_match:
                        children = [c for c in db_categories if c.parent_id == parent_match.id and c.keywords]
                        for child in children:
                            for ckw in child.keywords.split(","):
                                ckw = ckw.strip().lower()
                                if ckw and ckw in combined:
                                    result["sub_category"] = child.name
                                    return result
                        # No subcategory matched — use "Other" if it exists
                        other = next(
                            (c for c in db_categories if c.parent_id == parent_match.id and c.name == "Other"),
                            None,
                        )
                        if other:
                            result["sub_category"] = "Other"
                return result

    return result
