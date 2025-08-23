"""Top‑level package for the graphical Heroes‑like game.

This package can be executed either as a script (``python main.py``) or as a
module (``python -m FG.main`` when the repository is cloned as ``FG``).  The
codebase historically relied on *absolute* imports such as ``import
constants`` or ``from loaders import biomes`` which only work when the project
root is on :data:`sys.path`.

When the project is executed as a module, Python places the *parent* directory
of this package on ``sys.path`` which breaks those absolute imports.  To retain
backwards compatibility while still allowing module execution, we ensure the
package directory itself is available on the import path.
"""

from __future__ import annotations

import os
import sys

# Make the package directory importable as top‑level modules when running via
# ``python -m <package>.main``.  This preserves existing absolute imports such
# as ``import constants`` or ``from loaders import biomes``.
package_dir = os.path.dirname(__file__)
if package_dir not in sys.path:  # pragma: no cover - simple path manipulation
    sys.path.insert(0, package_dir)

