import sys
import types
import copy



def test_preview_returns_losses(monkeypatch):
    from core.entities import Unit, RECRUITABLE_UNITS
    SWORDSMAN_STATS = RECRUITABLE_UNITS["swordsman"]
    import core.auto_resolve as ar

    def fake_sim(hero_units, enemy_units):
        heroes = [copy.deepcopy(u) for u in hero_units]
        enemies = [copy.deepcopy(u) for u in enemy_units]
        for u in heroes:
            u.count -= 1
        for u in enemies:
            u.count -= 2
        return heroes, enemies, True, 10

    monkeypatch.setattr(ar, "_simulate", fake_sim)
    h_loss, e_loss, xp = ar.preview(
        [Unit(SWORDSMAN_STATS, 5, "h")], [Unit(SWORDSMAN_STATS, 5, "e")], iterations=1
    )
    assert h_loss == 1
    assert e_loss == 2
    assert xp == 10


def test_prompt_displays_losses(monkeypatch, pygame_stub):
    rendered = []

    class Rect:
        def __init__(self, x, y, w, h):
            self.x, self.y, self.width, self.height = x, y, w, h

        def _get_center(self):
            return (self.x + self.width // 2, self.y + self.height // 2)

        def _set_center(self, pos):
            self.x = pos[0] - self.width // 2
            self.y = pos[1] - self.height // 2

        center = property(_get_center, _set_center)

        def _get_centerx(self):
            return self._get_center()[0]

        def _set_centerx(self, val):
            self._set_center((val, self.centery))

        centerx = property(_get_centerx, _set_centerx)

        def _get_centery(self):
            return self._get_center()[1]

        def _set_centery(self, val):
            self._set_center((self.centerx, val))

        centery = property(_get_centery, _set_centery)

        @property
        def bottom(self):
            return self.y + self.height

        def get_rect(self, **kw):
            r = Rect(self.x, self.y, self.width, self.height)
            if "center" in kw:
                r.center = kw["center"]
            return r

        def collidepoint(self, pos):
            return True

    class DummySurface:
        def __init__(self, size=(10, 10), flags=0):
            self._w, self._h = size

        def convert_alpha(self):
            return self

        def get_width(self):
            return self._w

        def get_height(self):
            return self._h

        def get_size(self):
            return (self._w, self._h)

        def get_rect(self, **kw):
            rect = Rect(0, 0, self._w, self._h)
            if "center" in kw:
                rect.center = kw["center"]
            return rect

        def blit(self, *a, **k):
            pass

        def fill(self, *a, **k):
            pass

        def copy(self):
            return self

    class Font:
        def render(self, text, aa, color):
            rendered.append(text)
            return DummySurface()

        def get_height(self):
            return 10

        def get_linesize(self):
            return 12

    pg = pygame_stub(
        Rect=Rect,
        Surface=lambda size, flags=0: DummySurface(size, flags),
        image=types.SimpleNamespace(load=lambda p: DummySurface()),
        transform=types.SimpleNamespace(
            scale=lambda surf, size: surf,
            smoothscale=lambda surf, size: surf,
            flip=lambda *a, **k: DummySurface(),
        ),
        font=types.SimpleNamespace(SysFont=lambda *a, **k: Font(), Font=lambda *a, **k: Font()),
    )
    monkeypatch.setitem(sys.modules, "pygame", pg)
    monkeypatch.setitem(sys.modules, "pygame.draw", pg.draw)
    monkeypatch.setitem(sys.modules, "pygame.image", pg.image)
    monkeypatch.setitem(sys.modules, "pygame.transform", pg.transform)
    monkeypatch.setitem(sys.modules, "pygame.font", pg.font)

    import theme
    import core.game as game_mod
    monkeypatch.setattr(theme, "pygame", pg)
    monkeypatch.setattr(game_mod, "pygame", pg)
    from core.entities import Unit, RECRUITABLE_UNITS, Hero
    SWORDSMAN_STATS = RECRUITABLE_UNITS["swordsman"]
    Game = game_mod.Game
    import core.auto_resolve as ar
    from ui import dialogs

    monkeypatch.setattr(ar, "preview", lambda *a, **k: (5, 7, 10))
    monkeypatch.setattr(
        dialogs,
        "run_dialog",
        lambda screen, clock, draw, buttons, escape, on_escape=None: (draw(), escape)[1],
    )

    game = Game.__new__(Game)
    game.screen = pg.Surface((800, 600))
    game.clock = pg.time.Clock()
    game.draw_world = lambda *a, **k: None
    game.anim_frame = 0
    game.hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "h")])
    game.quit_to_menu = False

    enemy_units = [Unit(SWORDSMAN_STATS, 1, "e")]
    game.prompt_combat_choice(enemy_units)

    assert any("5" in t for t in rendered)
    assert any("7" in t for t in rendered)
