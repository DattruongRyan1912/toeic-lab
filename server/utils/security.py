"""Authentication and security utilities: password hashing and JWT token handling.

Zero third-party dependencies: uses Python standard library hashlib, hmac, secrets,
and RFC 7519 compliant JSON Web Token (HS256) implementation.
"""
import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional

from server.config import ACCESS_TOKEN_EXPIRE_DAYS, SECRET_KEY


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with 100,000 iterations and a secure random salt."""
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    return f"pbkdf2:sha256:100000${salt}${pw_hash}"


def verify_password(password: str, hashed: Optional[str]) -> bool:
    """Verify a plain password against the stored PBKDF2 hash using timing-safe comparison."""
    if not hashed or not password:
        return False
    try:
        header, salt, pw_hash = hashed.split("$")
        scheme, algo, iters = header.split(":")
        if scheme != "pbkdf2" or algo != "sha256":
            return False
        computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iters)).hex()
        return hmac.compare_digest(computed, pw_hash)
    except Exception:
        return False


def _b64_url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64_url_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def create_access_token(user_id: int, username: str, expires_in_seconds: Optional[int] = None) -> str:
    """Create a signed RFC 7519 JWT (HS256) token."""
    if expires_in_seconds is None:
        expires_in_seconds = ACCESS_TOKEN_EXPIRE_DAYS * 86400

    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + expires_in_seconds,
    }

    header_b64 = _b64_url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64_url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64_url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> dict:
    """Decode and verify an RFC 7519 JWT (HS256) token.
    
    Raises ValueError if signature is invalid or token has expired.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token format")

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()

    try:
        actual_sig = _b64_url_decode(sig_b64)
    except Exception as exc:
        raise ValueError("Malformed token signature") from exc

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Signature verification failed")

    try:
        payload = json.loads(_b64_url_decode(payload_b64).decode("utf-8"))
    except Exception as exc:
        raise ValueError("Malformed token payload") from exc

    now = int(time.time())
    if "exp" in payload and payload["exp"] < now:
        raise ValueError("Token has expired")

    return payload
