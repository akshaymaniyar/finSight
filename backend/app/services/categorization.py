"""
Transaction categorization engine.

Classifies transactions by matching merchant names and descriptions
against keyword rules. Also flags self-transfers, investments, mutual
funds, and Zerodha transactions.
"""

from __future__ import annotations

import logging
from typing import Dict

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
    "EMI": [
        "emi", "loan", "equated monthly", "bajaj finserv", "home credit",
        "hdfc ltd", "lic housing", "pnb housing", "loan repayment",
        "auto debit emi",
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
) -> dict:
    """Categorize a transaction based on merchant name and raw description.

    Args:
        merchant: The merchant/payee name.
        description: The raw transaction description text.
        card_type: ACCOUNT, CREDIT_CARD, or DEBIT_CARD.
        transaction_type: DEBIT or CREDIT.

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

    # Match against category rules
    for category, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw in combined:
                result["category"] = category
                logger.debug("Categorized: merchant=%s -> category=%s, flags={self_transfer=%s, investment=%s, mutual_fund=%s, zerodha=%s}", merchant, result["category"], result["is_self_transfer"], result["is_investment"], result["is_mutual_fund"], result["is_zerodha"])
                return result

    logger.debug("Categorized: merchant=%s -> category=%s, flags={self_transfer=%s, investment=%s, mutual_fund=%s, zerodha=%s}", merchant, result["category"], result["is_self_transfer"], result["is_investment"], result["is_mutual_fund"], result["is_zerodha"])
    return result
