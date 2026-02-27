import sys
from pathlib import Path

# Ensure the project root (parent of tests/) is on sys.path so tests can import modules like `maze`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
