"""Sandboxed file service — restricts all ops to a user's directory tree."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class SandboxedFileService:
    """
    File service that is confined to a single user's directory.

    Every read, write, delete, copy, move, and list operation is
    checked against the sandbox root. Operations that escape the
    sandbox are rejected with PermissionError.
    """

    def __init__(self, sandbox_path: str) -> None:
        self._sandbox = Path(sandbox_path).resolve()
        # Ensure sandbox exists on startup
        self._sandbox.mkdir(parents=True, exist_ok=True)

    # ── Path validation ──────────────────────────────────────────────────────

    def _resolve(self, path: str) -> Path:
        """Resolve a path and verify it's inside the sandbox."""
        try:
            resolved = (self._sandbox / path).resolve()
        except Exception as exc:
            raise ValueError(f"Invalid path {path!r}: {exc}") from exc
        # Symlink check — resolve symlinks to catch /sandbox/../../../etc attacks
        resolved_str = str(resolved)
        sandbox_str = str(self._sandbox)
        if (
            not resolved_str.startswith(sandbox_str + "/")
            and resolved_str != sandbox_str
        ):
            raise PermissionError(f"Path escape attempt blocked: {path}")
        return resolved

    def _check_file_exists(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not path.is_file():
            raise IsADirectoryError(f"Not a file: {path}")

    def _check_dir_exists(self, path: Path) -> None:
        if not path.exists():
            raise NotADirectoryError(f"Directory not found: {path}")
        if not path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")

    # ── Read / Write ─────────────────────────────────────────────────────────

    def read(
        self,
        path: str,
        max_bytes: int = 1_000_000,
        encoding: str = "utf-8",
    ) -> str:
        p = self._resolve(path)
        self._check_file_exists(p)
        data = p.read_bytes()[:max_bytes]
        return data.decode(encoding, errors="replace")

    def write(
        self,
        path: str,
        content: str,
        *,
        allow_overwrite: bool = False,
        create_parents: bool = True,
        encoding: str = "utf-8",
    ) -> Dict[str, Any]:
        p = self._resolve(path)
        if p.is_dir():
            raise IsADirectoryError(f"Target is a directory: {path}")
        if p.exists() and not allow_overwrite:
            raise FileExistsError(f"Refusing to overwrite existing file: {path}")
        if not p.exists() and create_parents:
            p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding=encoding)
        return self._stat_result(p)

    def append(
        self, path: str, content: str, encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding=encoding) as f:
            f.write(content)
        return self._stat_result(p)

    def delete(self, path: str, *, confirm: bool = False) -> bool:
        if not confirm:
            raise PermissionError("Deletion requires confirm=True")
        p = self._resolve(path)
        self._check_file_exists(p)
        p.unlink()
        return True

    def copy(
        self,
        src: str,
        dst: str,
        *,
        allow_overwrite: bool = False,
    ) -> Dict[str, Any]:
        src_p = self._resolve(src)
        dst_p = self._resolve(dst)
        self._check_file_exists(src_p)
        if dst_p.exists() and not allow_overwrite:
            raise FileExistsError(f"Refusing to overwrite: {dst}")
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        import shutil

        shutil.copy2(src_p, dst_p)
        return self._stat_result(dst_p)

    def move(
        self,
        src: str,
        dst: str,
        *,
        allow_overwrite: bool = False,
    ) -> Dict[str, Any]:
        src_p = self._resolve(src)
        dst_p = self._resolve(dst)
        self._check_file_exists(src_p)
        if dst_p.exists() and not allow_overwrite:
            raise FileExistsError(f"Refusing to overwrite: {dst}")
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        import shutil

        shutil.move(str(src_p), str(dst_p))
        return self._stat_result(dst_p)

    def list_dir(
        self, path: str = ".", recursive: bool = False
    ) -> List[Dict[str, Any]]:
        p = self._resolve(path)
        self._check_dir_exists(p)
        entries = []
        if recursive:
            for fp in sorted(p.rglob("*")):
                entries.append(self._stat_result(fp))
        else:
            for fp in sorted(p.iterdir()):
                entries.append(self._stat_result(fp))
        return entries

    def stat(self, path: str) -> Dict[str, Any]:
        p = self._resolve(path)
        if not p.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        return self._stat_result(p)

    def search(
        self, root: str = ".", pattern: str = "*", recursive: bool = True
    ) -> List[str]:
        p = self._resolve(root)
        self._check_dir_exists(p)
        if recursive:
            matches = [str(f) for f in p.rglob(pattern)]
        else:
            matches = [str(f) for f in p.glob(pattern)]
        # Strip sandbox prefix from returned paths so AI sees relative paths
        sandbox_str = str(self._sandbox)
        return [m.replace(sandbox_str + "/", "") for m in sorted(matches)]

    def ensure_dir(self, path: str = ".") -> Dict[str, Any]:
        p = self._resolve(path)
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
        return self._stat_result(p)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _stat_result(self, path: Path) -> Dict[str, Any]:
        stat = path.stat()
        return {
            "path": str(path),
            "name": path.name,
            "type": "dir" if path.is_dir() else "file",
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "permissions": oct(stat.st_mode)[-3:],
            "checksum": self._checksum(path) if path.is_file() else None,
        }

    @staticmethod
    def _checksum(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
