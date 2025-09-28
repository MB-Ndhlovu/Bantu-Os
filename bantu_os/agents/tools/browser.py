"""
Browser tool (minimal).

To avoid network dependencies in unit tests, this tool simply validates and
returns the URL. In future, replace with a fetcher using aiohttp if desired.
"""
from __future__ import annotations

from urllib.parse import urlparse


def open_url(url: str) -> str:
    """Validate and echo the URL.

    This is a placeholder for a richer browser tool. It prevents accidental
    network access during tests while keeping the tool contract stable.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Invalid URL")
    return url
