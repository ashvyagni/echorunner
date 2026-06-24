"""
player.py
=========
The player entity: physics, input handling, tile collision, and the per-frame
recording system that feeds the ghost replay.

Recording contract
------------------
Every fixed update tick the player appends a snapshot via get_frame_data().
These snapshots are what Ghost replays later, so they must be deterministic
given the same input — that's why we run physics on a fixed timestep.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

import pygame

from . import constants as C


@dataclass
class _InputState:
    """Captured input for the current tick (set from pygame events/keys)."""
    left: bool = False
    right: bool = False
    jump_pressed: bool = False   # edge-triggered this tick
    jump_held: bool = False
    run: bool = False


class Player:
    """A controllable character with platformer physics.

    Not a pygame Sprite subclass — we keep it as a plain object with a Rect so
    the rendering stays flexible (we draw a procedurally-built sprite).
    """

    SIZE = C.PLAYER_SIZE

    def __init__(self, x: float, y: float) -> None:
        self.rect = pygame.Rect(int(x), int(y), self.SIZE, self.SIZE)
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.facing: int = 1  # 1 = right, -1 = left

        self.on_ground: bool = False
        self._coyote: float = 0.0       # time since last grounded
        self._jump_buffer: float = 0.0  # time since jump pressed
        self._jump_consumed: bool = False

        # Animation timer for squash/stretch + run cycle.
        self._anim_t: float = 0.0
        # Juice state
        self._land_squash: float = 0.0       # remaining squash seconds (on land)
        self._run_bob_phase: float = 0.0     # for run-cycle bob
        self._wall_sliding: bool = False      # true when pressed against wall midair
        # Afterimage history: list of (x, y, facing, age) snapshots
        self._afterimages: List[tuple[int, int, int]] = []
        self._afterimage_timer: float = 0.0
        # Death animation progress (0 = alive, >0 = dying, animates over time)
        self.dying: bool = False
        self.death_t: float = 0.0
        # Per-tick juice signals (set in update(), read by the Game class)
        self.just_landed: bool = False
        self.just_jumped: bool = False
        self.just_bonked: bool = False
        self.land_velocity: float = 0.0
        self._touched_wall: bool = False

        # Recording of this run — list of frame dicts. Reset on spawn.
        self.current_recording: List[dict] = []
        self._record_every = 1  # record every tick (60fps) — frame-locked replay
        self._tick: int = 0

    # --------------------------------------------------------------- spawn/reset
    def respawn(self, x: float, y: float) -> None:
        """Reset physics state and clear the current recording."""
        self.rect.topleft = (int(x), int(y))
        self.vx = self.vy = 0.0
        self.facing = 1
        self.on_ground = False
        self._coyote = 0.0
        self._jump_buffer = 0.0
        self._jump_consumed = False
        self._anim_t = 0.0
        self._land_squash = 0.0
        self._run_bob_phase = 0.0
        self._wall_sliding = False
        self._afterimages.clear()
        self._afterimage_timer = 0.0
        self.dying = False
        self.death_t = 0.0
        self.current_recording = []
        self._tick = 0

    # --------------------------------------------------------------- input
    def capture_input(self, keys, jump_pressed: bool, jump_held: bool) -> _InputState:
        return _InputState(
            left=keys[pygame.K_a] or keys[pygame.K_LEFT],
            right=keys[pygame.K_d] or keys[pygame.K_RIGHT],
            jump_pressed=jump_pressed,
            jump_held=jump_held,
            run=keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT],
        )

    # --------------------------------------------------------------- update
    def update(self, dt: float, inp: _InputState, platforms: List[pygame.Rect],
               moving_deltas: List[tuple[float, float]]) -> None:
        """Advance physics by dt seconds.

        ``moving_deltas`` is the (dx, dy) of any moving platform the player is
        currently standing on, so the player rides it instead of sliding off.
        """
        # reset per-tick wall flag (set during _move_axis collision)
        self._touched_wall = False
        # ----- horizontal intention -----
        target = 0.0
        if inp.left and not inp.right:
            target = -(C.RUN_SPEED if inp.run else C.WALK_SPEED)
            self.facing = -1
        elif inp.right and not inp.left:
            target = (C.RUN_SPEED if inp.run else C.WALK_SPEED)
            self.facing = 1

        accel = C.ACCEL if self.on_ground else C.AIR_ACCEL
        if target == 0.0 and self.on_ground:
            # apply friction toward zero
            if self.vx > 0:
                self.vx = max(0.0, self.vx - C.FRICTION * dt)
            else:
                self.vx = min(0.0, self.vx + C.FRICTION * dt)
        else:
            # accelerate toward target
            if self.vx < target:
                self.vx = min(target, self.vx + accel * dt)
            else:
                self.vx = max(target, self.vx - accel * dt)

        # ----- timers -----
        if self.on_ground:
            self._coyote = C.COYOTE_TIME
        else:
            self._coyote = max(0.0, self._coyote - dt)

        if inp.jump_pressed:
            self._jump_buffer = C.JUMP_BUFFER
        else:
            self._jump_buffer = max(0.0, self._jump_buffer - dt)

        # ----- jump -----
        can_jump = self._coyote > 0.0 and not self._jump_consumed
        if self._jump_buffer > 0.0 and can_jump:
            self.vy = C.JUMP_FORCE
            self._jump_consumed = True
            self._jump_buffer = 0.0
            self._coyote = 0.0
            self.on_ground = False
            self.just_jumped = True

        # variable jump height: release early -> cut upward velocity
        if not inp.jump_held and self.vy < 0.0:
            self.vy *= 1.0 - (1.0 - C.VARIABLE_JUMP_CUT) * min(1.0, dt * 12)

        # ----- gravity -----
        self.vy = min(self.vy + C.GRAVITY * dt, C.MAX_FALL)

        # ----- ride moving platform if standing on one -----
        for dx, dy in moving_deltas:
            self.rect.x += dx  # type: ignore
            self.rect.y += dy  # type: ignore

        # ----- integrate + collide (resolve X then Y to avoid snags) -----
        self._move_axis(self.vx * dt, 0.0, platforms)
        grounded_before = self.on_ground
        self.on_ground = False
        prev_vy = self.vy
        self._move_axis(0.0, self.vy * dt, platforms)

        # reset per-tick juice signals (read by the Game class after update)
        self.just_landed = False
        self.just_jumped = False
        self.just_bonked = False
        self.land_velocity = 0.0

        if self.on_ground and not grounded_before:
            # just landed — allow a fresh jump
            self._jump_consumed = False
            self.just_landed = True
            self.land_velocity = prev_vy
            self._land_squash = C.LAND_SQUASH_TIME

        # detect wall-slide: airborne, moving toward a wall, pressed into it
        self._wall_sliding = (not self.on_ground and self.vy > 0
                              and abs(self.vx) < 5 and self._touched_wall)

        # advance juice timers
        self._land_squash = max(0.0, self._land_squash - dt)
        if self.on_ground and abs(self.vx) > 30:
            self._run_bob_phase += dt * 14.0
        else:
            self._run_bob_phase = 0.0

        # afterimage trail: snapshot periodically while moving fast
        self._afterimage_timer += dt
        speed = math.hypot(self.vx, self.vy)
        if speed > 250 and self._afterimage_timer >= C.AFTERIMAGE_INTERVAL:
            self._afterimage_timer = 0.0
            self._afterimages.append((self.rect.x, self.rect.y, self.facing))
            if len(self._afterimages) > C.AFTERIMAGE_COUNT:
                self._afterimages.pop(0)

        self._anim_t += dt
        self._tick += 1
        self._record()

    def _move_axis(self, dx: float, dy: float, platforms: List[pygame.Rect]) -> None:
        """Move and resolve collisions along a single axis."""
        self.rect.x += int(dx) if abs(dx) >= 1 else dx  # type: ignore
        self.rect.y += int(dy) if abs(dy) >= 1 else dy  # type: ignore

        for p in platforms:
            if not self.rect.colliderect(p):
                continue
            if dx > 0:    # moving right
                self.rect.right = p.left
                self.vx = 0.0
                self._touched_wall = True
            elif dx < 0:  # moving left
                self.rect.left = p.right
                self.vx = 0.0
                self._touched_wall = True
            if dy > 0:    # moving down (landing)
                self.rect.bottom = p.top
                self.vy = 0.0
                self.on_ground = True
            elif dy < 0:  # moving up (bonk head)
                self.rect.top = p.bottom
                self.vy = 0.0
                self.just_bonked = True

    # --------------------------------------------------------------- recording
    def _record(self) -> None:
        """Append a snapshot of the current state to the run recording."""
        if self._tick % self._record_every != 0:
            return
        self.current_recording.append({
            "x": self.rect.x,
            "y": self.rect.y,
            "facing": self.facing,
            "on_ground": self.on_ground,
            "vx": round(self.vx, 1),
            "vy": round(self.vy, 1),
        })

    def get_frame_data(self) -> dict:
        """Return the latest snapshot (matches the recording schema)."""
        return {
            "x": self.rect.x,
            "y": self.rect.y,
            "facing": self.facing,
            "on_ground": self.on_ground,
        }

    # --------------------------------------------------------------- death anim
    def start_death(self) -> None:
        """Begin the death animation (called by Game on death)."""
        self.dying = True
        self.death_t = 0.0

    def advance_death_anim(self, dt: float) -> None:
        """Advance the visual death animation. Returns False when finished."""
        if self.dying:
            self.death_t += dt

    @property
    def death_anim_done(self) -> bool:
        return self.dying and self.death_t >= C.DEATH_ANIM_TIME

    # --------------------------------------------------------------- render
    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float) -> None:
        """Draw the player with squash/stretch, bob, afterimage, and death anim."""
        size = self.SIZE

        # ---- afterimages first (behind everything) ----
        for i, (ax, ay, af) in enumerate(self._afterimages):
            alpha = int(60 * (i + 1) / len(self._afterimages)) if self._afterimages else 0
            self._blit_ghostlike(surface, ax, ay, af, cam_x, cam_y,
                                 C.COLOR_PLAYER_ACCENT, alpha, size)

        # ---- death animation overrides everything ----
        if self.dying:
            t = min(1.0, self.death_t / C.DEATH_ANIM_TIME)
            scale = max(0.05, 1.0 - t)
            spin = t * 360.0
            alpha = int(255 * (1.0 - t))
            self._blit_death(surface, cam_x, cam_y, scale, spin, alpha, size)
            return

        sx, sy = int(self.rect.x - cam_x), int(self.rect.y - cam_y)

        # ---- compute squash/stretch factors ----
        # base: airborne stretch (jump) / squash (fall)
        squash = 1.0
        if not self.on_ground:
            squash = 1.12 if self.vy < 0 else 0.92
        # landing squash: ease back from a wide/short shape over LAND_SQUASH_TIME
        if self._land_squash > 0.0:
            # 0 at full squash, 1 at recovered
            k = 1.0 - (self._land_squash / C.LAND_SQUASH_TIME)
            # wide-and-short at k=0, normal at k=1, with slight overshoot
            land_w = 1.18
            land_h = 0.78
            overshoot = math.sin(k * math.pi) * 0.06  # tiny bounce
            ws = land_w + (1.0 - land_w) * k + overshoot
            hs = land_h + (1.0 - land_h) * k + overshoot
            squash_x = ws
            squash_y = hs
        else:
            squash_x = 1.0 / squash
            squash_y = squash

        w = max(4, int(size * squash_x))
        h = max(4, int(size * squash_y))

        # run bob: tiny vertical oscillation while running
        bob = 0
        if self.on_ground and abs(self.vx) > 30:
            bob = int(math.sin(self._run_bob_phase) * C.RUN_BOB_AMP)

        rx = sx + (size - w) // 2
        ry = sy + (size - h) + bob

        # wall slide tilt: shift the top in the slide direction
        tilt = 0
        if self._wall_sliding:
            tilt = self.facing * 4

        body = pygame.Rect(rx + tilt, ry, w, h)
        pygame.draw.rect(surface, C.COLOR_PLAYER, body, border_radius=7)
        # accent stripe (cyan)
        pygame.draw.rect(surface, C.COLOR_PLAYER_ACCENT,
                         (rx + tilt + 2, ry + h - 6, w - 4, 3), border_radius=2)
        # eye — indicates facing
        ex = rx + tilt + (w // 2) + (self.facing * (w // 5))
        pygame.draw.circle(surface, (20, 20, 35), (ex, ry + h // 3), 3)

    def _blit_ghostlike(self, surface, x, y, facing, cam_x, cam_y,
                        color, alpha, size) -> None:
        """Draw a faded copy at (x,y) — used for afterimages."""
        if alpha <= 0:
            return
        sx, sy = int(x - cam_x), int(y - cam_y)
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*color, alpha), (0, 0, size, size), border_radius=7)
        surface.blit(surf, (sx, sy))

    def _blit_death(self, surface, cam_x, cam_y, scale, spin, alpha, size) -> None:
        """Shrink, spin, and fade the player body for the death animation."""
        cx = self.rect.centerx - int(cam_x)
        cy = self.rect.centery - int(cam_y)
        s = max(2, int(size * scale))
        surf = pygame.Surface((s, s), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*C.COLOR_PLAYER, alpha), (0, 0, s, s), border_radius=7)
        pygame.draw.rect(surf, (*C.COLOR_PLAYER_ACCENT, alpha),
                         (2, s - 5, max(1, s - 4), 2), border_radius=2)
        # rotate around center
        rot = pygame.transform.rotate(surf, spin)
        rr = rot.get_rect(center=(cx, cy))
        surface.blit(rot, rr)
