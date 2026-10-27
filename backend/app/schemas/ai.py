from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime

class ChatMessage(BaseModel):
    role: str # "user" or "assistant"
    content: str

class AskAIRequest(BaseModel):
    question: str
    history: List[ChatMessage] = []

class AskAIResponse(BaseModel):
    generated_sql: str
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class QueryHistoryItem(BaseModel):
    id: int
    database_id: int
    database_name: str
    question: str
    generated_sql: str
    created_at: datetime

    class Config:
        from_attributes = True
