"""
Helper utilities used across Bantu OS.
"""

from __future__ import annotations

import os
from typing import Any, Dict


def env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable."""
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}


def merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Shallow merge two dictionaries, override wins."""
    merged = base.copy()
    merged.update(override)
    return merged
