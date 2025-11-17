# password_utils.py
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2"],
    default="argon2",
    deprecated="auto",
)

def hash_password(plain: str) -> str:
    """Hash plain password (Argon2)."""
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    """Verify plain password against stored hash."""
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False

def needs_rehash(hashed: str) -> bool:
    """Use to migrate hashes if you change config later."""
    try:
        return pwd_context.needs_update(hashed)
    except Exception:
        return False