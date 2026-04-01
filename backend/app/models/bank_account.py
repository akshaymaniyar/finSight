from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from app.database import Base


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bank_name = Column(String(100), nullable=False)
    account_type = Column(String(20), nullable=False)  # SAVINGS, CURRENT, CREDIT_CARD
    account_number_masked = Column(String(50))
    card_network = Column(String(50))  # VISA, MASTERCARD, RUPAY
    nickname = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "bank_name", "account_number_masked", name="uq_user_bank_acct"),
    )
