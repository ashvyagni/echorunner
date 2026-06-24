"""
particles.py
============
A small, fast particle system for EchoRunner's game-feel.

Design: object pool. A fixed array of Particle slots is allocated once. Dead
particles become available for reuse, so nothing is allocated or garbage
collected during gameplay — important when spawning dozens of particles on
every landing, death, and ghost shimmer.

All emitters are free functions that stamp particles into the pool. The
ParticleSystem.update()/draw() loop is O(pool size) regardless of spawn rate.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pygame

from . import constants as C


@dataclass(slots=True)
class Particle:
    """One particle. Reused via the pool — never instantiated per-frame."""
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    life: float = 0.0      # remaining seconds
    max_life: float = 0.0  # original life (for fade math)
    size: float = 2.0
    color: Tuple[int, int, int] = (255, 255, 255)
    gravity: float = 0.0
    drag: float = 0.0      # velocity multiplier per second (1.0 = no drag)
    alive: bool = False


class ParticleSystem:
    """Owns the pool and exposes emitter helpers."""

    def __init__(self, pool_size: int = C.PARTICLE_POOL_SIZE) -> None:
        self.pool: List[Particle] = [Particle() for _ in range(pool_size)]
        self._next = 0  # round-robin cursor for slot reuse
        self._rng = random.Random(7)

    # ------------------------------------------------------------------ spawn
    def _spawn(self, **kw) -> None:
        """Grab a slot (reusing oldest dead one, else round-robin) and set it."""
        # Try to find a dead slot first (cheap reuse).
        p = self.pool[self._next]
        if p.alive:
            # fall back to scanning for any dead slot
            for cand in self.pool:
                if not cand.alive:
                    p = cand
                    break
        # (re)initialize fields
        p.alive = True
        p.x = kw.get("x", 0.0)
        p.y = kw.get("y", 0.0)
        p.vx = kw.get("vx", 0.0)
        p.vy = kw.get("vy", 0.0)
        life = kw.get("life", 0.4)
        p.life = life
        p.max_life = life
        p.size = kw.get("size", 2.0)
        p.color = kw.get("color", (255, 255, 255))
        p.gravity = kw.get("gravity", 0.0)
        p.drag = kw.get("drag", 1.0)
        self._next = (self._next + 1) % len(self.pool)

    # ------------------------------------------------------------------ update
    def update(self, dt: float) -> None:
        """Advance all live particles. dt is already time-scaled by caller."""
        for p in self.pool:
            if not p.alive:
                continue
            p.life -= dt
            if p.life <= 0.0:
                p.alive = False
                continue
            # drag (frame-rate independent): drag<1 slows velocity over time
            p.vx *= p.drag ** dt
            p.vy = p.vy * (p.drag ** dt) + p.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt

    # ------------------------------------------------------------------ draw
    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float) -> None:
        for p in self.pool:
            if not p.alive:
                continue
            # fade alpha over life
            t = max(0.0, p.life / p.max_life)
            alpha = int(255 * t)
            r = max(1, int(p.size * (0.5 + 0.5 * t)))
            sx, sy = int(p.x - cam_x), int(p.y - cam_y)
            # off-screen cull
            if sx < -r or sx > C.SCREEN_W + r or sy < -r or sy > C.SCREEN_H + r:
                continue
            col = (*p.color, alpha)
            # draw on a tiny per-particle alpha surface (cheap at small sizes)
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, col, (r, r), r)
            surface.blit(surf, (sx - r, sy - r))

    def clear(self) -> None:
        for p in self.pool:
            p.alive = False

    # ==================================================================
    #  Emitters — each stamps a burst of particles into the pool.
    # ==================================================================
    def dust_landing(self, x: float, y: float, color=C.COLOR_PLATFORM_TOP) -> None:
        """Small dust puff when the player lands."""
        for _ in range(8):
            ang = self._rng.uniform(math.pi, 2 * math.pi)  # upward fan
            spd = self._rng.uniform(40, 110)
            self._spawn(
                x=x + self._rng.uniform(-6, 6), y=y,
                vx=math.cos(ang) * spd, vy=math.sin(ang) * spd * 0.6,
                life=self._rng.uniform(0.25, 0.45),
                size=self._rng.uniform(2, 4),
                color=color, gravity=260, drag=0.06,
            )

    def dust_jump(self, x: float, y: float, color=C.COLOR_PLATFORM_TOP) -> None:
        """Downward puff when the player jumps."""
        for _ in range(6):
            ang = self._rng.uniform(0.15 * math.pi, 0.85 * math.pi)  # downward
            spd = self._rng.uniform(30, 70)
            self._spawn(
                x=x + self._rng.uniform(-4, 4), y=y,
                vx=math.cos(ang) * spd * self._rng.choice((-1, 1)),
                vy=abs(math.sin(ang)) * spd,
                life=self._rng.uniform(0.2, 0.35),
                size=self._rng.uniform(2, 3),
                color=color, gravity=120, drag=0.1,
            )

    def death_burst(self, x: float, y: float,
                    colors=((255, 90, 110), (255, 200, 200), (255, 255, 255))) -> None:
        """Explosive red/white burst on death."""
        for _ in range(28):
            ang = self._rng.uniform(0, 2 * math.pi)
            spd = self._rng.uniform(80, 280)
            self._spawn(
                x=x, y=y,
                vx=math.cos(ang) * spd, vy=math.sin(ang) * spd,
                life=self._rng.uniform(0.4, 0.8),
                size=self._rng.uniform(2, 5),
                color=self._rng.choice(colors),
                gravity=200, drag=0.25,
            )

    def complete_sparkle(self, x: float, y: float,
                         color=(255, 220, 120)) -> None:
        """Golden swirl around the exit on level clear."""
        for _ in range(24):
            ang = self._rng.uniform(0, 2 * math.pi)
            r = self._rng.uniform(10, 36)
            spd = self._rng.uniform(20, 70)
            self._spawn(
                x=x + math.cos(ang) * r, y=y + math.sin(ang) * r,
                vx=-math.sin(ang) * spd, vy=math.cos(ang) * spd,  # tangential
                life=self._rng.uniform(0.5, 1.0),
                size=self._rng.uniform(2, 4),
                color=color, gravity=-30, drag=0.4,
            )

    def ghost_shimmer(self, x: float, y: float, color) -> None:
        """Tiny sparkles shed by a moving ghost."""
        self._spawn(
            x=x + self._rng.uniform(-6, 6), y=y + self._rng.uniform(-6, 6),
            vx=self._rng.uniform(-8, 8), vy=self._rng.uniform(-20, -4),
            life=self._rng.uniform(0.25, 0.5),
            size=self._rng.uniform(1, 2),
            color=color, gravity=10, drag=0.5,
        )

    def run_dust(self, x: float, y: float, facing: int,
                 color=C.COLOR_PLATFORM_TOP) -> None:
        """Tiny dust kicked up while running."""
        self._spawn(
            x=x, y=y,
            vx=-facing * self._rng.uniform(20, 50),
            vy=self._rng.uniform(-30, -10),
            life=self._rng.uniform(0.15, 0.3),
            size=self._rng.uniform(1, 2),
            color=color, gravity=120, drag=0.2,
        )
