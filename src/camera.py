"""
camera.py
=========
A smooth, juicy camera. EchoRunner levels are wider than the screen, so the
camera follows the player with:

* **Lerp follow** — smoothly eases toward the target instead of snapping.
* **Deadzone** — small movements near screen center don't twitch the camera.
* **Lookahead** — leads the player slightly in the direction they face.
* **Screen shake** — additive trauma-based shake for impacts and death.

Shake uses the "trauma" model: events add trauma (0..1), it decays over time,
and the rendered offset is trauma^2 * intensity * random direction. Squaring
trauma makes small bumps feel small and big impacts feel violent.
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
        self._trauma: float = 0.0          # 0..1, decays over time
        self._shake_x: float = 0.0
        self._shake_y: float = 0.0
        self._rng = random.Random(99)
        self._facing: int = 1  # remembered for lookahead continuity

    # ------------------------------------------------------------ public API
    def update(self, target_x: float, target_y: float,
               level_width: int, level_height: int,
               dt: float, facing: int = 1) -> None:
        """Smoothly follow the target and apply shake. dt is real frame delta."""
        self._facing = facing

        # ---- desired camera center with lookahead in facing direction ----
        desired_cx = target_x + facing * C.CAMERA_LOOKAHEAD
        desired_cy = target_y
        desired_x = desired_cx - C.SCREEN_W / 2
        desired_y = desired_cy - C.SCREEN_H / 2

        # ---- deadzone + exponential lerp follow (frame-rate independent) ----
        cur_cx = self.x + C.SCREEN_W / 2
        band = C.SCREEN_W * 0.5 * C.CAMERA_DEADZONE
        if abs(cur_cx - desired_cx) > band:
            t = 1.0 - math.exp(-C.CAMERA_LERP * dt)
            self.x += (desired_x - self.x) * t

        # vertical: scroll only if the level is taller than the screen
        if level_height > C.SCREEN_H:
            cur_cy = self.y + C.SCREEN_H / 2
            vband = C.SCREEN_H * 0.5 * C.CAMERA_DEADZONE
            if abs(cur_cy - desired_cy) > vband:
                t = 1.0 - math.exp(-C.CAMERA_LERP * dt)
                self.y += (desired_y - self.y) * t
        else:
            self.y = 0.0

        # ---- clamp to level bounds ----
        self.x = max(0.0, min(self.x, max(0.0, level_width - C.SCREEN_W)))

        # ---- trauma / shake ----
        self._trauma = max(0.0, self._trauma - C.SHAKE_TRAUMA_DECAY * dt)
        shake = self._trauma ** 2  # squared for non-linear feel
        ang = self._rng.uniform(0, 2 * math.pi)
        # up to ~25px offset at full trauma; per-event intensity scales trauma
        self._shake_x = math.cos(ang) * shake * 25.0
        self._shake_y = math.sin(ang) * shake * 25.0

    def add_shake(self, intensity: float) -> None:
        """Add a shake event. intensity is px; normalized to trauma (0..1)."""
        # ~10px shake == 1.0 trauma. Clamped so overlapping events stack but cap.
        self._trauma = min(1.0, self._trauma + intensity / 10.0)

    def reset(self) -> None:
        self.x = 0.0
        self.y = 0.0
        self._trauma = 0.0
        self._shake_x = 0.0
        self._shake_y = 0.0

    # ------------------------------------------------------------ conversion
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
