from pathlib import Path
from dotenv import load_dotenv

# Ensure environment variables are loaded regardless of current working directory
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.db import engine
from app.models.base import Base

# Import routers
from app.api.auth import router as auth_router
from app.api.databases import router as db_router
from app.api.schema import router as schema_router
from app.api.query import router as query_router
from app.api.ai import router as ai_router
from app.services.ai_service import get_inference_engine

# Create database tables safely
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Database initialization warning: {e}")

app = FastAPI(title="AI-Based Conversational Database Query System")

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173", 
        "http://localhost:3000", 
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(db_router, prefix="/api")
app.include_router(schema_router, prefix="/api")
app.include_router(query_router, prefix="/api")
app.include_router(ai_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Database Assistant API"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
