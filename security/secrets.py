"""
Bantu-OS Secrets Manager

Provides secure access to credentials without hardcoding.
Reads from environment variables first, then encrypted file storage.

Never log or print secret values.
"""

from __future__ import annotations

import json
import os
import re
import struct
from base64 import b64decode, b64encode
from hashlib import sha256
from hmac import HMAC
from pathlib import Path
from typing import Optional

# Optional: cryptography for encrypted file support
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGC
    from cryptography.hazmat.primitives.kdf.argon2 import Argon2PasswordBased
    from cryptography.hazmat.backends import default_backend

    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False


SECRETS_DIR = Path.home() / ".bantu"
SECRETS_FILE = SECRETS_DIR / "secrets.enc"
ENV_PREFIX = "BANTU_SECRET_"
MAX_SECRET_NAME_LEN = 128
MAX_SECRET_VALUE_LEN = 8192


def _validate_name(name: str) -> None:
    """Validate secret name to prevent injection."""
    if not name:
        raise ValueError("Secret name cannot be empty")
    if len(name) > MAX_SECRET_NAME_LEN:
        raise ValueError(f"Secret name too long (max {MAX_SECRET_NAME_LEN})")
    if not re.match(r"^[A-Z][A-Z0-9_]*$", name):
        raise ValueError(
            "Secret name must be uppercase letters, numbers, underscores, "
            "start with a letter"
        )


def _validate_value(value: str) -> None:
    """Validate secret value."""
    if len(value) > MAX_SECRET_VALUE_LEN:
        raise ValueError(f"Secret value too long (max {MAX_SECRET_VALUE_LEN})")


class SecretsManager:
    """
    Manages secrets from environment and encrypted storage.

    Priority:
    1. Environment variable BANTU_SECRET_<NAME>
    2. Encrypted secrets file (~/.bantu/secrets.enc)
    """

    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize SecretsManager.

        Args:
            key: Optional decryption key. If None, encrypted storage is disabled.
        """
        self._key = key
        self._cache: dict[str, str] = {}
        self._secrets_file_cache: Optional[dict[str, str]] = None

    def get(self, name: str) -> Optional[str]:
        """
        Retrieve a secret by name.

        Args:
            name: Secret name (e.g. "OPENAI_API_KEY")

        Returns:
            Secret value or None if not found.
        """
        _validate_name(name)

        # Check cache first
        if name in self._cache:
            return self._cache[name]

        # 1. Environment variable
        env_name = f"{ENV_PREFIX}{name}"
        value = os.environ.get(env_name)
        if value is not None:
            _validate_value(value)
            self._cache[name] = value
            return value

        # 2. Encrypted file
        if self._key is not None:
            secrets = self._load_secrets_file()
            if secrets is not None and name in secrets:
                value = secrets[name]
                _validate_value(value)
                self._cache[name] = value
                return value

        return None

    def __getitem__(self, name: str) -> str:
        """Get secret or raise KeyError."""
        value = self.get(name)
        if value is None:
            raise KeyError(f"Secret not found: {name}")
        return value

    def __contains__(self, name: str) -> bool:
        """Check if secret exists."""
        try:
            return self.get(name) is not None
        except ValueError:
            return False

    def _load_secrets_file(self) -> Optional[dict[str, str]]:
        """Load and decrypt secrets file."""
        if not _HAS_CRYPTO or self._key is None:
            return None
        if not SECRETS_FILE.exists():
            return None
        if self._secrets_file_cache is not None:
            return self._secrets_file_cache

        try:
            data = SECRETS_FILE.read_bytes()
            # Format: nonce (12 bytes) + ciphertext + tag (16 bytes)
            if len(data) < 28:
                return None
            nonce = data[:12]
            ciphertext = data[12:]

            aes = AESGC(self._key)
            try:
                plaintext = aes.decrypt(nonce, ciphertext, None)
            except Exception:
                return None

            secrets = json.loads(plaintext.decode("utf-8"))
            self._secrets_file_cache = secrets
            return secrets
        except Exception:
            return None

    def set(self, name: str, value: str) -> None:
        """
        Store a secret in memory cache (not persisted to file by this method).

        Args:
            name: Secret name
            value: Secret value
        """
        _validate_name(name)
        _validate_value(value)
        self._cache[name] = value

    def clear_cache(self) -> None:
        """Clear in-memory cache. Does not affect environment or files."""
        self._cache.clear()
        self._secrets_file_cache = None


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """
    Derive a decryption key from password using Argon2id.

    Args:
        password: User password
        salt: Salt bytes (should be 16+ bytes)

    Returns:
        32-byte AES key
    """
    if not _HAS_CRYPTO:
        raise RuntimeError("cryptography library not installed")
    kdf = Argon2PasswordBased(
        algorithm=__import__(
            "cryptography.hazmat.primitives.hashalgorithms",
            fromlist=["Argon2id"]
        ).Argon2id(),
        length=32,
        salt=salt,
        iterations=3,
        memory_cost=65536,
        parallelism=4,
        backend=default_backend(),
    )
    return kdf.derive(password.encode())


def create_secrets_file(secrets: dict[str, str], key: bytes) -> None:
    """
    Create or update the encrypted secrets file.

    Args:
        secrets: Dict of secret names to values
        key: 32-byte AES key
    """
    if not _HAS_CRYPTO:
        raise RuntimeError("cryptography library not installed")
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)

    plaintext = json.dumps(secrets, ensure_ascii=True).encode("utf-8")
    nonce = os.urandom(12)
    aes = AESGC(key)
    ciphertext = aes.encrypt(nonce, plaintext, None)

    SECRETS_FILE.write_bytes(nonce + ciphertext)
    SECRETS_FILE.chmod(0o600)


# Global instance for convenience
_default_manager: Optional[SecretsManager] = None


def get_manager() -> SecretsManager:
    """Get the default secrets manager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = SecretsManager()
    return _default_manager


def get_secret(name: str) -> Optional[str]:
    """Convenience function to get a secret from the default manager."""
    return get_manager().get(name)
