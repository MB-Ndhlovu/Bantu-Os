"""
Configuration module for Bantu OS.
"""

from .settings import Settings
from .settings_manager import SettingsManager

# Create a global settings instance
settings = Settings()

__all__ = ['settings', 'SettingsManager']
