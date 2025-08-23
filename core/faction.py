from enum import Enum

class Faction(Enum):
    """Playable factions.

    Only ``RED_KNIGHTS`` is currently implemented but the enum is designed
    so additional factions can be added in the future.
    """

    RED_KNIGHTS = "Red Knights"
