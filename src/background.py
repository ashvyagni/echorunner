"""
background.py
=============
A cheap parallax starfield to give the dark navy backdrop some depth.
Two layers of dots scroll at different fractions of the camera for a
sense of motion without any image assets.
"""

from __future__ import annotations

import random

import pygame

from . import constants as C


class Background:
    def __init__(self) -> None:
        rng = random.Random(20240617)
        self.layer_far = [(rng.randint(0, C.SCREEN_W), rng.randint(0, C.SCREEN_H),
                           rng.randint(1, 2)) for _ in range(80)]
        self.layer_near = [(rng.randint(0, C.SCREEN_W), rng.randint(0, C.SCREEN_H),
                            rng.randint(2, 3)) for _ in range(40)]

    def draw(self, surface: pygame.Surface, cam_x: float) -> None:
        surface.fill(C.BG_COLOR)

        for x, y, r in self.layer_far:
            sx = int(x - cam_x * 0.15) % C.SCREEN_W
            pygame.draw.circle(surface, (45, 45, 70), (sx, y), r)

        for x, y, r in self.layer_near:
            sx = int(x - cam_x * 0.35) % C.SCREEN_W
            pygame.draw.circle(surface, (75, 75, 110), (sx, y), r)
