"""
Messaging service — Phase 2 skeleton.

Exports
-------
MessagingService : the service class
TOOL_SCHEMAS     : dict of tool name → JSON schema
"""

from bantu_os.services.messaging.messaging_service import MessagingService
from bantu_os.services.messaging import schemas as schemas

TOOL_SCHEMAS = schemas.TOOL_SCHEMAS

__all__ = ["MessagingService", "TOOL_SCHEMAS"]
