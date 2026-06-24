"""
hud.py
======
In-game heads-up display: run timer, personal best, ghost (echo) count,
death counter, ghost proximity warning, and timer urgency effects.
"""

from __future__ import annotations

import math

import pygame

from . import constants as C
from .fonts import Font


def _font(size: int, bold: bool = False) -> Font:
    """Create a robust Font that works on any pygame install."""
    return Font(size, bold=bold)


def format_time(seconds: float | None) -> str:
    """Format seconds as M:SS.cs  e.g. 0:18.42.  Returns '--' for None."""
    if seconds is None:
        return "--:--"
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m}:{s:05.2f}"


class HUD:
    """Renders the run timer, best time, ghost count, death counter,
    ghost proximity warning, and timer urgency effects."""

    def __init__(self) -> None:
        self.font_big = _font(28, bold=True)
        self.font_small = _font(18)
        self.font_micro = _font(14)
        self._warn_flash_t: float = 0.0  # accumulates for flashing

    def draw(self, surface: pygame.Surface, run_time: float,
             best_time: float | None, ghost_count: int, fps: float = 0.0,
             *, deaths: int = 0, ghost_near: bool = False,
             best_time_kwarg: float | None = None) -> None:
        # `best_time_kwarg` is passed by game.py as `best_time=` kwarg; it's
        # the same value as the positional `best_time` (both from the save).
        # We ignore the duplicate and use `best_time`.
        self._warn_flash_t += 1.0 / C.FPS

        # ---- panel background for legibility ----
        panel_h = 95 if deaths > 0 else 78
        panel = pygame.Surface((260, panel_h), pygame.SRCALPHA)
        panel.fill((*C.COLOR_PANEL, 150))
        surface.blit(panel, (12, 12))

        # ---- timer with urgency ----
        timer_color = C.COLOR_TEXT
        if best_time is not None and run_time > best_time:
            # beating personal best — pulse red at threshold
            gap = run_time - best_time
            if gap < 2.0:
                urgency = 0.5 + 0.5 * math.sin(self._warn_flash_t * 8.0)
                timer_color = _lerp_color(C.COLOR_TEXT, C.COLOR_DANGER, urgency)
        timer = self.font_big.render(format_time(run_time), True, timer_color)
        surface.blit(timer, (22, 16))

        # ---- best time ----
        best_label = self.font_small.render(
            f"BEST  {format_time(best_time)}", True, C.COLOR_ACCENT)
        surface.blit(best_label, (22, 50))

        # ---- death counter (current level) ----
        if deaths > 0:
            deaths_txt = self.font_small.render(
                f"DEATHS  {deaths}", True, C.COLOR_DANGER)
            surface.blit(deaths_txt, (22, 73))

        # ---- ghost count (echoes), top-right ----
        echo_color = C.COLOR_TEXT
        if ghost_near:
            # flash the echo label red when a ghost is close
            flash = 0.5 + 0.5 * math.sin(self._warn_flash_t * 12.0)
            echo_color = _lerp_color(C.COLOR_TEXT, C.COLOR_DANGER, flash)

        echoes = self.font_big.render(f"ECHOES {ghost_count}", True, echo_color)
        ex = C.SCREEN_W - echoes.get_width() - 22
        epanel = pygame.Surface((echoes.get_width() + 20, 38), pygame.SRCALPHA)
        epanel.fill((*C.COLOR_PANEL, 150))
        surface.blit(epanel, (ex - 10, 12))
        surface.blit(echoes, (ex, 18))

        # ---- ghost proximity warning banner ----
        if ghost_near and ghost_count > 0:
            flash = 0.5 + 0.5 * math.sin(self._warn_flash_t * 10.0)
            warn_alpha = int(180 * flash)
            warn_surf = self.font_big.render("⚠ ECHO NEAR", True, C.COLOR_DANGER)
            warn_bg = pygame.Surface(
                (warn_surf.get_width() + 30, 40), pygame.SRCALPHA)
            warn_bg.fill((20, 0, 0, warn_alpha))
            wx = (C.SCREEN_W - warn_bg.get_width()) // 2
            wy = C.SCREEN_H - 60
            surface.blit(warn_bg, (wx, wy))
            # modulate the text brightness with the flash
            text_alpha = int(255 * flash)
            warn_surf.set_alpha(text_alpha)
            surface.blit(warn_surf, (wx + 15, wy + 6))

        # ---- tiny fps readout, bottom-left ----
        if fps:
            fps_txt = self.font_micro.render(f"{fps:5.1f} fps", True, C.COLOR_TEXT_DIM)
            surface.blit(fps_txt, (14, C.SCREEN_H - 22))


def _lerp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    """Linearly interpolate between two RGB colors."""
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))
