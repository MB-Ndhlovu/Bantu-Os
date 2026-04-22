"""API key management for Bantu-OS Network API."""

from __future__ import annotations

import json
import secrets
import time
from pathlib import Path
from typing import Any, Dict


class APIKeyStore:
    """
    Persistent API key store backed by a JSON file.

    Each key maps to:
      - key_id: short stable ID (e.g. "key_4f3a")
      - key_hash: SHA256 of the full key (for lookup)
      - created_at: unix timestamp
      - tier: "free" | "pro" | "enterprise"
      - rate_limit: requests per minute
      - label: optional user label
    """

    def __init__(self, storage_path: str | Path = "/etc/bantu/api_keys.json") -> None:
        self._path = Path(storage_path)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            self._cache = {}
            return
        try:
            self._cache = json.loads(self._path.read_text())
        except Exception:
            self._cache = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._cache, indent=2))

    @staticmethod
    def _hash_key(key: str) -> str:
        import hashlib

        return hashlib.sha256(key.encode()).hexdigest()

    async def verify(self, key: str) -> bool:
        """Check whether an API key exists and is valid."""
        h = self._hash_key(key)
        entry = self._cache.get(h)
        if entry is None:
            return False
        if entry.get("expires_at") and entry["expires_at"] < time.time():
            return False
        return True

    async def get_key_info(self, key: str) -> Dict[str, Any]:
        """Return metadata about a key (no secrets)."""
        h = self._hash_key(key)
        entry = self._cache.get(h, {})
        return {
            "key_id": entry.get("key_id", ""),
            "tier": entry.get("tier", "free"),
            "rate_limit": entry.get("rate_limit", 60),
            "label": entry.get("label", ""),
            "created_at": entry.get("created_at", 0),
        }

    async def create_key(
        self,
        *,
        tier: str = "free",
        rate_limit: int = 60,
        label: str = "",
        expires_at: float | None = None,
    ) -> tuple[str, Dict[str, Any]]:
        """Create a new API key. Returns (full_key, metadata)."""
        key_id = f"key_{secrets.token_hex(4)}"
        full_key = f"bnta_{secrets.token_urlsafe(24)}"
        h = self._hash_key(full_key)

        entry: Dict[str, Any] = {
            "key_id": key_id,
            "created_at": time.time(),
            "tier": tier,
            "rate_limit": rate_limit,
            "label": label,
        }
        if expires_at:
            entry["expires_at"] = expires_at

        self._cache[h] = entry
        self._save()
        return full_key, entry

    async def revoke(self, key: str) -> bool:
        """Remove a key from the store."""
        h = self._hash_key(key)
        if h in self._cache:
            del self._cache[h]
            self._save()
            return True
        return False

    async def list_keys(self) -> list[Dict[str, Any]]:
        """List all keys (metadata only, no secrets)."""
        return [
            {
                "key_id": v["key_id"],
                "tier": v.get("tier", "free"),
                "rate_limit": v.get("rate_limit", 60),
                "label": v.get("label", ""),
                "created_at": v.get("created_at", 0),
                "expires_at": v.get("expires_at"),
            }
            for v in self._cache.values()
        ]
