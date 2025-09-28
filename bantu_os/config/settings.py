"""
Application settings and configuration.
"""
import os
from typing import Dict, Any, Optional
from pathlib import Path

# Prefer pydantic-settings (Pydantic v2). Fallback to a no-op BaseSettings to avoid
# hard dependency during testing if package is absent.
try:
    from pydantic_settings import BaseSettings  # type: ignore
except Exception:  # pragma: no cover - fallback for environments without pydantic-settings
    class BaseSettings:  # minimal stub
        def __init__(self, **kwargs: Any) -> None:
            pass

class Settings(BaseSettings):
    """Application settings."""
    
    # Application settings
    APP_NAME: str = "Bantu OS"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"
    
    # LLM Settings
    DEFAULT_LLM_MODEL: str = "gpt-4"
    LLM_API_KEY: Optional[str] = None
    LLM_TEMPERATURE: float = 0.7
    
    # Vector Database
    VECTOR_DB_PATH: Path = DATA_DIR / "vector_db"
    VECTOR_DIM: int = 768
    
    # Knowledge Graph
    KNOWLEDGE_GRAPH_PATH: Path = DATA_DIR / "knowledge_graph"
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True
    
    def ensure_dirs_exist(self) -> None:
        """Ensure all required directories exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)
        self.KNOWLEDGE_GRAPH_PATH.mkdir(parents=True, exist_ok=True)
    
    def update_from_dict(self, settings_dict: Dict[str, Any]) -> None:
        """Update settings from a dictionary. """
        for key, value in settings_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)
