"""
background.py
=============
A cheap parallax starfield to give the dark navy backdrop some depth.
Three layers of dots scroll at different fractions of the camera for a
sense of motion without any image assets.

Layer order (back to front):
  layer_far    — tiny dim stars, barely move (depth illusion)
  layer_mid    — medium stars at half-speed
  layer_near   — larger bright dots, scroll fastest
"""

from __future__ import annotations

import math
import random

import pygame

from . import constants as C


class Background:
    """Three-layer parallax starfield + optional nebula wisps."""

    def __init__(self) -> None:
        rng = random.Random(20240617)
        # (x, y, radius)
        self.layer_far = [
            (rng.randint(0, C.SCREEN_W), rng.randint(0, C.SCREEN_H), rng.randint(1, 1))
            for _ in range(120)
        ]
        self.layer_mid = [
            (rng.randint(0, C.SCREEN_W), rng.randint(0, C.SCREEN_H), rng.randint(1, 2))
            for _ in range(60)
        ]
        self.layer_near = [
            (rng.randint(0, C.SCREEN_W), rng.randint(0, C.SCREEN_H), rng.randint(2, 3))
            for _ in range(30)
        ]
        # Nebula wisps: large dim ellipses for atmosphere
        self.nebulas = [
            (rng.randint(0, C.SCREEN_W), rng.randint(0, C.SCREEN_H),
             rng.randint(80, 180), rng.randint(40, 100),
             rng.choice([(20, 10, 40), (10, 20, 40), (25, 15, 35)]),
             rng.uniform(12, 20))
            for _ in range(5)
        ]
        self._t: float = 0.0

    def update(self, dt: float) -> None:
        """Advance twinkle timer."""
        self._t += dt

    def draw(self, surface: pygame.Surface, cam_x: float) -> None:
        """Draw background. Call each frame before any game objects."""
        surface.fill(C.BG_COLOR)

        # Nebula wisps (static, very dim)
        for nx, ny, nw, nh, col, twinkle_freq in self.nebulas:
            sx = (int(nx - cam_x * 0.05)) % (C.SCREEN_W + nw) - nw // 2
            # soft pulsing alpha
            pulse = int(8 + 6 * math.sin(self._t * twinkle_freq * 0.1))
            nsurf = pygame.Surface((nw, nh), pygame.SRCALPHA)
            pygame.draw.ellipse(nsurf, (*col, pulse), (0, 0, nw, nh))
            surface.blit(nsurf, (sx, ny))

        # Far stars — barely move, tiny, dim
        for x, y, r in self.layer_far:
            sx = int(x - cam_x * 0.08) % C.SCREEN_W
            twinkle = int(35 + 15 * math.sin(self._t * 1.7 + x * 0.05))
            c = (twinkle, twinkle, twinkle + 20)
            pygame.draw.circle(surface, c, (sx, y), r)

        # Mid stars — half-speed
        for x, y, r in self.layer_mid:
            sx = int(x - cam_x * 0.22) % C.SCREEN_W
            twinkle = int(55 + 20 * math.sin(self._t * 2.3 + y * 0.03))
            c = (twinkle, twinkle, min(255, twinkle + 30))
            pygame.draw.circle(surface, c, (sx, y), r)

        # Near stars — fastest, brightest
        for x, y, r in self.layer_near:
            sx = int(x - cam_x * 0.42) % C.SCREEN_W
            twinkle = int(75 + 30 * math.sin(self._t * 3.1 + x * 0.08 + y * 0.04))
            c = (twinkle, twinkle, min(255, twinkle + 40))
            pygame.draw.circle(surface, c, (sx, y), r)
