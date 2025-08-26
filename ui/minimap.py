"""Public entry points for the minimap widget.

This small wrapper re-exports the :class:`Minimap` implementation and the
mouse event constants used to enable click-and-drag recentring of the camera.
The actual logic lives in :mod:`ui.widgets.minimap` but keeping a light-weight
module at :mod:`ui.minimap` mirrors the historical API and allows other parts
of the UI to simply ``import ui.minimap``.
"""

from .widgets.minimap import Minimap, MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION

__all__ = ["Minimap", "MOUSEBUTTONDOWN", "MOUSEBUTTONUP", "MOUSEMOTION"]

