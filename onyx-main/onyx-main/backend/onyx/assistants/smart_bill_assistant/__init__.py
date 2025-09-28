"""Smart Bill Assistant package

Provides parsing of emails/PDFs for bills, storage in Onyx key-value store,
and a FastAPI router to query and confirm sandbox actions.
"""

from .api import router  # noqa: F401
