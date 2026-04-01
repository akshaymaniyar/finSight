from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from app.database import Base


class Statement(Base):
    __tablename__ = "statements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True)
    source_type = Column(String(20), nullable=False)  # EMAIL, PDF_ATTACHMENT
    gmail_message_id = Column(String(255))
    email_from = Column(String(255))
    email_subject = Column(Text)
    email_date = Column(DateTime)
    statement_month = Column(Date)
    raw_content = Column(MEDIUMTEXT)
    parse_status = Column(String(20), default="PENDING")  # PENDING, PARSED, FAILED, SKIPPED
    parse_error = Column(Text)
    transaction_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "gmail_message_id", name="uq_gmail_msg"),
    )
