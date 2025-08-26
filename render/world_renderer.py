from __future__ import annotations

import logging
import math
import sys
import queue
import threading
from collections import OrderedDict
import pygame
from typing import Optional, Tuple, Set, List, Sequence


import constants
import settings
from core.world import WorldMap, ENEMY_UNIT_IMAGES, FLORA_CHUNK_TILES
from core.buildings import Town
from core.entities import UnitCarrier, Army
from render.autotile import AutoTileRenderer
from graphics.scale import scale_surface


logger = logging.getLogger(__name__)

# Number of tiles per cached biome chunk
BIOME_CHUNK_TILES = 32
BIOME_CACHE_SIZE = 64


class WorldRenderer:
    """Render a :class:`WorldMap` using :class:`AutoTileRenderer`.

    The renderer keeps track of a camera described by ``(x, y, zoom)`` where
    ``x`` and ``y`` are the top-left pixel coordinates of the view.  ``zoom`` is
    a multiplicative factor applied to the base tile size.  Camera movement is
    clamped so the view never leaves the bounds of the world.

    ``assets`` is an object providing a ``get(name)`` method returning
    ``pygame.Surface`` instances.  This mirrors the simple asset manager used in
    the rest of the project.
    """

    def __init__(
        self,
        assets: object,
        pan_speed: int = 20,
        player_colour: Tuple[int, int, int] = constants.BLUE,
        game: Optional[object] = None,
    ) -> None:
        self.assets = assets
        self.pan_speed = pan_speed
        self.player_colour = player_colour
        self.game = game
        self.cam_x = 0
        self.cam_y = 0
        self.zoom = 1.0
        self.selected: Optional[Tuple[int, int]] = None
        self._last_click_time = 0
        self._last_click_pos: Optional[Tuple[int, int]] = None
        self.double_click_ms = 400
        self.surface: Optional[pygame.Surface] = None
        self.world: Optional[WorldMap] = None
        # Cached biome surfaces per chunk (cx, cy) -> surface
        self._biome_chunks: "OrderedDict[Tuple[int, int], pygame.Surface]" = OrderedDict()
        self._biome_lock = threading.Lock()
        self._pending_chunks: Set[Tuple[int, int]] = set()
        self._prefetch_queue: "queue.Queue[Tuple[int, int, int]]" = queue.Queue()
        self._prefetch_set: Set[Tuple[int, int]] = set()
        self._prefetch_thread = threading.Thread(
            target=self._prefetch_worker, daemon=True
        )
        self._prefetch_thread.start()
        # Masks used for biome-to-biome transitions (edges & corners)
        self._transition_masks = {
            "edge": {d: assets.get(f"mask_{d}") for d in ("n", "e", "s", "w")},
            "corner": {c: assets.get(f"mask_{c}") for c in ("ne", "nw", "se", "sw")},
        }
        self._river_img = assets.get("terrain/river.png")

    # ------------------------------------------------------------------
    # Cached biome chunk helpers
    def _render_biome_chunk(self, cx: int, cy: int) -> None:
        """Ensure the biome chunk at ``(cx, cy)`` exists in the cache."""
        if not self.world:
            return
        with self._biome_lock:
            if (cx, cy) in self._biome_chunks or (cx, cy) in self._pending_chunks:
                return
            self._pending_chunks.add((cx, cy))
        world = self.world
        tile_size = constants.TILE_SIZE
        chunk = BIOME_CHUNK_TILES
        start_x = cx * chunk
        start_y = cy * chunk
        chunk_w = min(chunk, world.width - start_x)
        chunk_h = min(chunk, world.height - start_y)
        surf = pygame.Surface((chunk_w * tile_size, chunk_h * tile_size), pygame.SRCALPHA)
        assert world.renderer
        origin = (-start_x * tile_size, -start_y * tile_size)
        for y in range(start_y, start_y + chunk_h):
            for x in range(start_x, start_x + chunk_w):
                world.renderer.draw_cell(
                    surf,
                    origin,
                    x,
                    y,
                    world.biome_grid,
                    world.water_map,
                    constants.BIOME_PRIORITY,
                    self._transition_masks,
                )
                if world.biome_grid[y][x] == "river" and self._river_img:
                    px = (x - start_x) * tile_size
                    py = (y - start_y) * tile_size
                    surf.blit(self._river_img, (px, py))
        with self._biome_lock:
            self._pending_chunks.discard((cx, cy))
            self._biome_chunks[(cx, cy)] = surf
            self._biome_chunks.move_to_end((cx, cy))
            if len(self._biome_chunks) > BIOME_CACHE_SIZE:
                self._biome_chunks.popitem(last=False)

    def _generate_biome_chunks(self) -> None:
        """Reset biome chunk cache; chunks will be generated lazily."""
        if not self.world:
            return
        with self._biome_lock:
            self._biome_chunks.clear()
        self._pending_chunks.clear()
        self._prefetch_set.clear()
        while not self._prefetch_queue.empty():
            try:
                self._prefetch_queue.get_nowait()
                self._prefetch_queue.task_done()
            except queue.Empty:
                break

    def invalidate_biome(self, x: int, y: int) -> None:
        """Invalidate the cached chunk containing tile ``(x, y)``."""
        if not self.world:
            return
        cx = x // BIOME_CHUNK_TILES
        cy = y // BIOME_CHUNK_TILES
        with self._biome_lock:
            self._biome_chunks.pop((cx, cy), None)
            self._prefetch_set.discard((cx, cy))
            self._pending_chunks.discard((cx, cy))

    def _prefetch_worker(self) -> None:
        while True:
            cx, cy, world_id = self._prefetch_queue.get()
            if world_id != id(self.world):
                with self._biome_lock:
                    self._prefetch_set.discard((cx, cy))
                self._prefetch_queue.task_done()
                continue
            try:
                self._render_biome_chunk(cx, cy)
            finally:
                with self._biome_lock:
                    self._prefetch_set.discard((cx, cy))
                self._prefetch_queue.task_done()

    def _queue_prefetch(self, cx: int, cy: int) -> None:
        if not self.world:
            return
        with self._biome_lock:
            if (
                (cx, cy) in self._biome_chunks
                or (cx, cy) in self._prefetch_set
                or (cx, cy) in self._pending_chunks
            ):
                return
            self._prefetch_set.add((cx, cy))
        self._prefetch_queue.put((cx, cy, id(self.world)))

    def _prefetch_chunks(
        self, start_cx: int, end_cx: int, start_cy: int, end_cy: int
    ) -> None:
        if not self.world:
            return
        chunk = BIOME_CHUNK_TILES
        world = self.world
        chunks_x = math.ceil(world.width / chunk)
        chunks_y = math.ceil(world.height / chunk)
        radius = 1
        for cy in range(max(0, start_cy - radius), min(chunks_y, end_cy + radius)):
            for cx in range(max(0, start_cx - radius), min(chunks_x, end_cx + radius)):
                if start_cx <= cx < end_cx and start_cy <= cy < end_cy:
                    continue
                self._queue_prefetch(cx, cy)

    # ------------------------------------------------------------------
    # Camera helpers
    def _clamp_cam(self) -> None:
        if not self.surface or not self.world:
            return
        w = self.world.width * constants.TILE_SIZE
        h = self.world.height * constants.TILE_SIZE
        max_x = max(0, w - self.surface.get_width() / self.zoom)
        max_y = max(0, h - self.surface.get_height() / self.zoom)
        self.cam_x = max(0, min(self.cam_x, max_x))
        self.cam_y = max(0, min(self.cam_y, max_y))

    def center_on(self, tile: Tuple[int, int]) -> None:
        if not self.surface:
            return
        tx, ty = tile
        px = tx * constants.TILE_SIZE + constants.TILE_SIZE // 2
        py = ty * constants.TILE_SIZE + constants.TILE_SIZE // 2
        self.cam_x = px - self.surface.get_width() / (2 * self.zoom)
        self.cam_y = py - self.surface.get_height() / (2 * self.zoom)
        self._clamp_cam()

    # ------------------------------------------------------------------
    # Event handling
    def handle_event(self, evt: pygame.event.Event) -> None:
        """Update camera and selection from a Pygame event."""
        if not self.world or not self.surface:
            return
        pg = sys.modules.get("pygame", pygame)
        if evt.type == getattr(pg, "KEYDOWN", None):
            km = settings.KEYMAP

            def _resolve(action: str) -> list:
                return [getattr(pg, n, None) for n in km.get(action, [])]

            if evt.key in _resolve("pan_left"):
                self.cam_x -= self.pan_speed
            elif evt.key in _resolve("pan_right"):
                self.cam_x += self.pan_speed
            elif evt.key in _resolve("pan_up"):
                self.cam_y -= self.pan_speed
            elif evt.key in _resolve("pan_down"):
                self.cam_y += self.pan_speed
            elif evt.key in _resolve("zoom_in"):
                self.zoom *= 1.1
            elif evt.key in _resolve("zoom_out"):
                self.zoom /= 1.1
            self._clamp_cam()
        elif evt.type == getattr(pg, "MOUSEBUTTONDOWN", None) and evt.button == 1:
            x, y = evt.pos
            wx = int((x / self.zoom + self.cam_x) // constants.TILE_SIZE)
            wy = int((y / self.zoom + self.cam_y) // constants.TILE_SIZE)
            if self.world.in_bounds(wx, wy):
                now = pg.time.get_ticks()
                if (
                    self._last_click_pos == (wx, wy)
                    and now - self._last_click_time <= self.double_click_ms
                ):
                    tile = self.world.grid[wy][wx]
                    if (
                        self.game
                        and getattr(tile, "boat", None)
                        and hasattr(self.game, "embark")
                    ):
                        hero = getattr(self.game, "hero", None)
                        if hero and abs(hero.x - wx) + abs(hero.y - wy) == 1:
                            self.game.embark(hero, tile.boat)
                    elif (
                        self.game
                        and isinstance(getattr(tile, "building", None), Town)
                        and tile.building.owner == 0
                        and hasattr(self.game, "open_town")
                    ):
                        self.game.open_town(tile.building, town_pos=(wx, wy))
                    else:
                        self.center_on((wx, wy))
                else:
                    self.selected = (wx, wy)
                    self._last_click_pos = (wx, wy)
                    self._last_click_time = now

    # ------------------------------------------------------------------
    # Drawing helpers
    def _draw_layers(
        self,
        dest: pygame.Surface,
        heroes: Sequence[UnitCarrier],
        armies: Sequence[UnitCarrier],
        selected: Optional[UnitCarrier],
    ) -> None:
        assert self.world
        tile_size = constants.TILE_SIZE
        world = self.world

        view_w = dest.get_width()
        view_h = dest.get_height()
        start_x = max(0, int(self.cam_x // tile_size))
        start_y = max(0, int(self.cam_y // tile_size))
        end_x = min(world.width, int(math.ceil((self.cam_x + view_w) / tile_size)))
        end_y = min(world.height, int(math.ceil((self.cam_y + view_h) / tile_size)))
        offset_x = int(start_x * tile_size - self.cam_x)
        offset_y = int(start_y * tile_size - self.cam_y)

        dest_w, dest_h = dest.get_width(), dest.get_height()
        layers = {
            i: pygame.Surface((dest_w, dest_h), pygame.SRCALPHA)
            for i in range(constants.LAYER_UI + 1)
        }
        vis_grid = world.visible.get(0)
        exp_grid = world.explored.get(0)
        use_fog = bool(vis_grid and exp_grid)
        fog_surface = pygame.Surface((dest_w, dest_h), pygame.SRCALPHA) if use_fog else None
        tall_draw: List[Tuple[int, ...]] = []

        def grid_to_screen(x: int, y: int) -> Tuple[int, int]:
            """Return bottom-centre pixel position for tile (x, y) in viewport."""
            sx = (x - start_x) * tile_size + tile_size // 2 + offset_x
            sy = (y - start_y) * tile_size + tile_size + offset_y
            return sx, sy

        def scale_if_needed(surf: pygame.Surface) -> pygame.Surface:
            """Scale ``surf`` down to fit inside a tile if necessary."""
            w, h = surf.get_size()
            if w > tile_size or h > tile_size:
                scale = min(tile_size / w, tile_size / h)
                surf = scale_surface(
                    surf, (int(w * scale), int(h * scale)), smooth=True
                )
            return surf

        # Biome layer via cached chunks
        chunk = BIOME_CHUNK_TILES
        chunk_start_x = start_x // chunk
        chunk_end_x = math.ceil(end_x / chunk)
        chunk_start_y = start_y // chunk
        chunk_end_y = math.ceil(end_y / chunk)
        for cy in range(chunk_start_y, chunk_end_y):
            for cx in range(chunk_start_x, chunk_end_x):
                with self._biome_lock:
                    surf = self._biome_chunks.get((cx, cy))
                    if surf:
                        self._biome_chunks.move_to_end((cx, cy))
                if surf is None:
                    self._render_biome_chunk(cx, cy)
                    with self._biome_lock:
                        surf = self._biome_chunks.get((cx, cy))
                if surf is None:
                    continue
                px = cx * chunk * tile_size - self.cam_x
                py = cy * chunk * tile_size - self.cam_y
                layers[constants.LAYER_BIOME].blit(surf, (int(px), int(py)))
        self._prefetch_chunks(chunk_start_x, chunk_end_x, chunk_start_y, chunk_end_y)

        # Roads layer
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile = world.grid[y][x]
                key = getattr(tile, "road", "")
                if key:
                    img = self.assets.get(key)
                    if img:
                        layers[constants.LAYER_DECALS].blit(
                            img,
                            (
                                (x - start_x) * tile_size + offset_x,
                                (y - start_y) * tile_size + offset_y,
                            ),
                        )

        # Resource deposits layer
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile = world.grid[y][x]
                if tile.resource:
                    img = self.assets.get(tile.resource)
                    if img:
                        img = scale_if_needed(img)
                        layers[constants.LAYER_RESOURCES].blit(
                            img,
                            (
                                (x - start_x) * tile_size + offset_x,
                                (y - start_y) * tile_size + offset_y,
                            ),
                        )

        # Flora props
        if getattr(world, "flora_loader", None) and world.flora_props:
            view_rect = pygame.Rect(self.cam_x, self.cam_y, view_w, view_h)
            active_collectibles = set(getattr(world, "collectibles", {}).keys())
            chunk_px = FLORA_CHUNK_TILES * constants.TILE_SIZE
            cx0 = view_rect.x // chunk_px
            cy0 = view_rect.y // chunk_px
            cx1 = (view_rect.x + view_rect.width - 1) // chunk_px
            cy1 = (view_rect.y + view_rect.height - 1) // chunk_px
            seen: Set[int] = set()
            visible_props: List[object] = []
            for cy in range(cy0, cy1 + 1):
                for cx in range(cx0, cx1 + 1):
                    for p in world.flora_prop_chunks.get((cx, cy), []):
                        pid = id(p)
                        if pid in seen:
                            continue
                        seen.add(pid)
                        if p.rect_world.colliderect(view_rect) and (
                            world.flora_loader.assets[p.asset_id].type != "collectible"
                            or p.tile_xy in active_collectibles
                        ):
                            visible_props.append(p)
            loader = world.flora_loader
            tall_props: List[object] = []
            other_props: List[object] = []
            for p in visible_props:
                a = loader.assets[p.asset_id]
                if a.type == "tall":
                    tall_props.append(p)
                else:
                    other_props.append(p)
            if other_props:
                loader.draw_props(layers, other_props, grid_to_screen)
            for p in tall_props:
                a = loader.assets[p.asset_id]
                img, (ax, ay) = loader.get_surface(p.asset_id, p.variant)
                foot_x, foot_y = p.tile_xy
                fw, fh = p.footprint
                anchor_tile = (foot_x + fw // 2, foot_y + fh - 1)
                sx, sy = grid_to_screen(anchor_tile[0], anchor_tile[1])
                px = int(sx - ax)
                py = int(sy - ay)
                tall_draw.append((sy, "prop", img, (px, py)))

        # Decor layer: obstacles, treasures, buildings
        drawn_buildings: Set[object] = set()
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile = world.grid[y][x]
                px = (x - start_x) * tile_size + offset_x
                py = (y - start_y) * tile_size + offset_y
                if tile.obstacle and tile.building is None:
                    img = self.assets.get(constants.IMG_OBSTACLE)
                    if img:
                        if img.get_size() != (tile_size, tile_size):
                            img = scale_surface(img, tile_size)
                        layers[constants.LAYER_OBJECTS].blit(img, (px, py))
                elif tile.treasure is not None:
                    img = self.assets.get(constants.IMG_TREASURE)
                    if img:
                        if img.get_size() != (tile_size, tile_size):
                            img = scale_surface(img, tile_size)
                        layers[constants.LAYER_OBJECTS].blit(img, (px, py))
                elif tile.building and tile.building not in drawn_buildings:
                    b = tile.building
                    drawn_buildings.add(b)
                    img = self.assets.get(b.image)
                    if img:
                        xs = [p[0] for p in b.footprint]
                        ys = [p[1] for p in b.footprint]
                        width = max(xs) + 1
                        height = max(ys) + 1
                        sx = (
                            int((b.origin[0] + width / 2) * tile_size)
                            + offset_x
                            - start_x * tile_size
                        )
                        sy = (
                            int((b.origin[1] + height) * tile_size)
                            + offset_y
                            - start_y * tile_size
                        )
                        ax, ay = b.anchor
                        rect = img.get_rect(topleft=(sx - ax, sy - ay))
                        tall_draw.append((sy, "building", b, img, rect, sx, sy, ax, ay))
        # Draw tall props and buildings sorted by baseline
        tall_draw.sort(key=lambda t: t[0])
        for entry in tall_draw:
            kind = entry[1]
            if kind == "prop":
                _, _, img, pos = entry
                layers[constants.LAYER_FLORA].blit(img, pos)
            else:
                _, _, b, img, rect, sx, sy, ax, ay = entry
                layers[constants.LAYER_OBJECTS].blit(img, rect.topleft)
                if settings.DEBUG_BUILDINGS:
                    pygame.draw.circle(
                        layers[constants.LAYER_UI],
                        constants.RED,
                        (sx, sy),
                        4,
                    )
                    pygame.draw.circle(
                        layers[constants.LAYER_UI],
                        constants.GREEN,
                        rect.topleft,
                        4,
                    )
                    pygame.draw.rect(
                        layers[constants.LAYER_UI],
                        constants.MAGENTA,
                        rect,
                        1,
                    )
                    if self.surface:
                        screen_rect = pygame.Rect(
                            self.cam_x,
                            self.cam_y,
                            self.surface.get_width() / self.zoom,
                            self.surface.get_height() / self.zoom,
                        )
                        if not screen_rect.colliderect(rect):
                            logger.debug("Building rect %s off screen", rect)
                if b.owner is not None:
                    flag = self.assets.get("hero_flag")
                    if flag:
                        colour = self.player_colour if b.owner == 0 else constants.RED
                        flag_surf = flag.copy()
                        flag_surf.fill(
                            (*colour, 255), special_flags=pygame.BLEND_RGBA_MULT
                        )
                        fx = sx - flag_surf.get_width() // 2
                        fy = sy - ay - flag_surf.get_height() // 2
                        layers[constants.LAYER_OBJECTS].blit(flag_surf, (fx, fy))
                for dx, dy in b.footprint:
                    tx = b.origin[0] + dx
                    ty = b.origin[1] + dy
                    if start_x <= tx < end_x and start_y <= ty < end_y:
                        if b.owner == 0:
                            colour = self.player_colour
                        elif b.owner is not None:
                            colour = constants.RED
                        else:
                            colour = constants.GREY
                        pygame.draw.rect(
                            layers[constants.LAYER_OBJECTS],
                            colour,
                            pygame.Rect(
                                (tx - start_x) * tile_size + offset_x,
                                (ty - start_y) * tile_size + offset_y,
                                tile_size,
                                tile_size,
                            ),
                            1,
                        )

        # Units layer: enemy stacks, heroes and armies
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile = world.grid[y][x]
                if getattr(tile, "boat", None):
                    img = self.assets.get(tile.boat.id)
                    if not img and getattr(self.game, "boat_defs", None):
                        bdef = self.game.boat_defs.get(tile.boat.id)
                        if bdef:
                            img = self.assets.get(bdef.path)
                    if img:
                        if img.get_size() != (tile_size, tile_size):
                            img = scale_surface(img, tile_size)
                        layers[constants.LAYER_UNITS].blit(
                            img,
                            (
                                (x - start_x) * tile_size + offset_x,
                                (y - start_y) * tile_size + offset_y,
                            ),
                        )
                if tile.enemy_units:
                    strongest = max(tile.enemy_units, key=lambda u: u.stats.max_hp)
                    img_name = ENEMY_UNIT_IMAGES.get(strongest.stats.name)
                    img = self.assets.get(img_name)
                    if img:
                        layers[constants.LAYER_UNITS].blit(
                            img,
                            (
                                (x - start_x) * tile_size + offset_x,
                                (y - start_y) * tile_size + offset_y,
                            ),
                        )
        def draw_actor(actor: UnitCarrier) -> None:
            ax, ay = actor.x, actor.y
            if not (start_x <= ax < end_x and start_y <= ay < end_y):
                return
            hidden = use_fog and not vis_grid[ay][ax]
            px = (ax - start_x) * tile_size + offset_x
            py = (ay - start_y) * tile_size + offset_y
            portrait = getattr(actor, "portrait", None)
            units = getattr(actor, "units", [])
            surf: Optional[pygame.Surface] = None
            is_hero = not isinstance(actor, Army)

            # Draw boat beneath heroes that possess one
            if is_hero and getattr(actor, "naval_unit", None):
                boat = self.assets.get(actor.naval_unit)
                if not boat and getattr(self.game, "boat_defs", None):
                    bdef = self.game.boat_defs.get(actor.naval_unit)
                    if bdef:
                        boat = self.assets.get(bdef.path)
                if boat:
                    if boat.get_size() != (tile_size, tile_size):
                        boat = scale_surface(boat, tile_size)
                    layers[constants.LAYER_UNITS].blit(boat, (px, py))

            if hidden:
                player_hero = getattr(self.game, "hero", None)
                if (
                    is_hero
                    and actor is player_hero
                    and isinstance(portrait, pygame.Surface)
                ):
                    surf = portrait
                elif units:
                    strongest = max(
                        units,
                        key=lambda u: u.count * (u.stats.attack_min + u.stats.attack_max),
                    )
                    unit_id = getattr(strongest.stats, "name", "").lower().replace(" ", "_")
                    img = self.assets.get(unit_id)
                    if isinstance(img, pygame.Surface):
                        surf = img
            else:
                if is_hero and isinstance(portrait, pygame.Surface):
                    surf = portrait
                elif units:
                    strongest = max(
                        units,
                        key=lambda u: u.count * (u.stats.attack_min + u.stats.attack_max),
                    )
                    unit_id = getattr(strongest.stats, "name", "").lower().replace(" ", "_")
                    img = self.assets.get(unit_id)
                    if isinstance(img, pygame.Surface):
                        surf = img

            if isinstance(surf, pygame.Surface):
                try:
                    if surf.get_size() != (tile_size, tile_size):
                        surf = pygame.transform.smoothscale(
                            surf, (tile_size, tile_size)
                        )
                except AttributeError:
                    # Some surfaces used during testing may be simple stubs
                    # lacking ``get_size``; in that case draw them as-is.
                    pass
                layers[constants.LAYER_UNITS].blit(surf, (px, py))
                return

            img = self.assets.get("default_hero")
            if isinstance(img, dict):
                icon = img.get("icon") if isinstance(img.get("icon"), dict) else None
                if icon and isinstance(icon.get("surface"), pygame.Surface):
                    surf = icon["surface"]
                    ox, oy = icon.get("anchor", (0, 0))
                    layers[constants.LAYER_UNITS].blit(surf, (px - ox, py - oy))
                    return

            generic = self.assets.get("enemy_army")
            if isinstance(generic, pygame.Surface):
                layers[constants.LAYER_UNITS].blit(generic, (px, py))
                return

        for hero in heroes:
            draw_actor(hero)
        for army in armies:
            draw_actor(army)

        # Overlay layer: selection rectangle
        sel = (selected.x, selected.y) if selected else self.selected
        if sel:
            sx_tile, sy_tile = sel
            if start_x <= sx_tile < end_x and start_y <= sy_tile < end_y:
                sx = (sx_tile - start_x) * tile_size + offset_x
                sy = (sy_tile - start_y) * tile_size + offset_y
                pygame.draw.rect(
                    layers[constants.LAYER_UI],
                    constants.YELLOW,
                    pygame.Rect(sx, sy, tile_size, tile_size),
                    2,
                )
        if use_fog and fog_surface:
            for y in range(start_y, end_y):
                for x in range(start_x, end_x):
                    px = (x - start_x) * tile_size + offset_x
                    py = (y - start_y) * tile_size + offset_y
                    rect = pygame.Rect(px, py, tile_size, tile_size)
                    if not exp_grid[y][x]:
                        fog_surface.fill((0, 0, 0, 255), rect)
                    elif not vis_grid[y][x]:
                        fog_surface.fill((0, 0, 0, 120), rect)

        overlay = layers[constants.LAYER_OVERLAY]
        for i in range(constants.LAYER_UI + 1):
            if i == constants.LAYER_OVERLAY:
                continue
            dest.blit(layers[i], (0, 0))
        if use_fog and fog_surface:
            dest.blit(fog_surface, (0, 0))
        return overlay

    # ------------------------------------------------------------------
    def draw(
        self,
        surface: pygame.Surface,
        world: WorldMap,
        cam: Optional[Tuple[float, float, float]] = None,
        heroes: Optional[Sequence[UnitCarrier]] = None,
        armies: Optional[Sequence[UnitCarrier]] = None,
        selected: Optional[UnitCarrier] = None,
    ) -> Tuple[float, float, float]:
        """Draw ``world`` onto ``surface`` applying camera transform.

        ``cam`` is a tuple ``(x, y, zoom)`` describing the desired camera state.
        The effective camera after clamping is returned.
        """

        self.surface = surface
        if world is not self.world:
            self.world = world
            self._generate_biome_chunks()
        else:
            self.world = world
        if cam is not None:
            self.cam_x, self.cam_y, self.zoom = cam
        self._clamp_cam()

        view_w = int(math.ceil(surface.get_width() / self.zoom))
        view_h = int(math.ceil(surface.get_height() / self.zoom))
        map_surf = pygame.Surface((view_w, view_h), pygame.SRCALPHA)
        overlay = self._draw_layers(
            map_surf,
            heroes or [],
            armies if armies is not None else getattr(world, "player_armies", []),
            selected,
        )

        if self.zoom != 1.0:
            map_surf = pygame.transform.smoothscale(map_surf, surface.get_size())
            overlay = pygame.transform.smoothscale(overlay, surface.get_size())
        surface.blit(map_surf, (0, 0))
        blend = getattr(pygame, "BLEND_RGBA_ADD", 0)
        try:
            surface.blit(overlay, (0, 0), special_flags=blend)
        except TypeError:
            surface.blit(overlay, (0, 0))
        return (self.cam_x, self.cam_y, self.zoom)


__all__ = ["WorldRenderer"]
