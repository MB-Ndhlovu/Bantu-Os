"""Password utilities for Bantu-OS authentication."""

from __future__ import annotations

import hashlib
import hmac
import secrets


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash a password with a random salt using PBKDF2-HMAC-SHA256."""
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        600_000,
    )
    return digest.hex(), salt


def verify_password(password: str, hash_hex: str, salt: str) -> bool:
    """Verify a password against a stored PBKDF2 hash."""
    check_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(check_hash, hash_hex)


def generate_api_key() -> str:
    """Generate a cryptographically random API key."""
    return f"btu_{secrets.token_urlsafe(32)}"
