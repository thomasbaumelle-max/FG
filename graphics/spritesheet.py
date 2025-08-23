"""Utility helpers for working with sprite sheets."""
from __future__ import annotations

from typing import List

import pygame


def load_sprite_sheet(sheet_path: str, frame_width: int, frame_height: int) -> List[pygame.Surface]:
    """Load a sprite sheet and slice it into individual frames.

    Parameters
    ----------
    sheet_path: str
        Path to the sprite sheet image file.
    frame_width: int
        Width of a single frame in pixels.
    frame_height: int
        Height of a single frame in pixels.

    Returns
    -------
    List[pygame.Surface]
        List of surfaces representing individual frames extracted from the
        sprite sheet. Frames are ordered left-to-right, top-to-bottom.
    """
    sheet = pygame.image.load(sheet_path).convert_alpha()
    sheet_rect = sheet.get_rect()
    frames: List[pygame.Surface] = []
    for y in range(0, sheet_rect.height, frame_height):
        for x in range(0, sheet_rect.width, frame_width):
            frame_surface = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame_surface.blit(sheet, (0, 0), pygame.Rect(x, y, frame_width, frame_height))
            frames.append(frame_surface)
    return frames
