from __future__ import annotations
from typing import List, Tuple, Optional, Union
import pygame
import theme, audio

class TownOverlay:
    """Simple overlay listing player's towns using ``theme.PALETTE`` colours."""

    BG = theme.PALETTE["background"]
    PANEL = theme.PALETTE["panel"]
    ACCENT = theme.PALETTE["accent"]
    TEXT = theme.PALETTE["text"]

    def __init__(self, screen: pygame.Surface, game: "Game", towns: Optional[List["Town"]] = None) -> None:
        self.screen = screen
        self.game = game
        if towns is None:
            world = getattr(game, "world", None)
            data = getattr(world, "towns", [])
            if callable(data):
                towns = [t for t in data() if getattr(t, "owner", None) == 0]
            else:
                towns = [t for t in data if getattr(t, "owner", None) == 0]
        self.towns = towns
        if self.towns:
            faction = getattr(self.towns[0], "faction_id", None)
            if faction:
                try:
                    audio.play_music(f"town_{faction}")
                except Exception:
                    pass
        self.font = theme.get_font(16)
        self.town_rects: List[Tuple[pygame.Rect, "Town"]] = []
        audio.play_sound("panel_open")

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> Union[bool, "Town"]:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_u:
            audio.play_sound("panel_close")
            return True  # signal to caller to close overlay
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            audio.play_sound("panel_close")
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, town in self.town_rects:
                if rect.collidepoint(event.pos):
                    audio.play_sound("panel_close")
                    return town
        return False

    # ------------------------------------------------------------------
    def draw(self) -> List[pygame.Rect]:
        """Draw the overlay and return the list of updated rectangles."""
        w, h = self.screen.get_size()
        background = self.screen.copy()

        panel_w, panel_h = 300, 200
        panel_rect = pygame.Rect((w - panel_w) // 2, (h - panel_h) // 2, panel_w, panel_h)

        overlay = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        overlay.fill((*self.BG, 200))
        theme.draw_frame(overlay, overlay.get_rect())

        self.town_rects = []
        item_h = 40
        y = 20
        for town in self.towns:
            rect = pygame.Rect(20, y, panel_rect.width - 40, item_h)
            pygame.draw.rect(overlay, self.PANEL, rect)
            pygame.draw.rect(overlay, self.ACCENT, rect, 2)
            img = None
            assets = getattr(self.game, "assets", {})
            if assets:
                img = assets.get(getattr(town, "image", ""))
            if img:
                ih = item_h - 10
                try:
                    img = pygame.transform.smoothscale(img, (ih, ih))
                except Exception:
                    pass
                overlay.blit(img, (rect.x + 5, rect.y + 5))
                name_x = rect.x + ih + 10
            else:
                name_x = rect.x + 5
            if self.font:
                label = self.font.render(town.name, True, self.TEXT)
                overlay.blit(label, (name_x, rect.y + (item_h - label.get_height()) // 2))
            abs_rect = pygame.Rect(panel_rect.x + rect.x, panel_rect.y + rect.y, rect.width, rect.height)
            self.town_rects.append((abs_rect, town))
            y += item_h + 10

        background.blit(overlay, panel_rect.topleft)
        self.screen.blit(background, (0, 0))
        return [panel_rect]

# type hints for runtime
from typing import TYPE_CHECKING
if TYPE_CHECKING:  # pragma: no cover
    from core.game import Game
    from core.buildings import Town
