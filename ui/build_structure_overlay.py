from __future__ import annotations

import pygame
from loaders import icon_loader
from .town_common import COLOR_TEXT

FONT_NAME = None
COLOR_WARN = (210, 90, 70)
COLOR_DISABLED = (120, 120, 120)


def _can_afford(hero, cost: dict[str, int]) -> bool:
    gold = cost.get("gold", 0)
    if getattr(hero, "gold", 0) < gold:
        return False
    for res, amount in cost.items():
        if res == "gold":
            continue
        if hero.resources.get(res, 0) < amount:
            return False
    return True


def open(
    screen: pygame.Surface,
    town,
    hero,
    struct_id: str,
    clock: pygame.time.Clock | None = None,
    *,
    locked: bool = False,
) -> bool:
    """Open an overlay to confirm construction of ``struct_id``.

    Returns ``True`` if the player chose to build the structure.
    """

    info = town.structures.get(struct_id, {}) if town else {}
    desc = info.get("desc", "") if isinstance(info, dict) else ""
    prereq = info.get("prereq", []) if isinstance(info, dict) else []
    cost = town.structure_cost(struct_id) if town else {}

    font = pygame.font.SysFont(FONT_NAME, 18)
    font_small = pygame.font.SysFont(FONT_NAME, 14)
    font_big = pygame.font.SysFont(FONT_NAME, 20, bold=True)

    panel = pygame.Rect(0, 0, 360, 200)
    panel.center = screen.get_rect().center
    btn_build = pygame.Rect(0, 0, 120, 32)
    btn_cancel = pygame.Rect(0, 0, 120, 32)
    btn_build.topleft = (panel.x + 16, panel.bottom - 48)
    btn_cancel.topright = (panel.right - 16, panel.bottom - 48)

    clock = clock or pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_b):
                return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_cancel.collidepoint(event.pos):
                    return False
                if btn_build.collidepoint(event.pos):
                    if _can_afford(hero, cost) and not locked and all(
                        town.is_structure_built(p) for p in prereq
                    ):
                        return True

        # draw overlay
        s = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        s.fill((0, 0, 0, 160))
        screen.blit(s, (0, 0))
        pygame.draw.rect(screen, (40, 42, 50), panel, border_radius=8)
        pygame.draw.rect(screen, (110, 110, 120), panel, 2, border_radius=8)

        name = struct_id.replace("_", " ").title()
        screen.blit(font_big.render(name, True, COLOR_TEXT), (panel.x + 16, panel.y + 12))

        screen.blit(font.render(desc, True, COLOR_TEXT), (panel.x + 16, panel.y + 50))

        # cost row
        x = panel.x + 16
        y = panel.y + 90
        if cost:
            for res in ["gold", "wood", "stone", "crystal"]:
                if res in cost:
                    icon = icon_loader.get(f"resource_{res}", 24)
                    screen.blit(icon, (x, y))
                    amt = font.render(str(cost[res]), True, COLOR_TEXT)
                    screen.blit(amt, (x + 28, y + 4))
                    x += 80
        else:
            screen.blit(font.render("Gratuit", True, COLOR_TEXT), (x, y + 4))

        # prerequisites
        y += 40
        screen.blit(font.render("Requires:", True, COLOR_TEXT), (panel.x + 16, y))
        y += 24
        if prereq:
            for p in prereq:
                built = town.is_structure_built(p)
                col = COLOR_TEXT if built else COLOR_WARN
                screen.blit(
                    font_small.render(p.replace("_", " ").title(), True, col),
                    (panel.x + 32, y),
                )
                y += 20
        else:
            screen.blit(
                font_small.render("Aucun prérequis", True, COLOR_TEXT),
                (panel.x + 32, y),
            )

        can_build = _can_afford(hero, cost) and not locked and all(
            town.is_structure_built(p) for p in prereq
        )
        btn_col = (70, 140, 70) if can_build else COLOR_DISABLED
        pygame.draw.rect(screen, btn_col, btn_build, border_radius=4)
        pygame.draw.rect(screen, (90, 50, 50), btn_cancel, border_radius=4)
        screen.blit(
            font_big.render("Construire", True, COLOR_TEXT),
            (btn_build.x + 6, btn_build.y + 2),
        )
        screen.blit(
            font_big.render("Annuler", True, COLOR_TEXT),
            (btn_cancel.x + 12, btn_cancel.y + 2),
        )

        if locked:
            screen.blit(
                font_small.render(
                    "Vous avez déjà construit un bâtiment aujourd’hui",
                    True,
                    COLOR_WARN,
                ),
                (panel.x + 16, btn_build.y - 28),
            )

        pygame.display.update()
        clock.tick(60)

    return False


__all__ = ["open"]
