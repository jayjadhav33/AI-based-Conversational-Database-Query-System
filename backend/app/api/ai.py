from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.database_conn import DatabaseConn
from app.models.query_history import QueryHistory
from app.schemas.ai import AskAIRequest, AskAIResponse, QueryHistoryItem
from app.services.ai_service import ask_ai

router = APIRouter(
    prefix="/ai",
    tags=["AI Text-to-SQL"]
)

@router.post("/ask/{db_id}", response_model=AskAIResponse)
def handle_ask_ai(db_id: int, request: AskAIRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_conn = db.query(DatabaseConn).filter(DatabaseConn.id == db_id, DatabaseConn.user_id == current_user.id).first()
    if not db_conn:
        raise HTTPException(status_code=404, detail="Database not found")
        
    generated_sql, results, error = ask_ai(db_conn, request.question, request.history, db)
    
    return AskAIResponse(
        generated_sql=generated_sql,
        results=results,
        error=error
    )

@router.get("/history", response_model=List[QueryHistoryItem])
def get_query_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    history = db.query(QueryHistory, DatabaseConn.database_name)\
        .join(DatabaseConn, QueryHistory.database_id == DatabaseConn.id)\
        .filter(QueryHistory.user_id == current_user.id)\
        .order_by(QueryHistory.created_at.desc())\
        .limit(50).all()
        
    # Format the joined result
    formatted_history = []
    for h, db_name in history:
        formatted_history.append(QueryHistoryItem(
            id=h.id,
            database_id=h.database_id,
            database_name=db_name,
            question=h.question,
            generated_sql=h.generated_sql,
            created_at=h.created_at
        ))
        
    return formatted_history
