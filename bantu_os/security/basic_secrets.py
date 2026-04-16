"""
Bantu-OS Security Module: Secrets Management

Provides encrypted storage and retrieval for sensitive credentials
including API keys, OAuth tokens, and service keys.
"""

import os
import json
import hashlib
import hmac
import base64
import secrets
import time
from pathlib import Path
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


# Constants
SECRETS_DIR = Path("/home/workspace/.z/secrets")
VAULT_FILE = SECRETS_DIR / "vault.json"
MASTER_KEY_ENV = "BANTU_OS_MASTER_KEY"
ITERATIONS = 100_000
KEY_LEN = 32  # AES-256
NONCE_LEN = 12


class SecretsVault:
    """
    Encrypted secrets vault using AES-256-GCM.
    
    Secrets are stored encrypted at rest and decrypted only when retrieved.
    Access is logged for audit purposes.
    """
    
    def __init__(self, secrets_dir: Path = SECRETS_DIR):
        self.secrets_dir = secrets_dir
        self.secrets_dir.mkdir(parents=True, exist_ok=True)
        self._master_key = self._get_master_key()
        self._audit_log: list[dict] = []
    
    def _get_master_key(self) -> bytes:
        """Derive encryption key from master key or environment."""
        env_key = os.environ.get(MASTER_KEY_ENV)
        if env_key:
            # Use environment key directly (base64 encoded)
            return base64.b64decode(env_key)
        
        # Generate a per-installation key if none exists
        key_file = self.secrets_dir / ".master.key"
        if key_file.exists():
            return key_file.read_bytes()
        
        # Create new master key
        key = secrets.token_bytes(KEY_LEN)
        key_file.write_bytes(key)
        os.chmod(key_file, 0o600)
        return key
    
    def _derive_key(self, secret_name: str, salt: bytes) -> bytes:
        """Derive a unique key for each secret using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_LEN,
            salt=salt,
            iterations=ITERATIONS,
            backend=default_backend()
        )
        return kdf.derive(self._master_key + secret_name.encode())
    
    def _encrypt(self, value: str, secret_name: str) -> tuple[bytes, bytes, bytes]:
        """Encrypt a secret value. Returns (ciphertext, nonce, salt)."""
        salt = secrets.token_bytes(16)
        key = self._derive_key(secret_name, salt)
        nonce = secrets.token_bytes(NONCE_LEN)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, value.encode(), None)
        return ciphertext, nonce, salt
    
    def _decrypt(self, ciphertext: bytes, nonce: bytes, salt: bytes, secret_name: str) -> str:
        """Decrypt a secret value."""
        key = self._derive_key(secret_name, salt)
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode()
    
    def _load_vault(self) -> dict:
        """Load encrypted vault from disk."""
        if not VAULT_FILE.exists():
            return {"version": 1, "secrets": {}}
        try:
            return json.loads(VAULT_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            return {"version": 1, "secrets": {}}
    
    def _save_vault(self, vault: dict) -> None:
        """Save encrypted vault to disk."""
        VAULT_FILE.write_text(json.dumps(vault))
        os.chmod(VAULT_FILE, 0o600)
    
    def _audit(self, action: str, secret_name: str, success: bool) -> None:
        """Log secret access for audit trail."""
        entry = {
            "timestamp": time.time(),
            "action": action,
            "secret_name": secret_name,
            "success": success,
        }
        self._audit_log.append(entry)
    
    def set_secret(self, name: str, value: str) -> bool:
        """
        Store a secret encrypted at rest.
        
        Args:
            name: Unique identifier for the secret
            value: The sensitive value to store
            
        Returns:
            True if stored successfully
        """
        try:
            vault = self._load_vault()
            ciphertext, nonce, salt = self._encrypt(value, name)
            
            vault["secrets"][name] = {
                "ciphertext": base64.b64encode(ciphertext).decode(),
                "nonce": base64.b64encode(nonce).decode(),
                "salt": base64.b64encode(salt).decode(),
                "created_at": time.time(),
            }
            self._save_vault(vault)
            self._audit("set", name, True)
            return True
        except Exception as e:
            self._audit("set", name, False)
            return False
    
    def get_secret(self, name: str) -> Optional[str]:
        """
        Retrieve a decrypted secret.
        
        Args:
            name: Identifier of the secret to retrieve
            
        Returns:
            Decrypted value or None if not found
        """
        try:
            vault = self._load_vault()
            if name not in vault["secrets"]:
                self._audit("get", name, False)
                return None
            
            entry = vault["secrets"][name]
            ciphertext = base64.b64decode(entry["ciphertext"])
            nonce = base64.b64decode(entry["nonce"])
            salt = base64.b64decode(entry["salt"])
            
            value = self._decrypt(ciphertext, nonce, salt, name)
            self._audit("get", name, True)
            return value
        except Exception as e:
            self._audit("get", name, False)
            return None
    
    def delete_secret(self, name: str) -> bool:
        """
        Irreversibly delete a secret.
        
        Args:
            name: Identifier of the secret to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            vault = self._load_vault()
            if name in vault["secrets"]:
                del vault["secrets"][name]
                self._save_vault(vault)
                self._audit("delete", name, True)
                return True
            self._audit("delete", name, False)
            return False
        except Exception as e:
            self._audit("delete", name, False)
            return False
    
    def list_secrets(self) -> list[str]:
        """
        List all secret names (not values).
        
        Returns:
            List of secret identifiers
        """
        vault = self._load_vault()
        self._audit("list", "*", True)
        return list(vault["secrets"].keys())
    
    def rotate_secret(self, name: str) -> bool:
        """
        Re-encrypt a secret with a new key derivation.
        Requires the current value to be re-provided.
        
        Args:
            name: Identifier of the secret to rotate
            
        Returns:
            True if rotated successfully
        """
        try:
            current = self.get_secret(name)
            if current is None:
                return False
            return self.set_secret(name, current)
        except Exception:
            return False
    
    def get_audit_log(self) -> list[dict]:
        """Return the audit log for this session."""
        return self._audit_log.copy()


# Global vault instance
_vault: Optional[SecretsVault] = None


def get_vault() -> SecretsVault:
    """Get or create the global vault instance."""
    global _vault
    if _vault is None:
        _vault = SecretsVault()
    return _vault


def get_secret(name: str) -> Optional[str]:
    """Convenience function to get a secret from the global vault."""
    return get_vault().get_secret(name)


def set_secret(name: str, value: str) -> bool:
    """Convenience function to set a secret in the global vault."""
    return get_vault().set_secret(name, value)


def delete_secret(name: str) -> bool:
    """Convenience function to delete a secret from the global vault."""
    return get_vault().delete_secret(name)


def list_secrets() -> list[str]:
    """Convenience function to list secrets from the global vault."""
    return get_vault().list_secrets()
