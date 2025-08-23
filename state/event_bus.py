"""Simple publish/subscribe event bus used across the UI and game code."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Dict, List, Union
from weakref import WeakMethod

EventCallback = Callable[..., None]
Subscriber = Union[EventCallback, WeakMethod]


class EventBus:
    """Minimalistic event dispatcher.

    Subscribers register callbacks for string based event identifiers.  When an
    event is published all callbacks for that name are invoked with the supplied
    positional and keyword arguments.  The implementation is intentionally
    lightweight – no error handling is performed and callbacks are executed
    synchronously.
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Subscriber]] = defaultdict(list)

    def subscribe(self, event: str, callback: EventCallback) -> None:
        """Register ``callback`` to be invoked when ``event`` is published."""

        if hasattr(callback, "__self__") and getattr(callback, "__self__") is not None:
            self._subscribers[event].append(WeakMethod(callback))
        else:
            self._subscribers[event].append(callback)

    def publish(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Invoke all callbacks subscribed to ``event``."""

        subs = self._subscribers.get(event, [])
        for cb in list(subs):
            if isinstance(cb, WeakMethod):
                func = cb()
                if func is None:
                    subs.remove(cb)
                    continue
                func(*args, **kwargs)
            else:
                cb(*args, **kwargs)


# Global bus instance used by modules -----------------------------------
EVENT_BUS = EventBus()

# Event name constants ---------------------------------------------------
ON_SELECT_HERO = "on_select_hero"
ON_RESOURCES_CHANGED = "on_resources_changed"
ON_TURN_END = "on_turn_end"
ON_CAMERA_CHANGED = "on_camera_changed"
ON_ENEMY_DEFEATED = "on_enemy_defeated"
ON_INFO_MESSAGE = "on_info_message"
ON_ASSET_LOAD_PROGRESS = "on_asset_load_progress"
