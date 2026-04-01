from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # NULL = global default
    name = Column(String(100), nullable=False)
    icon = Column(String(50))  # emoji or icon name
    color = Column(String(7))  # hex color like #FF5733
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    is_income = Column(Boolean, default=False)  # True for income-type categories
    is_system = Column(Boolean, default=True)  # System defaults can't be deleted
    sort_order = Column(Integer, default=0)
    keywords = Column(Text)  # comma-separated keywords for auto-categorization
    created_at = Column(DateTime, default=datetime.utcnow)

    parent = relationship("Category", remote_side=[id], backref="subcategories")
