"""
fonts.py
========
A small font abstraction that renders text no matter what.

Priority:
  1. ``pygame.font``  — the normal, fast path (used on every well-formed
     pygame install and in the frozen .exe).
  2. ``pygame._freetype`` — the compiled freetype module, accessed directly to
     dodge the ``pygame.sysfont`` circular import that appears on some
     cutting-edge Python wheels where ``font`` is a pure-Python stub.

If neither is available (genuinely audio/video-less headless box), we render
text into a crude blocky bitmap so the game is still *playable*.  This path is
essentially never hit in practice but keeps the game from ever crashing on a
font problem.
"""

from __future__ import annotations

import importlib
from typing import Optional

import logging
import pygame

log = logging.getLogger("echorunner.fonts")


class Font:
    """Unified font handle. ``render`` always returns a pygame.Surface."""

    def __init__(self, size: int, bold: bool = False) -> None:
        self.size = size
        self.bold = bold
        self._impl, self._backend = _pick_backend(size, bold)

    def render(self, text: str, antialias: bool, color) -> pygame.Surface:
        if self._backend == "font":
            return self._impl.render(text, antialias, color)
        if self._backend == "freetype":
            surf = self._impl.render(text, fgcolor=color)[0]
            return surf
        return _blocky_render(text, self.size, color)

    def size(self, text: str) -> tuple[int, int]:
        if self._backend in ("font", "freetype"):
            try:
                return self._impl.get_rect(text).size  # freetype
            except AttributeError:
                return self._impl.size(text)           # font
        return _blocky_size(text, self.size)


# ------------------------------------------------------------------ backend pick
def _pick_backend(size: int, bold: bool):
    # 1) standard pygame.font
    try:
        f = pygame.font
        if f.get_init() or _try_font_init():
            return f.SysFont("arial,helvetica,verdana", size, bold=bold), "font"
    except Exception as e:
        log.warning("pygame.font backend failed: %s", e)

    # 2) compiled freetype, imported directly to avoid sysfont circular import
    try:
        ft = importlib.import_module("pygame._freetype")
        if not ft.get_init():
            ft.init()
        fnt = ft.Font(None, size)
        fnt.style = ft.STYLE_NORMAL if not bold else ft.STYLE_BOLD
        return fnt, "freetype"
    except Exception as e:
        log.warning("pygame._freetype backend failed: %s", e)

    log.warning("Both font backends unavailable — using blocky bitmap fallback. "
                "Check your pygame/SDL2_ttf installation.")
    return None, "blocky"


def _try_font_init() -> bool:
    try:
        pygame.font.init()
        return True
    except Exception:
        return False


# ------------------------------------------------------------------ blocky fallback
# A tiny 5x7 bitmap font so text is still legible if every real font backend
# is unavailable. Built from scratch — no assets required.
_RAW_ROWS = [  # each glyph: 7 rows of 5 bits
        0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110,  # A
        0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110,  # B
        0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110,  # C
        0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110,  # D
        0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111,  # E
        0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000,  # F
        0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01111,  # G
        0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001,  # H
        0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110,  # I
        0b00111, 0b00010, 0b00010, 0b00010, 0b10010, 0b10010, 0b01100,  # J
        0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001,  # K
        0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111,  # L
        0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001,  # M
        0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001,  # N
        0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110,  # O
        0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000,  # P
        0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101,  # Q
        0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001,  # R
        0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110,  # S
        0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100,  # T
        0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110,  # U
        0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100,  # V
        0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b10101, 0b01010,  # W
        0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001,  # X
        0b10001, 0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100,  # Y
        0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111,  # Z
        0b00000, 0b00000, 0b01110, 0b01110, 0b00000, 0b00000, 0b00000,  # 0
        0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110,  # 1
        0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111,  # 2
        0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110,  # 3
        0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010,  # 4
        0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110,  # 5
        0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110,  # 6
        0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000,  # 7
        0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110,  # 8
        0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100,  # 9
        0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000,  # (space)
        0b00000, 0b00000, 0b01110, 0b01110, 0b00000, 0b00000, 0b00000,  # :
        0b00000, 0b00000, 0b00000, 0b01110, 0b01110, 0b00000, 0b00000,  # .
        0b00000, 0b00000, 0b00000, 0b01110, 0b00000, 0b00000, 0b00000,  # !
        0b00000, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00000,  # -
        0b00010, 0b00100, 0b01000, 0b10000, 0b01000, 0b00100, 0b00010,  # /
        0b01000, 0b10100, 0b00010, 0b00100, 0b01000, 0b00101, 0b00010,  # +
        0b00100, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00100,  # %
        0b00010, 0b00100, 0b01110, 0b10101, 0b11111, 0b00100, 0b01000,  # '
]
_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 :.!-+/%'"
assert len(_RAW_ROWS) == len(_CHARS) * 7, (
    f"Glyph table misaligned: {len(_RAW_ROWS)} rows for {len(_CHARS)} chars "
    f"(expected {len(_CHARS) * 7})"
)
_GLYPHS = {
    ch: _RAW_ROWS[i * 7:(i + 1) * 7]
    for i, ch in enumerate(_CHARS)
}


def _blocky_size(text: str, size: int) -> tuple[int, int]:
    scale = max(1, size // 8)
    return (len(text) * 6 - 1) * scale, 7 * scale


def _blocky_render(text: str, size: int, color) -> pygame.Surface:
    scale = max(1, size // 8)
    gw, gh = 5, 7
    w = max(1, (len(text) * 6 - 1)) * scale
    h = gh * scale
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for i, ch in enumerate(text.upper()):
        rows = _GLYPHS.get(ch, [0] * 7)
        for row in range(gh):
            bits = rows[row] & 0b11111
            for col in range(gw):
                if bits & (1 << (gw - 1 - col)):
                    px = (i * 6 + col) * scale
                    py = row * scale
                    surf.fill(color, (px, py, scale, scale))
    return surf
