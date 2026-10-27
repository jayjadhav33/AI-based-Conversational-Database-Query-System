from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.database_conn import DatabaseConn
from app.schemas.query import QueryRequest, QueryResponse
from app.services.query_service import execute_safe_query
from app.security.encryption import decrypt_db_password

router = APIRouter(
    prefix="/query",
    tags=["Query Execution"]
)

@router.post("/{db_id}", response_model=QueryResponse)
def execute_query(db_id: int, request: QueryRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_conn = db.query(DatabaseConn).filter(DatabaseConn.id == db_id, DatabaseConn.user_id == current_user.id).first()
    if not db_conn:
        raise HTTPException(status_code=404, detail="Database not found")
    
    plain_password = decrypt_db_password(db_conn.encrypted_password)
    
    success, msg, data = execute_safe_query(
        host=db_conn.host,
        port=db_conn.port,
        user=db_conn.username,
        password=plain_password,
        database=db_conn.database_name,
        sql_query=request.sql_query
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=msg)
        
    return data
