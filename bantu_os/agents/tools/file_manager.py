"""
File management tools with safety checks to avoid accidental overwrites/deletes.

Functions:
- list_files(path: str, recursive: bool = False) -> list[str]
- read_file(path: str, max_bytes: int = 1_000_000, encoding: str = "utf-8") -> str
- write_file(path: str, content: str, *, allow_overwrite: bool = False, create_parents: bool = True, encoding: str = "utf-8") -> str
- delete_file(path: str, *, confirm: bool = False) -> bool

Notes:
- write_file refuses to overwrite unless allow_overwrite=True.
- delete_file requires confirm=True.
- read_file limits size via max_bytes and decodes text.
"""
from __future__ import annotations

from pathlib import Path
from typing import List


def list_files(path: str, recursive: bool = False) -> List[str]:
    p = Path(path)
    if not p.exists() or not p.is_dir():
        raise FileNotFoundError(f"Not a directory: {path}")
    if recursive:
        return sorted([str(fp) for fp in p.rglob("*") if fp.is_file()])
    return sorted([str(fp) for fp in p.iterdir() if fp.is_file()])


def read_file(path: str, max_bytes: int = 1_000_000, encoding: str = "utf-8") -> str:
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"Not a file: {path}")
    data = p.read_bytes()[:max_bytes]
    return data.decode(encoding, errors="replace")


def write_file(
    path: str,
    content: str,
    *,
    allow_overwrite: bool = False,
    create_parents: bool = True,
    encoding: str = "utf-8",
) -> str:
    p = Path(path)
    if p.exists() and p.is_dir():
        raise IsADirectoryError(f"Target is a directory: {path}")
    if p.exists() and not allow_overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    if not p.exists() and create_parents:
        p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding=encoding)
    return str(p)


def delete_file(path: str, *, confirm: bool = False) -> bool:
    if not confirm:
        raise PermissionError("Deletion requires confirm=True to proceed")
    p = Path(path)
    if not p.exists():
        return False
    if p.is_dir():
        raise IsADirectoryError("Refusing to delete a directory with this helper")
    p.unlink()
    return True
