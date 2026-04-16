import sys
from pathlib import Path

import pytest

THIS_FILE = Path(__file__).resolve()

# Walk up from tests/integration/conftest.py to the repo root.
# The repo root contains the bantu_os package and pyproject.toml.
for parent in THIS_FILE.parents:
    if (parent / 'bantu_os').is_dir():
        root = parent
        break
else:
    root = THIS_FILE.parents[1]

if str(root) not in sys.path:
    sys.path.insert(0, str(root))