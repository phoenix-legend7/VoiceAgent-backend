"""Encryption utilities for sensitive data."""
from cryptography.fernet import Fernet
from app.core.config import settings
import base64
import hashlib

def get_encryption_key() -> bytes:
    """Generate a consistent encryption key from SECRET_KEY."""
    # Use SECRET_KEY to derive a Fernet key
    secret = settings.SECRET_KEY.encode()
    # Hash the secret key to get 32 bytes
    key = hashlib.sha256(secret).digest()
    # Base64 encode to get Fernet-compatible key
    return base64.urlsafe_b64encode(key)

_fernet = None

def get_fernet() -> Fernet:
    """Get or create Fernet instance."""
    global _fernet
    if _fernet is None:
        key = get_encryption_key()
        _fernet = Fernet(key)
    return _fernet

def encrypt_value(value: str) -> str:
    """Encrypt a string value."""
    if not value:
        return value
    fernet = get_fernet()
    encrypted = fernet.encrypt(value.encode())
    return encrypted.decode()

def decrypt_value(encrypted_value: str) -> str:
    """Decrypt an encrypted string value."""
    if not encrypted_value:
        return encrypted_value
    fernet = get_fernet()
    try:
        decrypted = fernet.decrypt(encrypted_value.encode())
        return decrypted.decode()
    except Exception as e:
        # If decryption fails, return as-is (might be unencrypted legacy data)
        return encrypted_value

