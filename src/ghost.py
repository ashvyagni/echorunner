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

Age-based visual decay: older ghosts (by recording index) progressively
desaturate toward gray, reinforcing the "ancient mistake" vs. "just happened"
narrative. The oldest ghost is most gray; the newest is fully colored.

Near-miss detection: GhostManager.check_near_miss() reports whether the
player passed within NEAR_MISS_RADIUS pixels of any ghost without colliding,
enabling the Game class to fire a distinct audio + visual cue.
"""

from __future__ import annotations

import math
from typing import List

import pygame

from . import constants as C
from .save_system import SaveSystem

# How long ghosts take to fade in on run start (seconds).
_FADE_IN_TIME = 0.3
# Completed-run ghosts are brighter; death-run ghosts are more faded.
_COMPLETED_ALPHA_MULT = 1.1   # up to 255
_DEATH_ALPHA_MULT = 0.7

# Near-miss: player hitbox within this many pixels (squared) of ghost center.
NEAR_MISS_RADIUS_SQ = 60 ** 2  # 60px radius

# How much each "age step" desaturates the ghost color (0=none, 1=full gray).
# With MAX_GHOSTS=20, the oldest ghost gets desaturation factor near 0.65.
_AGE_DESATURATE_MAX = 0.65


def _desaturate(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """Blend ``color`` toward gray by ``factor`` (0=unchanged, 1=fully gray)."""
    r, g, b = color
    gray = int(0.299 * r + 0.587 * g + 0.114 * b)
    nr = int(r + (gray - r) * factor)
    ng = int(g + (gray - g) * factor)
    nb = int(b + (gray - b) * factor)
    return (nr, ng, nb)


class Ghost:
    """A single replaying run.

    Parameters
    ----------
    age_index : int
        0 = newest (this session's last ghost), higher = older. Used to
        compute desaturation so old ghosts visually "fade to gray."
    total_ghosts : int
        Total number of ghosts currently active (for normalizing age_index).
    """

    def __init__(self, frames: List[dict], color: tuple[int, int, int],
                 completed: bool = True,
                 alpha: int = C.GHOST_ALPHA,
                 age_index: int = 0,
                 total_ghosts: int = 1) -> None:
        self.frames = frames
        self.completed = completed
        # Adjust base opacity: completed ghosts feel "solid", death ghosts feel
        # like a warning marker.
        mult = _COMPLETED_ALPHA_MULT if completed else _DEATH_ALPHA_MULT
        self.alpha = min(255, int(alpha * mult))
        self.frame_index = 0
        self._trail: List[tuple[int, int]] = []
        self._tick = 0
        self._age: float = 0.0  # time since first frame (for fade-in)
        # Near-miss flash: when player grazes us, flash outline for 1 frame.
        self._near_miss_flash: float = 0.0  # seconds remaining for flash

        # Desaturate older ghosts toward gray.
        age_norm = age_index / max(1, total_ghosts - 1) if total_ghosts > 1 else 0.0
        desat_factor = age_norm * _AGE_DESATURATE_MAX
        self.color = _desaturate(color, desat_factor)

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
        if self._near_miss_flash > 0:
            self._near_miss_flash = max(0.0, self._near_miss_flash - dt)
        if self._tick % C.GHOST_TRAIL_EVERY == 0:
            fx, fy = self.current_pos()
            self._trail.append((fx, fy))
            if len(self._trail) > C.GHOST_TRAIL_LEN:
                self._trail.pop(0)

    def trigger_near_miss(self) -> None:
        """Called by GhostManager when the player nearly collides."""
        self._near_miss_flash = 0.12  # ~7 frames at 60Hz

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
        """Squared distance from the player to this ghost's center (for proximity)."""
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

        # near-miss outline flash: bright white border when player just grazed us
        if self._near_miss_flash > 0:
            flash_alpha = int(255 * (self._near_miss_flash / 0.12))
            size = C.PLAYER_SIZE
            outline = pygame.Surface((size + 4, size + 4), pygame.SRCALPHA)
            pygame.draw.rect(outline, (255, 255, 255, flash_alpha),
                             (0, 0, size + 4, size + 4), 2, border_radius=8)
            surface.blit(outline, (sx - 2, sy - 2))

        # echo shimmer: faint chromatic aberration hint (offset red/blue copies)
        if self.emit_shimmer and fade > 0.5:
            shimmer_a = int(25 * fade)
            shim = pygame.Surface((C.PLAYER_SIZE, C.PLAYER_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(shim, (255, 120, 120, shimmer_a),
                             (0, 0, C.PLAYER_SIZE, C.PLAYER_SIZE), border_radius=7)
            surface.blit(shim, (sx + 2, sy))
            shim2 = pygame.Surface((C.PLAYER_SIZE, C.PLAYER_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(shim2, (120, 120, 255, shimmer_a),
                             (0, 0, C.PLAYER_SIZE, C.PLAYER_SIZE), border_radius=7)
            surface.blit(shim2, (sx - 2, sy))


class GhostManager:
    """Owns and coordinates all ghosts for the current level."""

    def __init__(self, save: SaveSystem, level_id: str) -> None:
        self.save = save
        self.level_id = level_id
        self.ghosts: List[Ghost] = []
        self._raw: List[dict] = []
        # Track which ghosts just finished this tick for despawn events.
        self._just_finished: List[Ghost] = []
        # Track near-miss state (per ghost) to avoid repeated triggering.
        self._near_miss_cooldown: dict[int, float] = {}  # ghost id → cooldown

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
        """Instantiate Ghost objects from loaded data with per-ghost styling.

        Ghosts are indexed from newest (index 0) to oldest (index n-1).
        Older ghosts receive more desaturation so they read as "ancient."
        """
        self.ghosts = []
        total = len(self._raw)
        for i, record in enumerate(self._raw):
            frames = record.get("frames", [])
            if not frames:
                continue
            color = C.GHOST_COLORS[i % len(C.GHOST_COLORS)]
            completed = record.get("completed", False)
            # Reverse age: the LAST record is the newest run.
            age_index = total - 1 - i  # 0=newest, total-1=oldest
            self.ghosts.append(Ghost(
                frames, color, completed=completed,
                age_index=age_index, total_ghosts=total,
            ))
        self._just_finished = []
        self._near_miss_cooldown = {}

    def update(self, dt: float = 0.0) -> None:
        self._just_finished = []
        for g in self.ghosts:
            was_active = not g.is_finished()
            g.update(dt)
            if was_active and g.is_finished():
                self._just_finished.append(g)

    def count(self) -> int:
        return len(self._raw)

    def active_count(self) -> int:
        return sum(1 for g in self.ghosts if not g.is_finished())

    def just_finished_count(self) -> int:
        """Number of ghosts that finished replay this tick (for despawn SFX)."""
        return len(self._just_finished)

    # ------------------------------------------------------------ collision
    def check_collision(self, player_rect: pygame.Rect) -> bool:
        for g in self.ghosts:
            if g.is_finished():
                continue
            if player_rect.colliderect(g.get_rect()):
                return True
        return False

    def check_near_miss(self, player_rect: pygame.Rect) -> bool:
        """Return True if the player is within near-miss radius of any active
        ghost WITHOUT colliding. Also triggers the ghost's outline flash.
        """
        px = player_rect.centerx
        py = player_rect.centery
        found = False
        for g in self.ghosts:
            if g.is_finished():
                continue
            gid = id(g)
            # check cooldown so we don't spam near-miss events
            if self._near_miss_cooldown.get(gid, 0.0) > 0:
                continue
            dist_sq = g.nearest_dist(px, py)
            if dist_sq < NEAR_MISS_RADIUS_SQ and not player_rect.colliderect(g.get_rect()):
                g.trigger_near_miss()
                self._near_miss_cooldown[gid] = 0.5  # 0.5s cooldown per ghost
                found = True
        # Decay cooldowns
        for gid in list(self._near_miss_cooldown.keys()):
            self._near_miss_cooldown[gid] = max(0.0, self._near_miss_cooldown[gid] - 1 / 60.0)
        return found

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
