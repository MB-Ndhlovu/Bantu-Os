# Bantu-OS Services Base
# Common interfaces and patterns for system services

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class ServiceBase(ABC):
    """
    Base class for all Bantu-OS services.

    Provides common interface for initialization, health checks,
    and operation logging.
    """

    def __init__(self, name: str = "service"):
        self.name = name
        self._initialized_at: Optional[str] = None
        self._operation_log: list = []

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Check service health and return status."""
        pass

    def get_service_info(self) -> Dict[str, Any]:
        """Get basic service information."""
        return {
            "name": self.name,
            "initialized_at": self._initialized_at,
            "operation_count": len(self._operation_log),
        }

    def _log_operation(self, operation: str, details: Any) -> None:
        """Log an operation for audit trail."""
        self._operation_log.append(
            {
                "operation": operation,
                "details": str(details),
                "timestamp": datetime.now().isoformat(),
            }
        )
