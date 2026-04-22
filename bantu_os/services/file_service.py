# Bantu-OS File Service
# AI-native file operations with safety and metadata

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class FileService:
    """
    System service for AI-powered file operations.

    Handles read/write/copy/move/delete with safety checks,
    metadata extraction, and AI context awareness.
    """

    def __init__(self, base_path: str = "/home/workspace"):
        self.base_path = Path(base_path)
        self._operation_log: List[Dict[str, Any]] = []

    def read(
        self, path: str, max_bytes: int = 1_000_000, encoding: str = "utf-8"
    ) -> str:
        """Read file contents with size guard and encoding support."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not p.is_file():
            raise IsADirectoryError(f"Not a file: {path}")

        data = p.read_bytes()[:max_bytes]
        self._log_operation("read", path, len(data))
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
        """Write content to file with safety checks."""
        p = Path(path)
        if p.exists() and p.is_dir():
            raise IsADirectoryError(f"Target is a directory: {path}")
        if p.exists() and not allow_overwrite:
            raise FileExistsError(f"Refusing to overwrite existing file: {path}")
        if not p.exists() and create_parents:
            p.parent.mkdir(parents=True, exist_ok=True)

        p.write_text(content, encoding=encoding)
        size = p.stat().st_size
        self._log_operation("write", path, size)

        return {
            "path": str(p),
            "size": size,
            "checksum": self._checksum(p),
            "timestamp": datetime.now().isoformat(),
        }

    def append(
        self, path: str, content: str, encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """Append content to file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        with open(p, "a", encoding=encoding) as f:
            f.write(content)

        size = p.stat().st_size
        self._log_operation("append", path, len(content))

        return {
            "path": str(p),
            "appended_bytes": len(content.encode(encoding)),
            "total_size": size,
            "timestamp": datetime.now().isoformat(),
        }

    def delete(self, path: str, *, confirm: bool = False) -> bool:
        """Delete file with explicit confirmation required."""
        if not confirm:
            raise PermissionError("Deletion requires confirm=True")

        p = Path(path)
        if not p.exists():
            return False

        if p.is_dir():
            raise IsADirectoryError("Use recursive delete for directories")

        p.unlink()
        self._log_operation("delete", path, 0)
        return True

    def copy(
        self, src: str, dst: str, *, allow_overwrite: bool = False
    ) -> Dict[str, Any]:
        """Copy file with safety checks."""
        src_p = Path(src)
        dst_p = Path(dst)

        if not src_p.exists():
            raise FileNotFoundError(f"Source not found: {src}")

        if dst_p.exists() and not allow_overwrite:
            raise FileExistsError(f"Refusing to overwrite: {dst}")

        dst_p.parent.mkdir(parents=True, exist_ok=True)
        import shutil

        shutil.copy2(src_p, dst_p)

        self._log_operation("copy", f"{src} -> {dst}", dst_p.stat().st_size)

        return {
            "source": str(src_p),
            "destination": str(dst_p),
            "size": dst_p.stat().st_size,
            "checksum": self._checksum(dst_p),
            "timestamp": datetime.now().isoformat(),
        }

    def move(
        self, src: str, dst: str, *, allow_overwrite: bool = False
    ) -> Dict[str, Any]:
        """Move file with safety checks."""
        src_p = Path(src)
        dst_p = Path(dst)

        if not src_p.exists():
            raise FileNotFoundError(f"Source not found: {src}")

        if dst_p.exists() and not allow_overwrite:
            raise FileExistsError(f"Refusing to overwrite: {dst}")

        dst_p.parent.mkdir(parents=True, exist_ok=True)
        import shutil

        shutil.move(str(src_p), str(dst_p))

        self._log_operation("move", f"{src} -> {dst}", dst_p.stat().st_size)

        return {
            "source": str(src_p),
            "destination": str(dst_p),
            "timestamp": datetime.now().isoformat(),
        }

    def list_dir(self, path: str, recursive: bool = False) -> List[Dict[str, Any]]:
        """List directory with metadata."""
        p = Path(path)
        if not p.exists() or not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")

        entries = []
        if recursive:
            for fp in sorted(p.rglob("*")):
                stat = fp.stat()
                entries.append(
                    {
                        "path": str(fp),
                        "name": fp.name,
                        "type": "dir" if fp.is_dir() else "file",
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )
        else:
            for fp in sorted(p.iterdir()):
                stat = fp.stat()
                entries.append(
                    {
                        "path": str(fp),
                        "name": fp.name,
                        "type": "dir" if fp.is_dir() else "file",
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )

        return entries

    def stat(self, path: str) -> Dict[str, Any]:
        """Get detailed file/directory statistics."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        stat = p.stat()
        return {
            "path": str(p),
            "name": p.name,
            "type": "dir" if p.is_dir() else "file",
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "permissions": oct(stat.st_mode)[-3:],
            "checksum": self._checksum(p) if p.is_file() else None,
        }

    def search(self, root: str, pattern: str, recursive: bool = True) -> List[str]:
        """Search for files matching pattern."""
        p = Path(root)
        if not p.exists():
            raise FileNotFoundError(f"Search root not found: {root}")

        matches = []
        if recursive:
            matches = [str(f) for f in p.rglob(pattern)]
        else:
            matches = [str(f) for f in p.glob(pattern)]

        self._log_operation("search", f"{root}/{pattern}", len(matches))
        return sorted(matches)

    def ensure_dir(self, path: str) -> Dict[str, Any]:
        """Ensure directory exists, creating if necessary."""
        p = Path(path)
        created = not p.exists()
        p.mkdir(parents=True, exist_ok=True)

        return {
            "path": str(p),
            "created": created,
            "timestamp": datetime.now().isoformat(),
        }

    def get_operation_log(self) -> List[Dict[str, Any]]:
        """Get history of file operations."""
        return self._operation_log.copy()

    def _log_operation(self, operation: str, path: str, size: int) -> None:
        self._operation_log.append(
            {
                "operation": operation,
                "path": path,
                "bytes": size,
                "timestamp": datetime.now().isoformat(),
            }
        )

    @staticmethod
    def _checksum(path: Path) -> str:
        """Calculate SHA256 checksum of file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
