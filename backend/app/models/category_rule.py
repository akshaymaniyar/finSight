from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from app.database import Base


class CategoryRule(Base):
    """User-defined merchant → category mapping rules.

    When a user manually categorizes a transaction, the merchant name
    is saved here so future transactions from the same merchant are
    auto-categorized.
    """
    __tablename__ = "category_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    merchant_pattern = Column(String(255), nullable=False)  # lowercase merchant name or pattern
    category = Column(String(100), nullable=False)
    sub_category = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "merchant_pattern", name="uq_user_merchant_rule"),
    )
