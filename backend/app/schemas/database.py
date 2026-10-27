from pydantic import BaseModel
from typing import Optional

class DatabaseBase(BaseModel):
    name: str
    db_type: str = "mysql"
    host: str
    port: int = 3306
    database_name: str
    username: str

class DatabaseCreate(DatabaseBase):
    password: str

class DatabaseOut(DatabaseBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

class TestConnection(DatabaseCreate):
    pass
