from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class QueryRequest(BaseModel):
    sql_query: str

class QueryResponse(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
