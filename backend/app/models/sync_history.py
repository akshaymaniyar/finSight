from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, Index
from app.database import Base


class SyncHistory(Base):
    __tablename__ = "sync_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sync_month = Column(Date, nullable=False)
    sync_status = Column(String(20), nullable=False)  # IN_PROGRESS, COMPLETED, FAILED, PARTIAL
    emails_found = Column(Integer, default=0)
    emails_parsed = Column(Integer, default=0)
    transactions_created = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    __table_args__ = (
        Index("idx_sync_user_month", "user_id", "sync_month"),
    )
