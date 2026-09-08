"""Cryptographic utilities for password hashing, token generation, and signature verification."""

import base64
import hashlib
import hmac
import os
import secrets


def hash_password(password: str, salt: bytes | None = None) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations and random salt."""
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        100_000,
    )
    # Format: salt_b64:key_b64
    salt_b64 = base64.b64encode(salt).decode("utf-8")
    key_b64 = base64.b64encode(key).decode("utf-8")
    return f"{salt_b64}:{key_b64}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed salt:key string using constant-time comparison."""
    try:
        parts = hashed_password.split(":")
        if len(parts) != 2:
            return False
        salt = base64.b64decode(parts[0])
        expected_key = base64.b64decode(parts[1])
        candidate_key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            100_000,
        )
        return hmac.compare_digest(expected_key, candidate_key)
    except Exception:
        return False


def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure random token string."""
    return secrets.token_urlsafe(length)


def sign_token(token: str, secret_key: str) -> str:
    """Produce HMAC-SHA256 signature for token."""
    signature = hmac.new(
        secret_key.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{token}.{signature}"


def verify_signed_token(signed_token: str, secret_key: str) -> str | None:
    """Verify signed token signature and return raw token string if valid, else None."""
    try:
        parts = signed_token.rsplit(".", 1)
        if len(parts) != 2:
            return None
        token, signature = parts
        expected_sig = hmac.new(
            secret_key.encode("utf-8"),
            token.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if hmac.compare_digest(expected_sig, signature):
            return token
        return None
    except Exception:
        return None
