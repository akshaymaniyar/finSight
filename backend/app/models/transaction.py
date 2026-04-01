from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Boolean, Numeric, ForeignKey, Index
from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    statement_id = Column(Integer, ForeignKey("statements.id", ondelete="CASCADE"), nullable=True)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True)
    transaction_type = Column(String(10), nullable=False)  # DEBIT, CREDIT
    amount = Column(Numeric(15, 2), nullable=False)
    merchant = Column(String(500))
    raw_description = Column(Text)
    category = Column(String(100))
    sub_category = Column(String(100))
    transaction_date = Column(Date, nullable=False)
    value_date = Column(Date)
    reference_id = Column(String(255))
    balance_after = Column(Numeric(15, 2))
    is_self_transfer = Column(Boolean, default=False)
    is_investment = Column(Boolean, default=False)
    is_mutual_fund = Column(Boolean, default=False)
    is_zerodha = Column(Boolean, default=False)
    is_excluded = Column(Boolean, default=False)
    card_type = Column(String(20), default="ACCOUNT")  # DEBIT_CARD, CREDIT_CARD, ACCOUNT
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_txn_user_date", "user_id", "transaction_date"),
        Index("idx_txn_user_category", "user_id", "category"),
        Index("idx_txn_statement", "statement_id"),
    )
