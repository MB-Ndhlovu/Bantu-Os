"""
SettingsManager - JSON-based configuration loader/updater for Bantu OS.

This complements Pydantic Settings for environment-driven config by providing
simple runtime-configurable settings persisted to a JSON file.

Default file location: bantu_os/config/settings.json
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

from . import settings as runtime_settings


DEFAULT_CONFIG_PATH = Path(__file__).parent / "settings.json"


@dataclass
class SettingsManager:
    path: Path = field(default_factory=lambda: DEFAULT_CONFIG_PATH)
    data: Dict[str, Any] = field(default_factory=dict)

    def load(self) -> None:
        if not self.path.exists():
            # Initialize with defaults if file missing
            self.data = {
                "default_llm": runtime_settings.DEFAULT_LLM_MODEL,
                "memory_provider": "vectordb",
                "voice_enabled": False,
            }
            self.save()
            return
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            # Fallback to sane defaults if file is corrupt
            self.data = {
                "default_llm": runtime_settings.DEFAULT_LLM_MODEL,
                "memory_provider": "vectordb",
                "voice_enabled": False,
            }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

    # Convenience accessors
    @property
    def default_llm(self) -> str:
        return str(self.data.get("default_llm", runtime_settings.DEFAULT_LLM_MODEL))

    @property
    def memory_provider(self) -> str:
        return str(self.data.get("memory_provider", "vectordb"))

    @property
    def voice_enabled(self) -> bool:
        return bool(self.data.get("voice_enabled", False))
