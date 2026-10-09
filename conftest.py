import sys
from pathlib import Path

# Allow `import ckinject` in tests without requiring `pip install -e tool`.
sys.path.insert(0, str(Path(__file__).parent / "tool"))
