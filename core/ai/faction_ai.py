from __future__ import annotations

"""Simple faction AI controller.

This module defines :class:`FactionAI`, a small dataclass used by the game to
represent an enemy faction.  It keeps track of the faction's main town, the
heroes it controls and the associated economy data.  A :class:`FactionAI`
instance acts as the entry point for higher level behaviour such as town
management, unit recruitment and strategic movement across the world map.
"""

from dataclasses import dataclass, field
from typing import List

from core.buildings import Town
from core.entities import EnemyHero
from core import economy


@dataclass
class FactionAI:
    """Container representing an AI‑controlled faction.

    The faction AI is responsible for high level decisions including:

    * gestion des villes possédées par la faction ;
    * recrutement et renforcement des héros ennemis ;
    * déplacements stratégiques des armées contrôlées par l'ordinateur.
    """

    town: Town
    heroes: List[EnemyHero] = field(default_factory=list)
    economy: economy.PlayerEconomy = field(default_factory=economy.PlayerEconomy)
