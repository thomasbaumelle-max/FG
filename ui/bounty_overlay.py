from __future__ import annotations

import pygame

def open(screen: pygame.Surface, game, town, hero, clock) -> None:
    """Open the bounty/quest overlay using the game's journal."""
    if hasattr(game, "open_journal"):
        game.open_journal(screen)
