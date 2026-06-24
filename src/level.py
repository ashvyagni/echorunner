"""
level.py
========
Loads a level from JSON, builds collision rectangles and renders the tilemap
with per-tile edge detail, shade variation, animated hazard glow, and level-
specific color themes.

Level JSON schema
-----------------
{
  "id":   "level_01",
  "name": "First Steps",
  "spawn":[col, row],          # player spawn in tile coordinates
  "exit": [col, row],          # exit tile (must also be tile 2 in the map)
  "tilemap": [[int, ...], ...],# rows of tiles, 0=air,1=platform,2=exit,3=hazard
  "moving_platforms": [        # optional, for "Rising Risk" style levels
      {"x":col,"y":row,"w":tiles,"axis":"x"|"y","range":pixels,"speed":px/s,"phase":0.0}
  ]
}

Tile ids live in constants.py.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import pygame

from . import constants as C


# ---------------------------------------------------------------------------
# Pre-compute a deterministic shade variation per tile position.
# Uses a simple hash so the pattern is consistent across frames.
# ---------------------------------------------------------------------------
def _tile_shade(col: int, row: int) -> int:
    """Return -10..+10 brightness offset for a tile at (col, row)."""
    h = (col * 374761 + row * 668265) & 0xFFFF
    return (h % 21) - 10  # -10 to +10


def _clamp_color(c: tuple) -> tuple:
    return tuple(max(0, min(255, int(v))) for v in c)


@dataclass
class MovingPlatform:
    """A platform that oscillates along one axis. Carries the player when stood on."""

    rect: pygame.Rect
    axis: str            # "x" or "y"
    range_px: float      # total travel distance (half each direction from origin)
    speed: float         # pixels per second
    phase: float = 0.0   # starting offset in seconds (stagger multiple platforms)
    origin_x: float = 0.0
    origin_y: float = 0.0

    def update(self, dt: float, t: float) -> tuple[float, float]:
        """Advance position. Returns (dx, dy) delta since last update."""
        prev = (self.rect.x, self.rect.y)
        # Triangle-wave oscillation gives smooth linear platforms (not sinusoidal).
        period = (2.0 * self.range_px / self.speed) if self.speed > 0 else 1.0
        progress = ((t + self.phase) / period) % 1.0          # 0..1
        tri = 4.0 * abs(progress - 0.5) - 1.0                 # -1..1 triangle
        offset = (tri * 0.5 + 0.5) * self.range_px - self.range_px / 2.0
        if self.axis == "x":
            self.rect.x = int(self.origin_x + offset)
        else:
            self.rect.y = int(self.origin_y + offset)
        return self.rect.x - prev[0], self.rect.y - prev[1]


def get_zero_rect() -> pygame.Rect:
    """Factory for the default empty exit rect (used by the Level dataclass)."""
    return pygame.Rect(0, 0, 0, 0)


@dataclass
class Level:
    """A loaded, drawable level with collision data."""

    id: str
    name: str
    tilemap: List[List[int]]
    spawn_tile: tuple[int, int]
    exit_tile: tuple[int, int]
    moving_platforms: List[MovingPlatform] = field(default_factory=list)
    width_px: int = 0
    height_px: int = 0
    theme_index: int = 0  # which LEVEL_THEMES entry to use

    # --- derived (filled by load) ---
    _platform_rects: List[pygame.Rect] = field(default_factory=list)
    _exit_rect: pygame.Rect = field(default_factory=get_zero_rect)
    _hazard_rects: List[pygame.Rect] = field(default_factory=list)
    _exit_world_pos: tuple[int, int] = (0, 0)

    # ------------------------------------------------------------------ build
    def _index(self) -> None:
        """Compute collision rects and pixel dimensions from the tilemap."""
        rows = len(self.tilemap)
        cols = max((len(r) for r in self.tilemap), default=0)
        self.width_px = cols * C.TILE_SIZE
        self.height_px = rows * C.TILE_SIZE

        self._platform_rects.clear()
        self._hazard_rects.clear()
        for r, row in enumerate(self.tilemap):
            for c, tile in enumerate(row):
                x, y = c * C.TILE_SIZE, r * C.TILE_SIZE
                if tile == C.TILE_PLATFORM:
                    self._platform_rects.append(pygame.Rect(x, y, C.TILE_SIZE, C.TILE_SIZE))
                elif tile == C.TILE_EXIT:
                    self._exit_rect = pygame.Rect(x, y, C.TILE_SIZE, C.TILE_SIZE)
                    self._exit_world_pos = (x, y)
                elif tile == C.TILE_HAZARD:
                    self._hazard_rects.append(pygame.Rect(x, y, C.TILE_SIZE, C.TILE_SIZE))

    # ----------------------------------------------------------------- access
    def platforms(self) -> List[pygame.Rect]:
        """All solid platforms (static + current positions of moving ones)."""
        return self._platform_rects + [mp.rect for mp in self.moving_platforms]

    def hazards(self) -> List[pygame.Rect]:
        return self._hazard_rects

    def exit_rect(self) -> pygame.Rect:
        return self._exit_rect

    def spawn_pos(self) -> tuple[int, int]:
        """Spawn in pixels, centered on the tile, player-sized."""
        sx = self.spawn_tile[0] * C.TILE_SIZE + (C.TILE_SIZE - C.PLAYER_SIZE) // 2
        sy = self.spawn_tile[1] * C.TILE_SIZE + (C.TILE_SIZE - C.PLAYER_SIZE)
        return sx, sy

    def update(self, dt: float, t: float) -> None:
        """Animate moving platforms."""
        for mp in self.moving_platforms:
            mp.update(dt, t)

    # ------------------------------------------------------------------ draw
    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float,
             *, t: float = 0.0) -> None:
        """Render visible tiles with theme colors, edge detail, and animations.

        Parameters
        ----------
        t : float
            Level elapsed time in seconds (for animated hazard glow, exit pulse).
        """
        ox, oy = int(cam_x), int(cam_y)

        # Resolve level theme (clamp to available entries).
        theme = C.LEVEL_THEMES[min(self.theme_index, len(C.LEVEL_THEMES) - 1)]
        plat_col = theme[0]
        plat_top_col = theme[1]

        # Only iterate the visible column range to stay fast on big maps.
        start_col = max(0, ox // C.TILE_SIZE)
        end_col = C.SCREEN_W // C.TILE_SIZE + start_col + 2
        for r, row in enumerate(self.tilemap):
            for c in range(start_col, min(end_col, len(row))):
                tile = row[c]
                if tile == C.TILE_EMPTY:
                    continue
                x = c * C.TILE_SIZE - ox
                y = r * C.TILE_SIZE - oy

                # Check if this tile is screen-visible (quick cull).
                if x + C.TILE_SIZE < 0 or x > C.SCREEN_W:
                    continue
                if y + C.TILE_SIZE < 0 or y > C.SCREEN_H:
                    continue

                if tile == C.TILE_PLATFORM:
                    # Per-tile shade variation
                    shade = _tile_shade(c, r)
                    col = _clamp_color((plat_col[0] + shade,
                                        plat_col[1] + shade,
                                        plat_col[2] + shade))
                    top_col = _clamp_color((plat_top_col[0] + shade,
                                            plat_top_col[1] + shade,
                                            plat_top_col[2] + shade))
                    surface.fill(col, (x, y, C.TILE_SIZE, C.TILE_SIZE))
                    surface.fill(top_col, (x, y, C.TILE_SIZE, 4))
                    # Edge detail: 1px darker border on exposed edges
                    self._draw_tile_edges(surface, row, c, r, x, y,
                                         (max(0, plat_col[0] - 20),
                                          max(0, plat_col[1] - 20),
                                          max(0, plat_col[2] - 20)))

                elif tile == C.TILE_EXIT:
                    _draw_exit(surface, x, y, t, theme)

                elif tile == C.TILE_HAZARD:
                    _draw_hazard(surface, x, y, t)

        # Moving platforms draw on top, distinct color.
        for mp in self.moving_platforms:
            r = mp.rect.move(-ox, -oy)
            # Only draw if on-screen.
            if r.right < 0 or r.left > C.SCREEN_W:
                continue
            if r.bottom < 0 or r.top > C.SCREEN_H:
                continue
            surface.fill(C.COLOR_MOVING_PLATFORM, r)
            surface.fill(C.COLOR_MOVING_PLATFORM_TOP, (r.x, r.y, r.w, 4))
            # 1px edge detail on moving platforms too
            edge_col = (max(0, C.COLOR_MOVING_PLATFORM[0] - 20),
                        max(0, C.COLOR_MOVING_PLATFORM[1] - 20),
                        max(0, C.COLOR_MOVING_PLATFORM[2] - 20))
            pygame.draw.rect(surface, edge_col, r, 1)

    def _draw_tile_edges(self, surface: pygame.Surface,
                         row: List[int], c: int, r: int,
                         x: int, y: int, edge_color: tuple) -> None:
        """Draw 1px darker border on edges where this tile meets air."""
        rows = self.tilemap
        # top edge
        if r == 0 or (r > 0 and rows[r - 1][c] == C.TILE_EMPTY):
            pygame.draw.line(surface, edge_color, (x, y), (x + C.TILE_SIZE - 1, y))
        # bottom edge
        if r + 1 >= len(rows) or rows[r + 1][c] == C.TILE_EMPTY:
            pygame.draw.line(surface, edge_color,
                             (x, y + C.TILE_SIZE - 1), (x + C.TILE_SIZE - 1, y + C.TILE_SIZE - 1))
        # left edge
        if c == 0 or row[c - 1] == C.TILE_EMPTY:
            pygame.draw.line(surface, edge_color, (x, y), (x, y + C.TILE_SIZE - 1))
        # right edge
        if c + 1 >= len(row) or row[c + 1] == C.TILE_EMPTY:
            pygame.draw.line(surface, edge_color,
                             (x + C.TILE_SIZE - 1, y), (x + C.TILE_SIZE - 1, y + C.TILE_SIZE - 1))


def _draw_exit(surface: pygame.Surface, x: int, y: int, t: float,
               theme: tuple) -> None:
    """Glowing teal portal — pulses over time, uses theme accent."""
    pulse = 0.5 + 0.5 * math.sin(t * 4.0)
    # Use theme accent for the exit glow (4th element of theme tuple)
    accent = theme[3]
    glow = tuple(min(255, int(v + 60 * pulse)) for v in accent)
    surface.fill(glow, (x, y, C.TILE_SIZE, C.TILE_SIZE))
    surface.fill(C.COLOR_PLATFORM, (x + 6, y + 6, C.TILE_SIZE - 12, C.TILE_SIZE - 12))
    inner_glow = tuple(min(255, int(v + 40 * pulse)) for v in accent)
    surface.fill(inner_glow, (x + 10, y + 10, C.TILE_SIZE - 20, C.TILE_SIZE - 20))


def _draw_hazard(surface: pygame.Surface, x: int, y: int, t: float) -> None:
    """Spikes: a row of triangles on a darker base with animated glow."""
    # Animated subtle glow behind spikes
    glow_pulse = 0.5 + 0.5 * math.sin(t * 3.0)
    base_r = int(40 + 15 * glow_pulse)
    base_g = int(20 + 8 * glow_pulse)
    surface.fill((base_r, base_g, 28), (x, y, C.TILE_SIZE, C.TILE_SIZE))

    spikes = 4
    sw = C.TILE_SIZE // spikes
    pts = []
    for i in range(spikes):
        bx = x + i * sw
        pts.append([(bx, y + C.TILE_SIZE), (bx + sw // 2, y + 4), (bx + sw, y + C.TILE_SIZE)])

    # Spike color pulses slightly
    spike_col = (min(255, C.COLOR_HAZARD[0] + int(20 * glow_pulse)),
                 C.COLOR_HAZARD[1],
                 min(255, C.COLOR_HAZARD[2] + int(10 * glow_pulse)))
    for tri in pts:
        pygame.draw.polygon(surface, spike_col, tri)


# --------------------------------------------------------------------- loader
def load_level(path: Path) -> Level:
    """Read a level JSON file and build a fully indexed Level."""
    data = json.loads(path.read_text(encoding="utf-8"))

    # Derive theme_index from level number in the id (level_01 -> 0, etc.)
    stem = path.stem  # e.g. "level_01"
    digits = "".join(ch for ch in stem if ch.isdigit())
    theme_index = int(digits) - 1 if digits.isdigit() else 0

    level = Level(
        id=data["id"],
        name=data.get("name", data["id"]),
        tilemap=data["tilemap"],
        spawn_tile=tuple(data.get("spawn", [1, 1])),
        exit_tile=tuple(data.get("exit", [0, 0])),
        moving_platforms=[],
        theme_index=theme_index,
    )
    # Build moving platforms from the optional list.
    for mp in data.get("moving_platforms", []):
        w = mp.get("w", 3)
        rect = pygame.Rect(
            mp["x"] * C.TILE_SIZE,
            mp["y"] * C.TILE_SIZE,
            w * C.TILE_SIZE,
            C.TILE_SIZE,
        )
        level.moving_platforms.append(
            MovingPlatform(
                rect=rect,
                axis=mp.get("axis", "x"),
                range_px=float(mp.get("range", 4)) * C.TILE_SIZE,
                speed=float(mp.get("speed", 80)),
                phase=float(mp.get("phase", 0.0)),
                origin_x=rect.x,
                origin_y=rect.y,
            )
        )
    level._index()
    return level


def load_all_levels() -> List[Level]:
    """Load every level_*.json from the levels directory in numeric order."""
    if not C.LEVELS_DIR.exists():
        return []
    files = sorted(
        C.LEVELS_DIR.glob("level_*.json"),
        key=lambda p: _level_sort_key(p.stem),
    )
    return [load_level(p) for p in files]


def _level_sort_key(stem: str):
    """Sort level_02 before level_10 by reading the trailing number."""
    digits = "".join(ch for ch in stem if ch.isdigit())
    return int(digits) if digits else 0
