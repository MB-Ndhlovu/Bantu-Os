"""
Crypto wallet service — Phase 2 skeleton.

Exports
-------
CryptoWalletService : the service class
TOOL_SCHEMAS        : dict of tool name → JSON schema
"""

from bantu_os.services.crypto.crypto_service import CryptoWalletService
from bantu_os.services.crypto import schemas as schemas

TOOL_SCHEMAS = schemas.TOOL_SCHEMAS

__all__ = ["CryptoWalletService", "TOOL_SCHEMAS"]
