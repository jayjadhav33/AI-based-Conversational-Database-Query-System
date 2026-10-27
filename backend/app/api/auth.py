import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.db import get_db
from app.schemas.user import UserCreate, UserLogin, UserOut, Token, GoogleLoginRequest
from app.models.user import User
from app.security.auth import get_password_hash, verify_password, create_access_token
from app.api.deps import get_current_user

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()

@router.post("/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(name=user.name, email=user.email, password_hash=hashed_password, auth_provider="local")
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not db_user.password_hash or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer", "user": db_user}

from dotenv import load_dotenv

@router.post("/google", response_model=Token)
def google_auth(request: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a user using a Google OAuth ID token.
    Verifies the token with Google and creates or logs in the user.
    Supports clock skew tolerance and authoritative Google tokeninfo fallback.
    """
    from pathlib import Path
    _env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(dotenv_path=_env_path, override=True)
    load_dotenv(override=True)
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip().strip("\"'")

    if not request.token:
        raise HTTPException(status_code=400, detail="Missing Google ID token")

    idinfo = None
    verification_errors = []

    # Strategy 1: Verify locally via google.oauth2.id_token with 5-minute clock skew tolerance
    try:
        req = google_requests.Request()
        idinfo = id_token.verify_oauth2_token(
            request.token,
            req,
            audience=client_id if client_id else None,
            clock_skew_in_seconds=300
        )
    except Exception as e:
        verification_errors.append(f"Local verification error: {str(e)}")

    # Strategy 2: Fallback to Google's authoritative tokeninfo endpoint
    if not idinfo:
        try:
            import requests as http_requests
            resp = http_requests.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={request.token}",
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                token_aud = data.get("aud")
                token_azp = data.get("azp")
                # Verify audience if client_id configured
                if client_id and client_id not in (token_aud, token_azp):
                    raise HTTPException(
                        status_code=401,
                        detail=f"Google Client ID mismatch. Backend has '{client_id[:12]}...', but token is for aud='{str(token_aud)[:12]}...', azp='{str(token_azp)[:12]}...'."
                    )
                idinfo = data
            else:
                verification_errors.append(f"Google tokeninfo response ({resp.status_code}): {resp.text.strip()}")
        except HTTPException:
            raise
        except Exception as e:
            verification_errors.append(f"Tokeninfo HTTP fallback error: {str(e)}")

    if not idinfo:
        err_msg = " | ".join(verification_errors)
        print(f"[Google Auth Failed] {err_msg}")
        raise HTTPException(
            status_code=401,
            detail=f"Google token verification failed: {err_msg}"
        )

    email = idinfo.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google token does not contain an email address")

    name = idinfo.get("name") or (email.split("@")[0] if email else "Google User")
    picture = idinfo.get("picture")

    # Check if user already exists
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Create a new user for Google Sign-In
        user = User(
            name=name,
            email=email,
            password_hash=None,
            auth_provider="google",
            avatar_url=picture
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update user's avatar or name if missing
        updated = False
        if picture and not user.avatar_url:
            user.avatar_url = picture
            updated = True
        if name and not user.name:
            user.name = name
            updated = True
        if updated:
            db.commit()
            db.refresh(user)

    # Generate our internal application JWT token
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
