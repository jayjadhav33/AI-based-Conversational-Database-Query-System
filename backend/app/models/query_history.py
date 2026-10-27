from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.models.base import Base

class QueryHistory(Base):
    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    database_id = Column(Integer, ForeignKey("databases.id", ondelete="CASCADE"), nullable=False)
    question = Column(String(1000), nullable=False)
    generated_sql = Column(String(2000), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
