from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings
from cryptography.fernet import Fernet, InvalidToken
import base64
import os
import hashlib

pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def _derive_fernet_key_from_secret(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()  
    return base64.urlsafe_b64encode(digest)  

def _get_fernet() -> Fernet:
    raw = os.getenv("SECRETS_KEY")
    if raw:
        try:
            key_bytes = raw.encode("utf-8") if isinstance(raw, str) else raw
            return Fernet(key_bytes)
        except Exception:
            raise RuntimeError(
                "SECRETS_KEY inválida. Ela deve ser uma chave base64 urlsafe de 32 bytes "
                "(44 caracteres). Ex.: base64.urlsafe_b64encode(os.urandom(32)).decode()"
            )
    key_bytes = _derive_fernet_key_from_secret(settings.SECRET_KEY)
    return Fernet(key_bytes)

def encrypt_secret(value: str) -> str:
    f = _get_fernet()
    token = f.encrypt(value.encode("utf-8"))
    return token.decode("utf-8")

def decrypt_secret(token_str: str) -> str:
    f = _get_fernet()
    try:
        plain = f.decrypt(token_str.encode("utf-8"))
        return plain.decode("utf-8")
    except InvalidToken:
        raise ValueError("Secret inválido ou chave incorreta")
