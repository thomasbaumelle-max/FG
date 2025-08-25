"""Helpers for classifying combat status effects."""

from __future__ import annotations

BUFF_STATUSES = {"focus", "shield_block", "charge"}
DEBUFF_STATUSES = {"burn", "fear_-1"}


def categorize_status(name: str) -> str:
    """Return the category for a status effect.

    Parameters
    ----------
    name:
        Identifier of the status effect.

    Returns
    -------
    str
        ``"buff"`` when the status is beneficial, ``"debuff"`` when harmful
        and ``"neutral"`` for unclassified statuses.
    """
    if name in BUFF_STATUSES:
        return "buff"
    if name in DEBUFF_STATUSES:
        return "debuff"
    return "neutral"
