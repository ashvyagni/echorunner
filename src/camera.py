"""
camera.py
=========
A smooth, juicy camera designed for sleek platformer feel.

Features:
* **Velocity-based lookahead** — camera leads proportionally to player speed
* **Asymmetric deadzone** — tighter horizontal, more forgiving vertical
* **Exponential lerp** — frame-rate independent smooth follow
* **Idle breath** — subtle oscillation when player is stationary
* **Trauma-based shake** — smooth sinusoidal noise, not random per-tick
* **Bounds clamping** — stays within level limits
"""

from __future__ import annotations

import math
import random

from . import constants as C


class Camera:
    """Tracks an x/y world offset used to translate world -> screen coords."""

    def __init__(self) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self._trauma: float = 0.0
        self._shake_x: float = 0.0
        self._shake_y: float = 0.0
        self._shake_seed_x = random.uniform(0, 1000)
        self._shake_seed_y = random.uniform(0, 1000)
        self._shake_time = 0.0
        self._rng = random.Random(99)
        self._facing: int = 1
        self._breath_time: float = 0.0
        self._last_target_x: float = 0.0
        self._last_target_y: float = 0.0
        self._target_vx: float = 0.0
        self._target_vy: float = 0.0

    def update(self, target_x: float, target_y: float,
               level_width: int, level_height: int,
               dt: float, facing: int = 1,
               player_vx: float = 0.0, player_vy: float = 0.0) -> None:
        """Smoothly follow the target with velocity-based lookahead.

        Parameters
        ----------
        player_vx, player_vy : float
            Player velocity for velocity-based camera lead.
        """
        self._facing = facing

        # Smooth velocity tracking (exponential moving average)
        self._target_vx = self._target_vx * 0.85 + player_vx * 0.15
        self._target_vy = self._target_vy * 0.85 + player_vy * 0.15

        # ---- velocity-based lookahead ----
        # Lead camera in movement direction, scaled by speed
        speed = abs(self._target_vx)
        look_x = facing * (C.CAMERA_LOOKAHEAD + speed * 0.12)  # 40px base + speed bonus
        look_y = self._target_vy * 0.03  # slight lead when falling/jumping

        desired_cx = target_x + look_x
        desired_cy = target_y + look_y
        desired_x = desired_cx - C.SCREEN_W / 2
        desired_y = desired_cy - C.SCREEN_H / 2

        # ---- horizontal follow with asymmetric deadzone ----
        cur_cx = self.x + C.SCREEN_W / 2
        hband = C.SCREEN_W * 0.5 * C.CAMERA_DEADZONE
        if abs(cur_cx - desired_cx) > hband:
            t = 1.0 - math.exp(-C.CAMERA_LERP * dt)
            self.x += (desired_x - self.x) * t
        else:
            # Inside deadzone: gently drift toward target for smooth centering
            t = 1.0 - math.exp(-C.CAMERA_LERP * 0.3 * dt)
            self.x += (desired_x - self.x) * t

        # ---- vertical follow ----
        if level_height > C.SCREEN_H:
            cur_cy = self.y + C.SCREEN_H / 2
            vband = C.SCREEN_H * 0.5 * C.CAMERA_DEADZONE * 0.8  # tighter vertical
            if abs(cur_cy - desired_cy) > vband:
                t = 1.0 - math.exp(-C.CAMERA_LERP * 0.8 * dt)
                self.y += (desired_y - self.y) * t
            else:
                t = 1.0 - math.exp(-C.CAMERA_LERP * 0.2 * dt)
                self.y += (desired_y - self.y) * t
        else:
            self.y = 0.0

        # ---- idle breath: subtle oscillation when player is stationary ----
        is_idle = abs(self._target_vx) < 20 and abs(self._target_vy) < 20
        if is_idle:
            self._breath_time += dt
            breath_x = math.sin(self._breath_time * 0.8) * 2.0
            breath_y = math.sin(self._breath_time * 1.1) * 1.5
            self.x += breath_x * dt * 2
            self.y += breath_y * dt * 2
        else:
            self._breath_time = 0.0

        # ---- clamp to level bounds ----
        self.x = max(0.0, min(self.x, max(0.0, level_width - C.SCREEN_W)))
        if level_height > C.SCREEN_H:
            self.y = max(0.0, min(self.y, max(0.0, level_height - C.SCREEN_H)))

        # ---- trauma / shake ----
        self._trauma = max(0.0, self._trauma - C.SHAKE_TRAUMA_DECAY * dt)
        self._shake_time += dt
        shake = self._trauma ** 2
        # Multi-frequency shake for organic feel
        freq1 = 18.0
        freq2 = 27.0
        nx = (math.sin(self._shake_time * freq1 + self._shake_seed_x) * 0.6
              + math.sin(self._shake_time * freq2 + self._shake_seed_x * 1.3) * 0.4)
        ny = (math.sin(self._shake_time * freq1 * 1.3 + self._shake_seed_y) * 0.4
              + math.sin(self._shake_time * freq2 * 0.9 + self._shake_seed_y * 1.7) * 0.6)
        max_offset = 6.0
        self._shake_x = nx * shake * max_offset
        self._shake_y = ny * shake * max_offset

    def add_shake(self, intensity: float) -> None:
        """Add a shake event. intensity is px; normalized to trauma (0..1)."""
        self._trauma = min(1.0, self._trauma + intensity / 10.0)

    def reset(self) -> None:
        self.x = 0.0
        self.y = 0.0
        self._trauma = 0.0
        self._shake_x = 0.0
        self._shake_y = 0.0
        self._breath_time = 0.0
        self._target_vx = 0.0
        self._target_vy = 0.0

    @property
    def render_x(self) -> float:
        """Camera x including shake — use this for rendering."""
        return self.x + self._shake_x

    @property
    def render_y(self) -> float:
        """Camera y including shake — use this for rendering."""
        return self.y + self._shake_y

    def apply(self, world_x: float, world_y: float) -> tuple[int, int]:
        """Convert a world-space point to screen-space (includes shake)."""
        return int(world_x - self.render_x), int(world_y - self.render_y)
