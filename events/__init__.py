"""Event handling registry."""

from . import handlers

# Mapping of event type strings to handler callables.
EVENT_REGISTRY = {
    "explore_tile": handlers.explore_tile,
    "recruit_unit": handlers.recruit_unit,
}


def dispatch(game, event):
    """Dispatch an ``event`` dictionary using the registry.

    Parameters
    ----------
    game:
        Game instance providing context for the handler.
    event:
        Dictionary containing at least ``type`` and optional ``params``.
    """
    handler = EVENT_REGISTRY.get(event.get("type"))
    if not handler:
        raise KeyError(f"Unknown event type: {event.get('type')}")
    params = event.get("params", {})
    handler(game, params)

__all__ = ["EVENT_REGISTRY", "dispatch"]
