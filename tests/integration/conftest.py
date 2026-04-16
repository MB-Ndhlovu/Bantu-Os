import sys
from pathlib import Path

import pytest

THIS_FILE = Path(__file__).resolve()

# Walk up from tests/integration/ to the repo root.
for parent in THIS_FILE.parents:
    if (parent / "bantu_os").is_dir():
        root = parent
        break
else:
    root = THIS_FILE.parents[2]

if str(root) not in sys.path:
    sys.path.insert(0, str(root))


@pytest.fixture(autouse=True)
def stub_llm_provider(monkeypatch):
    """Override the parent's autouse stub_llm_provider to avoid importing
    bantu_os modules (which may have import errors in this environment).
    Integration tests for init.c and shell binary don't need LLM stubs.
    """
    pass
