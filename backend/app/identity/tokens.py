"""Cryptographic token generation, hashing, and timing-safe verification for Kairo Identity."""

import hashlib
import secrets
import string


def hash_token(raw_token: str) -> str:
    """Compute SHA-256 hex digest of a token."""
    if not raw_token:
        return ""
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


def verify_token(raw_token: str, expected_hash: str) -> bool:
    """Timing-safe verification of raw token against stored SHA-256 hash."""
    if not raw_token or not expected_hash:
        return False
    computed = hash_token(raw_token)
    return secrets.compare_digest(computed, expected_hash)


def generate_session_token() -> str:
    """Generate cryptographically secure bearer token for an interactive session."""
    return f"kairo_stk_{secrets.token_urlsafe(32)}"


def generate_pairing_code() -> str:
    """Generate high-entropy, short-lived single-use pairing code (e.g. PAIR-A8X9-2KF3)."""
    alphabet = string.ascii_uppercase + string.digits
    # Exclude ambiguous characters (0, O, 1, I)
    clean_alphabet = [c for c in alphabet if c not in ("0", "O", "1", "I")]
    part1 = "".join(secrets.choice(clean_alphabet) for _ in range(4))
    part2 = "".join(secrets.choice(clean_alphabet) for _ in range(4))
    return f"PAIR-{part1}-{part2}"


def generate_handoff_token() -> str:
    """Generate short-lived, single-use, scoped handoff token."""
    return f"kairo_hnd_{secrets.token_urlsafe(32)}"


def mask_token(token: str | None) -> str:
    """Safely redact token for logs and audit trails."""
    if not token or len(token) < 8:
        return "[REDACTED]"
    return f"{token[:6]}...[REDACTED]...{token[-4:]}"
