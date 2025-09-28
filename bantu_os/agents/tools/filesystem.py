"""
Filesystem tools.
"""
from __future__ import annotations

from pathlib import Path
from typing import List


def list_dir(path: str) -> List[str]:
    """List directory entries (names only)."""
    p = Path(path)
    if not p.exists() or not p.is_dir():
        raise FileNotFoundError(f"Not a directory: {path}")
    return sorted([e.name for e in p.iterdir()])


def read_text(path: str, max_bytes: int = 4096) -> str:
    """Read a text file with a maximum size guard."""
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"Not a file: {path}")
    data = p.read_bytes()[:max_bytes]
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return data.decode(errors="replace")
