from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, JSON
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    picture = Column(Text)
    # Profile fields for PDF password generation
    first_name = Column(String(100))
    last_name = Column(String(100))
    dob = Column(Date)  # Date of birth
    pan_first5 = Column(String(10))  # First 5 chars of PAN (e.g., ABCDE)
    mobile_last5 = Column(String(5))  # Last 5 digits of registered mobile
    # JSON dict mapping bank_name -> customer_id (for banks needing CRN/CIF)
    customer_ids = Column(JSON, default=dict)
    profile_completed = Column(Integer, default=0)  # 0=no, 1=yes
    google_access_token = Column(Text)
    google_refresh_token = Column(Text)
    google_token_expiry = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
