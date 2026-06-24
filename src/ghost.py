"""
ghost.py
========
The signature EchoRunner mechanic: past runs replay as collidable ghosts.

* ``Ghost``        — one replaying run. Advances one frame per tick and draws a
                     semi-transparent body with a soft glow, fading trail, and
                     a facing indicator.
* ``GhostManager`` — owns all ghosts for the current level. Loads them from
                     disk on run start, ticks them, draws them, and reports
                     collisions against the player.

Frame-locked replay: ghosts advance exactly one frame per game tick, matching
how they were recorded, so the obstacle you see is the obstacle you made.
"""

from __future__ import annotations

from typing import List

import pygame

from . import constants as C
from .save_system import SaveSystem

# How long ghosts take to fade in on run start (seconds).
_FADE_IN_TIME = 0.3
# Completed-run ghosts are brighter; death-run ghosts are more faded.
_COMPLETED_ALPHA_MULT = 1.1   # up to 255
_DEATH_ALPHA_MULT = 0.7


class Ghost:
    """A single replaying run."""

    def __init__(self, frames: List[dict], color: tuple[int, int, int],
                 completed: bool = True,
                 alpha: int = C.GHOST_ALPHA) -> None:
        self.frames = frames
        self.color = color
        self.completed = completed
        # Adjust base opacity: completed ghosts feel "solid", death ghosts feel
        # like a warning marker.
        mult = _COMPLETED_ALPHA_MULT if completed else _DEATH_ALPHA_MULT
        self.alpha = min(255, int(alpha * mult))
        self.frame_index = 0
        self._trail: List[tuple[int, int]] = []
        self._tick = 0
        self._age: float = 0.0  # time since first frame (for fade-in)
        self._body = self._build_body()
        self._glow = self._build_glow()
        # per-frame shimmer flag (set by manager if particle system is active)
        self.emit_shimmer: bool = True

    # ------------------------------------------------------------ surface cache
    def _build_body(self) -> pygame.Surface:
        size = C.PLAYER_SIZE
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*self.color, self.alpha), (0, 0, size, size),
                         border_radius=7)
        pygame.draw.rect(surf, (*self.color, min(255, self.alpha + 50)),
                         (3, 3, size - 6, size - 6), border_radius=5)
        return surf

    def _build_glow(self) -> pygame.Surface:
        """A soft, larger circle behind the ghost body — ambient glow."""
        size = C.PLAYER_SIZE
        pad = 8
        surf = pygame.Surface((size + pad * 2, size + pad * 2), pygame.SRCALPHA)
        glow_alpha = max(10, self.alpha // 3)
        pygame.draw.rect(surf, (*self.color, glow_alpha),
                         (0, 0, size + pad * 2, size + pad * 2), border_radius=12)
        return surf

    # ----------------------------------------------------------------- update
    def update(self, dt: float = 0.0) -> None:
        if self.is_finished():
            return
        self.frame_index += 1
        self._tick += 1
        self._age += dt
        if self._tick % C.GHOST_TRAIL_EVERY == 0:
            fx, fy = self.current_pos()
            self._trail.append((fx, fy))
            if len(self._trail) > C.GHOST_TRAIL_LEN:
                self._trail.pop(0)

    # ----------------------------------------------------------------- state
    def current_pos(self) -> tuple[int, int]:
        f = self.frames[min(self.frame_index, len(self.frames) - 1)]
        return f["x"], f["y"]

    def current_facing(self) -> int:
        f = self.frames[min(self.frame_index, len(self.frames) - 1)]
        return f.get("facing", 1)

    def is_finished(self) -> bool:
        return self.frame_index >= len(self.frames)

    def get_rect(self) -> pygame.Rect:
        """Forgiveness hitbox: slightly smaller than the visible body."""
        x, y = self.current_pos()
        s = C.GHOST_HITBOX_SHRINK
        return pygame.Rect(x + s, y + s,
                           C.PLAYER_SIZE - 2 * s, C.PLAYER_SIZE - 2 * s)

    def nearest_dist(self, px: int, py: int) -> float:
        """Distance from the player to this ghost's center (for proximity)."""
        gx, gy = self.current_pos()
        return ((gx + C.PLAYER_SIZE / 2) - px) ** 2 + ((gy + C.PLAYER_SIZE / 2) - py) ** 2

    # ----------------------------------------------------------------- draw
    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float) -> None:
        if self.is_finished():
            return
        x, y = self.current_pos()
        sx, sy = int(x - cam_x), int(y - cam_y)
        # global fade-in: ease from 0 to full alpha over _FADE_IN_TIME
        fade = min(1.0, self._age / _FADE_IN_TIME) if _FADE_IN_TIME > 0 else 1.0
        if fade <= 0.01:
            return
        facing = self.current_facing()

        # soft glow behind the body
        gw, gh = self._glow.get_size()
        glow_copy = self._glow.copy()
        glow_copy.set_alpha(int(255 * fade))
        surface.blit(glow_copy, (sx - (gw - C.PLAYER_SIZE) // 2,
                                  sy - (gh - C.PLAYER_SIZE) // 2))

        # fading trail
        for i, (tx, ty) in enumerate(self._trail):
            t_alpha = int(self.alpha * (i + 1) / (len(self._trail) + 1) * 0.5 * fade)
            if t_alpha < 5:
                continue
            ghost_trail = pygame.Surface((C.PLAYER_SIZE, C.PLAYER_SIZE),
                                          pygame.SRCALPHA)
            pygame.draw.rect(ghost_trail, (*self.color, t_alpha),
                             (0, 0, C.PLAYER_SIZE, C.PLAYER_SIZE), border_radius=6)
            surface.blit(ghost_trail, (int(tx - cam_x), int(ty - cam_y)))

        # body (facing-aware: flip if facing left)
        body_copy = self._body.copy()
        body_copy.set_alpha(int(255 * fade))
        if facing < 0:
            body_copy = pygame.transform.flip(body_copy, True, False)
        surface.blit(body_copy, (sx, sy))


class GhostManager:
    """Owns and coordinates all ghosts for the current level."""

    def __init__(self, save: SaveSystem, level_id: str) -> None:
        self.save = save
        self.level_id = level_id
        self.ghosts: List[Ghost] = []
        self._raw: List[dict] = []

    # ------------------------------------------------------------ load / save
    def load(self) -> None:
        self._raw = self.save.load_ghosts(self.level_id)

    def save_ghost(self, frames: List[dict], completed: bool,
                   completion_time: float | None) -> None:
        record = SaveSystem.make_ghost_record(frames, completed, completion_time)
        best = self.save.get_best_time(self.level_id)
        self.save.append_ghost(self.level_id, record, best)

    def clear(self) -> None:
        self.save.clear_ghosts(self.level_id)
        self.ghosts.clear()
        self._raw.clear()

    # ------------------------------------------------------------ replay
    def start_replay(self) -> None:
        """Instantiate Ghost objects from loaded data with per-ghost styling."""
        self.ghosts = []
        for i, record in enumerate(self._raw):
            frames = record.get("frames", [])
            if not frames:
                continue
            color = C.GHOST_COLORS[i % len(C.GHOST_COLORS)]
            completed = record.get("completed", False)
            self.ghosts.append(Ghost(frames, color, completed=completed))

    def update(self, dt: float = 0.0) -> None:
        for g in self.ghosts:
            g.update(dt)

    def count(self) -> int:
        return len(self._raw)

    def active_count(self) -> int:
        return sum(1 for g in self.ghosts if not g.is_finished())

    # ------------------------------------------------------------ collision
    def check_collision(self, player_rect: pygame.Rect) -> bool:
        for g in self.ghosts:
            if g.is_finished():
                continue
            if player_rect.colliderect(g.get_rect()):
                return True
        return False

    def nearest_ghost_dist(self, px: int, py: int) -> float:
        """Squared distance to the nearest active ghost (for proximity warnings)."""
        best = float("inf")
        for g in self.ghosts:
            if g.is_finished():
                continue
            d = g.nearest_dist(px, py)
            if d < best:
                best = d
        return best

    # ------------------------------------------------------------ draw
    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float) -> None:
        for g in self.ghosts:
            g.draw(surface, cam_x, cam_y)
