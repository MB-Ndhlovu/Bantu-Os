import sys
from pathlib import Path

# Ensure the project root (containing the bantu_os package) is on sys.path
THIS_FILE = Path(__file__).resolve()
for parent in [THIS_FILE.parent, *THIS_FILE.parents]:
    if (parent / "bantu_os").is_dir():
        root = parent
        break
else:
    root = THIS_FILE.parents[2]

if str(root) not in sys.path:
    sys.path.insert(0, str(root))
