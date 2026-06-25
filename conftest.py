"""Make the repo root importable so `import core`, `import backend`, etc. resolve
regardless of where pytest is invoked from. Stdlib only — must not pull in deps.
"""

import sys
from pathlib import Path

_ROOT = str(Path(__file__).parent.resolve())
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
