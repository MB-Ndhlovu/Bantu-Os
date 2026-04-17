"""
Fintech service — Phase 2 skeleton.

Exports
-------
FintechService : the service class
TOOL_SCHEMAS   : dict of tool name → JSON schema
"""
from bantu_os.services.fintech.fintech_service import FintechService
from bantu_os.services.fintech import schemas as schemas

TOOL_SCHEMAS = schemas.TOOL_SCHEMAS

__all__ = ['FintechService', 'TOOL_SCHEMAS']