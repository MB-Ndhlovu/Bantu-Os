"""
Built-in tools for Bantu OS agents.

Each tool is a plain callable that can be registered with AgentManager
or Kernel. Keep implementations minimal and dependency-light.
"""
from .calculator import calculate
from .filesystem import list_dir, read_text
from .browser import open_url
from .file_manager import list_files, read_file, write_file, delete_file
from .web_search import web_search

__all__ = [
    "calculate",
    "list_dir",
    "read_text",
    "open_url",
    "list_files",
    "read_file",
    "write_file",
    "delete_file",
    "web_search",
]
