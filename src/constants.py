"""
constants.py
============
Central place for every "magic number" in EchoRunner.

Keeping values here means physics, ghost tuning, colors and screen
dimensions can be tweaked in one file without hunting through the
codebase.  Nothing in this module instantiates pygame.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path helpers (PyInstaller-friendly)
# ---------------------------------------------------------------------------
# When frozen with PyInstaller, bundled read-only data lives in sys._MEIPASS
# (a temp extraction dir), while writable data (saves/) must live next to the
# executable. When running from source, both anchor to the project root.
def _bundled_root() -> Path:
    """Where read-only bundled data (levels/) lives."""
    if hasattr(os, "_MEIPASS"):  # running inside a PyInstaller bundle
        return Path(os._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def _writable_root() -> Path:
    """Where writable data (saves/) lives — next to the exe, or project root."""
    if hasattr(os, "_MEIPASS"):  # frozen: write beside the executable
        return Path(sys.argv[0]).resolve().parent
    return Path(__file__).resolve().parent.parent


ROOT = _writable_root()               # used by SAVES_DIR (writable)
LEVELS_DIR = _bundled_root() / "levels"   # read-only data
SAVES_DIR = _writable_root() / "saves"    # writable data

# ---------------------------------------------------------------------------
# Screen
# ---------------------------------------------------------------------------
SCREEN_W = 1280
SCREEN_H = 720
FPS = 60
TILE_SIZE = 32

# Player sprite is a touch smaller than a tile so it fits through 1-tile gaps.
PLAYER_SIZE = 28

# Background color (dark navy).
BG_COLOR = (15, 15, 35)

# ---------------------------------------------------------------------------
# Physics  (units: pixels, seconds)
# ---------------------------------------------------------------------------
WALK_SPEED = 200      # horizontal speed while walking
RUN_SPEED = 320       # horizontal speed while holding Shift (optional)
ACCEL = 2200          # ground acceleration toward target speed
AIR_ACCEL = 1400      # reduced control while airborne
FRICTION = 2000       # ground deceleration when no input
JUMP_FORCE = -550     # initial jump velocity (negative = up)
GRAVITY = 1200        # downward acceleration
MAX_FALL = 800        # terminal velocity
COYOTE_TIME = 0.1     # grace period after leaving a ledge
JUMP_BUFFER = 0.1     # jump press queued shortly before landing
VARIABLE_JUMP_CUT = 0.45  # velocity multiplier when jump released early

# ---------------------------------------------------------------------------
# Ghosts
# ---------------------------------------------------------------------------
MAX_GHOSTS = 20          # cap per level (oldest dropped)
GHOST_ALPHA = 115        # 0-255, ~45% opacity
GHOST_TRAIL_LEN = 4      # number of trailing copies
GHOST_TRAIL_EVERY = 4    # leave a trail copy every N frames
# Forgiveness: shrink the ghost hitbox a little so near-misses feel fair.
GHOST_HITBOX_SHRINK = 6

# Each ghost cycles through this palette for visual variety.
GHOST_COLORS = [
    (255, 107, 107),  # coral
    (78, 205, 196),   # teal
    (255, 230, 109),  # yellow
    (168, 230, 207),  # mint
    (255, 139, 148),  # pink
    (195, 166, 255),  # purple
]

# ---------------------------------------------------------------------------
# World colors
# ---------------------------------------------------------------------------
COLOR_PLAYER = (240, 240, 240)
COLOR_PLAYER_ACCENT = (120, 230, 255)
COLOR_PLATFORM = (60, 60, 80)
COLOR_PLATFORM_TOP = (90, 90, 110)
COLOR_HAZARD = (220, 70, 90)
COLOR_EXIT = (78, 205, 196)
COLOR_MOVING_PLATFORM = (110, 90, 160)
COLOR_MOVING_PLATFORM_TOP = (150, 130, 200)
COLOR_TEXT = (235, 235, 245)
COLOR_TEXT_DIM = (150, 150, 170)
COLOR_ACCENT = (120, 230, 255)
COLOR_DANGER = (255, 90, 110)
COLOR_PANEL = (24, 24, 48)

# Tile ids used by level JSON.
TILE_EMPTY = 0
TILE_PLATFORM = 1
TILE_EXIT = 2
TILE_HAZARD = 3  # instant death (spikes) — extends the tilemap spec

# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------
DEATH_RESTART_DELAY = 0.6   # seconds before auto-restart on death
COMPLETE_HOLD = 1.8         # level-complete screen min display before allowing input
MENU_TRANSITION = 0.15      # seconds for button fade

# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------
# These are tunable; the sound module degrades gracefully if mixer is absent.
SOUND_ENABLED_DEFAULT = True
MUSIC_ENABLED_DEFAULT = True
MASTER_VOLUME = 0.6

# ---------------------------------------------------------------------------
# Juice / game-feel tuning
# ---------------------------------------------------------------------------
# Camera
CAMERA_LERP = 6.0          # higher = snappier follow (per second)
CAMERA_DEADZONE = 0.15     # fraction of half-screen before camera starts moving
CAMERA_LOOKAHEAD = 40.0    # px the camera leads the player in facing direction

# Screen shake (intensity in px, duration in seconds)
SHAKE_DEATH = (9.0, 0.35)
SHAKE_LAND = (1.5, 0.06)
SHAKE_COMPLETE = (4.0, 0.18)
SHAKE_TRAUMA_DECAY = 2.5   # how fast shake trauma fades per second

# Time dilation (visual slow-motion). Physics stays at fixed 60Hz; this scales
# only particle/visual update rate so ghost determinism is preserved.
TIME_SCALE_DEATH = 0.30    # 30% speed during death sequence
TIME_SCALE_DEATH_DUR = 0.5
TIME_SCALE_COMPLETE = 0.45
TIME_SCALE_COMPLETE_DUR = 0.35

# Player juice
LAND_SQUASH_TIME = 0.09    # how long the landing squash lasts
RUN_BOB_AMP = 1.5          # px vertical bob amplitude while running
AFTERIMAGE_INTERVAL = 0.04 # seconds between afterimage snapshots
AFTERIMAGE_COUNT = 3       # fading copies trailing the player
DEATH_ANIM_TIME = 0.30     # spin/shrink/fade before restart

# Screen transitions
SCREEN_FADE_TIME = 0.22    # fade-to-black between states

# Particles
PARTICLE_POOL_SIZE = 300   # max simultaneously alive particles

# Level themes — each entry shifts the world palette for visual variety.
# Index 0 = level 1. Values are (platform, platform_top, background, accent).
LEVEL_THEMES = [
    ((60, 60, 80),   (90, 90, 110),  (15, 15, 35),  (120, 230, 255)),  # 1 navy/steel
    ((78, 56, 70),   (112, 84, 100), (24, 14, 28),  (255, 150, 120)),  # 2 warm rose
    ((58, 52, 92),   (96, 86, 140),  (14, 12, 30),  (180, 140, 255)),  # 3 purple
    ((50, 70, 70),   (80, 110, 108), (10, 22, 22),  (110, 230, 200)),  # 4 teal-green
    ((80, 60, 55),   (118, 90, 84),  (28, 16, 12),  (255, 180, 90)),   # 5 ember
]

