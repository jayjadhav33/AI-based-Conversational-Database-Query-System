from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.models.query_history import QueryHistory

class DatabaseConn(Base):
    __tablename__ = "databases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    db_type = Column(String(50), nullable=False)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    database_name = Column(String(255), nullable=False)
    username = Column(String(100), nullable=False)
    encrypted_password = Column(String(255), nullable=False)
    queries = relationship("QueryHistory", backref="database", cascade="all, delete-orphan", passive_deletes=True)
