from cryptography.fernet import Fernet
import os
import base64
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)
load_dotenv()

# We need a 32-url-safe-base64-encoded bytes key for Fernet.
# Let's derive it simply from the SECRET_KEY in .env by padding/hashing it to 32 bytes.
import hashlib
raw_key = os.getenv("SECRET_KEY", "fallback_secret_key").encode('utf-8')
m = hashlib.sha256()
m.update(raw_key)
FERNET_KEY = base64.urlsafe_b64encode(m.digest())
f = Fernet(FERNET_KEY)

def encrypt_db_password(plain_password: str) -> str:
    return f.encrypt(plain_password.encode('utf-8')).decode('utf-8')

def decrypt_db_password(encrypted_password: str) -> str:
    return f.decrypt(encrypted_password.encode('utf-8')).decode('utf-8')
