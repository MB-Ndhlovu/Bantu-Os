"""Password utilities for Bantu-OS authentication."""

from __future__ import annotations

import hashlib
import secrets


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash a password with a random salt using SHA-256.

    Returns (hash_hex, salt_hex).
    """
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode())
    for _ in range(100_000):
        h.update(salt.encode())
    return h.hexdigest(), salt


def verify_password(password: str, hash_hex: str, salt: str) -> bool:
    """Verify a password against a stored hash."""
    check_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(check_hash, hash_hex)


def generate_api_key() -> str:
    """Generate a cryptographically random API key."""
    return f"btu_{secrets.token_urlsafe(32)}"
