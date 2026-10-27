from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.db import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.database_conn import DatabaseConn
from app.services.schema_service import extract_schema
from app.security.encryption import decrypt_db_password

router = APIRouter(
    prefix="/schema",
    tags=["Schema"]
)

@router.get("/{db_id}")
def get_schema(db_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_conn = db.query(DatabaseConn).filter(DatabaseConn.id == db_id, DatabaseConn.user_id == current_user.id).first()
    if not db_conn:
        raise HTTPException(status_code=404, detail="Database not found")
    
    plain_password = decrypt_db_password(db_conn.encrypted_password)
    
    success, schema_or_error = extract_schema(
        host=db_conn.host,
        port=db_conn.port,
        user=db_conn.username,
        password=plain_password,
        database=db_conn.database_name
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to extract schema: {schema_or_error}")
        
    return {"database_name": db_conn.database_name, "schema": schema_or_error}
