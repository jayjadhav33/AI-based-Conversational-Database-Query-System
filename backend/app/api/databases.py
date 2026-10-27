from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.database_conn import DatabaseConn
from app.models.query_history import QueryHistory
from app.schemas.database import DatabaseCreate, DatabaseOut, TestConnection
from app.services.database_service import test_mysql_connection
from app.security.encryption import encrypt_db_password

router = APIRouter(
    prefix="/databases",
    tags=["Databases"]
)

@router.get("/", response_model=List[DatabaseOut])
def list_databases(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(DatabaseConn).filter(DatabaseConn.user_id == current_user.id).all()

@router.post("/test")
def test_connection(conn: TestConnection, current_user: User = Depends(get_current_user)):
    success, msg = test_mysql_connection(
        host=conn.host,
        port=conn.port,
        user=conn.username,
        password=conn.password,
        database=conn.database_name
    )
    if not success:
        raise HTTPException(status_code=400, detail=f"Connection failed: {msg}")
    return {"message": "Connection successful"}

@router.post("/", response_model=DatabaseOut)
def add_database(conn: DatabaseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Test first
    success, msg = test_mysql_connection(
        host=conn.host,
        port=conn.port,
        user=conn.username,
        password=conn.password,
        database=conn.database_name
    )
    if not success:
        raise HTTPException(status_code=400, detail=f"Cannot add DB, connection failed: {msg}")
    
    # Save connection
    encrypted_pass = encrypt_db_password(conn.password)
    
    new_db = DatabaseConn(
        user_id=current_user.id,
        name=conn.name,
        db_type=conn.db_type,
        host=conn.host,
        port=conn.port,
        database_name=conn.database_name,
        username=conn.username,
        encrypted_password=encrypted_pass
    )
    db.add(new_db)
    db.commit()
    db.refresh(new_db)
    return new_db

@router.delete("/{db_id}")
def remove_database(db_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_conn = db.query(DatabaseConn).filter(DatabaseConn.id == db_id, DatabaseConn.user_id == current_user.id).first()
    if not db_conn:
        raise HTTPException(status_code=404, detail="Database not found")
    
    try:
        # Delete associated query history entries to maintain integrity
        db.query(QueryHistory).filter(QueryHistory.database_id == db_id).delete(synchronize_session=False)
        db.delete(db_conn)
        db.commit()
        return {"message": "Database configuration removed successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete database: {str(e)}")

