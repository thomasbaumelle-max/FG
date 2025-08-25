import pygame
from types import SimpleNamespace
import constants
from core.world import WorldMap, BIOME_IMAGES
from core.combat import Combat
from core import combat_render
from core.entities import UnitStats, Unit
from core.game import Game


def _ensure_stub_functions(monkeypatch):
    if not hasattr(pygame.Surface, "get_size"):
        monkeypatch.setattr(
            pygame.Surface,
            "get_size",
            lambda self: (self.get_width(), self.get_height()),
            raising=False,
        )
    if not hasattr(pygame, "BLEND_RGBA_ADD"):
        monkeypatch.setattr(pygame, "BLEND_RGBA_ADD", 1, raising=False)
    if not hasattr(pygame, "transform"):
        class _T:
            @staticmethod
            def rotate(surf, angle):
                return surf
            @staticmethod
            def smoothscale(surf, size):
                return surf
            @staticmethod
            def scale(surf, size):
                return surf
        monkeypatch.setattr(pygame, "transform", _T, raising=False)
    if not hasattr(pygame.Rect, "size"):
        monkeypatch.setattr(
            pygame.Rect,
            "size",
            property(lambda self: (self.width, self.height)),
            raising=False,
        )
    if not hasattr(pygame.Rect, "left"):
        def _get_left(self):
            return self.x
        def _set_left(self, value):
            self.x = value
        monkeypatch.setattr(pygame.Rect, "left", property(_get_left, _set_left), raising=False)
    if not hasattr(pygame.Rect, "top"):
        def _get_top(self):
            return self.y
        def _set_top(self, value):
            self.y = value
        monkeypatch.setattr(pygame.Rect, "top", property(_get_top, _set_top), raising=False)
    if not hasattr(pygame.Rect, "centerx"):
        def _get_centerx(self):
            return self.center[0]
        def _set_centerx(self, value):
            self.x = value - self.width // 2
        monkeypatch.setattr(pygame.Rect, "centerx", property(_get_centerx, _set_centerx), raising=False)
    if not hasattr(pygame.Rect, "centery"):
        def _get_centery(self):
            return self.center[1]
        def _set_centery(self, value):
            self.y = value - self.height // 2
        monkeypatch.setattr(pygame.Rect, "centery", property(_get_centery, _set_centery), raising=False)


def test_world_overlay_uses_additive_blending(monkeypatch):
    _ensure_stub_functions(monkeypatch)
    BIOME_IMAGES["scarletia_echo_plain"] = ("", (10, 20, 30))
    world = WorldMap(map_data=["GG"])
    assets = SimpleNamespace(get=lambda key: None)
    hero = SimpleNamespace(x=0, y=0, ap=1)
    game = Game.__new__(Game)
    game.world = world
    game.assets = assets
    game.hero = hero
    game.active_actor = hero
    game.path = [(1, 0)]
    game.arrow_green = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))
    game.arrow_red = game.arrow_green
    game._draw_hero_sprite = lambda surf, pos: None
    game.enemy_heroes = []
    game.offset_x = 0
    game.offset_y = 0
    game.zoom = 1.0
    world_rect = pygame.Rect(0, 0, world.width * constants.TILE_SIZE, world.height * constants.TILE_SIZE)
    game.main_screen = SimpleNamespace(widgets={"1": world_rect})
    class DummyScreen(pygame.Surface):
        def set_clip(self, rect=None):
            return None

    game.screen = DummyScreen((world_rect.width, world_rect.height))
    game.ap_font = None

    calls = []
    orig_blit = pygame.Surface.blit

    def tracking_blit(self, src, dest, area=None, special_flags=0):
        calls.append(special_flags)
        return orig_blit(self, src, dest)

    monkeypatch.setattr(pygame.Surface, "blit", tracking_blit)

    game.draw_world(0)

    assert pygame.BLEND_RGBA_ADD in calls


def test_combat_overlay_uses_additive_blending(monkeypatch):
    _ensure_stub_functions(monkeypatch)
    highlight = pygame.Surface((constants.COMBAT_TILE_SIZE, constants.COMBAT_TILE_SIZE), pygame.SRCALPHA)
    highlight.fill((255, 0, 0, 255))
    assets = {"highlight": highlight}
    screen = pygame.Surface((800, 600))
    stats = UnitStats(
        name="a",
        max_hp=1,
        attack_min=1,
        attack_max=1,
        defence_melee=0,
        defence_ranged=0,
        defence_magic=0,
        speed=1,
        attack_range=1,
        initiative=1,
        sheet="",
        hero_frames=(0, 0),
        enemy_frames=(0, 0),
    )
    hero = Unit(stats, 1, "hero")
    enemy = Unit(stats, 1, "enemy")
    combat = Combat(screen, assets, [hero], [enemy])
    combat.selected_unit = combat.hero_units[0]
    combat.selected_action = "move"

    calls = []
    orig_blit = pygame.Surface.blit

    def tracking_blit(self, src, dest, area=None, special_flags=0):
        calls.append(special_flags)
        return orig_blit(self, src, dest)

    monkeypatch.setattr(pygame.Surface, "blit", tracking_blit)

    combat_render.draw(combat)

    assert pygame.BLEND_RGBA_ADD in calls


def test_combat_active_unit_overlay_uses_additive_blending(monkeypatch):
    _ensure_stub_functions(monkeypatch)
    active = pygame.Surface(
        (constants.COMBAT_TILE_SIZE, constants.COMBAT_TILE_SIZE), pygame.SRCALPHA
    )
    active.fill((255, 0, 0, 255))
    assets = {"active_unit": active}
    screen = pygame.Surface((800, 600))
    stats = UnitStats(
        name="a",
        max_hp=1,
        attack_min=1,
        attack_max=1,
        defence_melee=0,
        defence_ranged=0,
        defence_magic=0,
        speed=1,
        attack_range=1,
        initiative=1,
        sheet="",
        hero_frames=(0, 0),
        enemy_frames=(0, 0),
    )
    hero = Unit(stats, 1, "hero")
    enemy = Unit(stats, 1, "enemy")
    combat = Combat(screen, assets, [hero], [enemy])
    combat.turn_order = [combat.hero_units[0]]
    combat.current_index = 0

    calls = []
    orig_blit = pygame.Surface.blit

    def tracking_blit(self, src, dest, area=None, special_flags=0):
        if src is active:
            calls.append(special_flags)
        return orig_blit(self, src, dest, area, special_flags)

    monkeypatch.setattr(pygame.Surface, "blit", tracking_blit)

    combat_render.draw(combat)

    assert pygame.BLEND_RGBA_ADD in calls
