import sys
from pathlib import Path

# Ensure the repository root is on sys.path so tests can import `backend`.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
