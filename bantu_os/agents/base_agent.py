"""
Base Agent - Abstract base class for all Bantu OS agents.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseAgent(ABC):
    """Abstract base class for all Bantu OS agents."""
    
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.context: Dict[str, Any] = {}
        self.is_active = False
    
    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """Process input data and return a response."""
        pass
    
    def update_context(self, new_context: Dict[str, Any]) -> None:
        """Update the agent's context."""
        self.context.update(new_context)
    
    def reset(self) -> None:
        """Reset the agent's state."""
        self.context = {}
        self.is_active = False
