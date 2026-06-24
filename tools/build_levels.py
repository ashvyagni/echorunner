"""
tools/build_levels.py
=====================
Generates the level_*.json files from readable ASCII art so the maps can be
verified by eye.  Run once:

    python tools/build_levels.py

Legend:
    ' '  empty (0)
    '#'  platform (1)
    'E'  exit (2)
    '^'  hazard / spikes (3)

Spawn/exit and moving_platforms are declared per-level as Python data and
merged into the JSON, so the ASCII map only encodes the static tile layer.
"""

from __future__ import annotations

import json
from pathlib import Path

LEGEND = {' ': 0, '#': 1, 'E': 2, '^': 3}

# Each level: (id, name, ascii_rows, spawn, exit, moving_platforms)
# All ascii rows must be the same length. The generator enforces this.

LEVELS = []

# ---------------------------------------------------------------------------
# LEVEL 1 — First Steps
# A gentle flat ground with a couple of optional higher platforms and a step.
# ---------------------------------------------------------------------------
ascii1 = [
    "                                                            ",  # 0
    "                                                            ",  # 1
    "                                                            ",  # 2
    "                                                            ",  # 3
    "                                                            ",  # 4
    "                                                            ",  # 5
    "                     ######                                 ",  # 6
    "                                                            ",  # 7
    "             ####                                           ",  # 8
    "                                                            ",  # 9
    "                                  ####                      ",  # 10
    "                                                            ",  # 11
    "                                                            ",  # 12
    "                                                            ",  # 13
    "                       ####                                 ",  # 14
    "                                                            ",  # 15
    "###############   ##########################################",  # 16
    "###############^^^##########################################",  # 17
]
LEVELS.append(("level_01", "First Steps", ascii1, [1, 15], [56, 15], []))
# Note: a tiny 3-tile pit around cols 15-17 introduces jumping gently.

# ---------------------------------------------------------------------------
# LEVEL 2 — The Gap
# Three pits separated by platforms. Falling into a pit hits spikes.
# ---------------------------------------------------------------------------
ascii2 = [
    "                                                            ",  # 0
    "                                                            ",  # 1
    "                                                            ",  # 2
    "                                                            ",  # 3
    "                                                            ",  # 4
    "        ####                  #####                         ",  # 5
    "                                                            ",  # 6
    "                       ####                                 ",  # 7
    "                                                            ",  # 8
    "                                  ####                      ",  # 9
    "                                                            ",  # 10
    "                                                            ",  # 11
    "                                                            ",  # 12
    "                                                            ",  # 13
    "                                                            ",  # 14
    "                                                            ",  # 15
    "#######   #######   ########   #############################",  # 16
    "#######^^^#######^^^########^^^#############################",  # 17
]
LEVELS.append(("level_02", "The Gap", ascii2, [1, 15], [56, 15], []))

# ---------------------------------------------------------------------------
# LEVEL 3 — Rising Risk
# Moving platforms carry the player across a wide void. Sparse static ground.
# ---------------------------------------------------------------------------
ascii3 = [
    "                                                            ",  # 0
    "                                                            ",  # 1
    "                                                            ",  # 2
    "                                                  ###       ",  # 3  exit ledge
    "                                                            ",  # 4
    "                                                            ",  # 5
    "                                                            ",  # 6
    "                                                            ",  # 7
    "                                                            ",  # 8
    "                                                            ",  # 9
    "                                                            ",  # 10
    "                                                            ",  # 11
    "                                                            ",  # 12
    "                                                            ",  # 13
    "                                                            ",  # 14
    "                                                            ",  # 15
    "####                                                        ",  # 16
    "####                                                        ",  # 17
]
mp3 = [
    # horizontal shuttle over the void at ground-ish height
    {"x": 6, "y": 16, "w": 3, "axis": "x", "range": 3, "speed": 90, "phase": 0.0},
    {"x": 14, "y": 14, "w": 3, "axis": "x", "range": 2, "speed": 80, "phase": 1.0},
    {"x": 22, "y": 12, "w": 3, "axis": "y", "range": 3, "speed": 70, "phase": 0.5},
    {"x": 30, "y": 10, "w": 3, "axis": "x", "range": 3, "speed": 90, "phase": 1.5},
    {"x": 38, "y": 8, "w": 3, "axis": "y", "range": 2, "speed": 75, "phase": 0.0},
    {"x": 46, "y": 6, "w": 3, "axis": "x", "range": 3, "speed": 85, "phase": 0.8},
]
LEVELS.append(("level_03", "Rising Risk", ascii3, [1, 15], [52, 2], mp3))

# ---------------------------------------------------------------------------
# LEVEL 4 — The Maze
# Multiple tiers and routes; a couple of dead-end platforms to punish guessing.
# ---------------------------------------------------------------------------
ascii4 = [
    "                                                            ",  # 0
    "                                                            ",  # 1
    "                                                            ",  # 2
    "                  ###                       ###             ",  # 3
    "                                                            ",  # 4
    "          ####        ####                   ####           ",  # 5
    "                                                            ",  # 6
    "                            ####                            ",  # 7
    "                                                            ",  # 8
    "    ####             ####              ####                 ",  # 9
    "                                                            ",  # 10
    "                                                            ",  # 11
    "                                                            ",  # 12
    "##############                     #########################",  # 13
    "                                                            ",  # 14
    "                                                            ",  # 15
    "      ####   ####      ##############      ####   ####      ",  # 16
    "      ^^^^   ^^^^      ################      ^^^^   ^^^^    ",  # 17
]
LEVELS.append(("level_04", "The Maze", ascii4, [2, 12], [54, 12], []))

# ---------------------------------------------------------------------------
# LEVEL 5 — Ghost Town
# Densest layout: stacked tiers, spikes, tight jumps. Built to get crowded.
# ---------------------------------------------------------------------------
ascii5 = [
    "                                                            ",  # 0
    "                                                            ",  # 1
    "                              ###                           ",  # 2
    "                            #######                         ",  # 3
    "                  ###                        ###            ",  # 4
    "              ####              ####               ####     ",  # 5
    "                                                            ",  # 6
    "       ####                          ####                   ",  # 7
    "                                                            ",  # 8
    "   ###              ###                   ###               ",  # 9
    "                                                            ",  # 10
    "                                                            ",  # 11
    "                                                            ",  # 12
    "                                                            ",  # 13
    "###              ########              #########        ### ",  # 14
    "                                                            ",  # 15
    "########    ####    #########    ###    ######    ##########",  # 16
    "########^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^#########",  # 17
]
LEVELS.append(("level_05", "Ghost Town", ascii5, [1, 15], [56, 15], []))


def build(ascii_rows):
    """Validate row widths and convert ASCII to an int tilemap."""
    width = len(ascii_rows[0])
    tilemap = []
    for r, row in enumerate(ascii_rows):
        assert len(row) == width, f"row {r} width {len(row)} != {width}"
        tilemap.append([LEGEND[ch] for ch in row])
    return tilemap, width


def main():
    out = Path(__file__).resolve().parent.parent / "levels"
    out.mkdir(exist_ok=True)
    for level_id, name, ascii_rows, spawn, exit_tile, mps in LEVELS:
        tilemap, width = build(ascii_rows)
        # sanity: exit tile in the map must be reachable / present nearby
        data = {
            "id": level_id,
            "name": name,
            "spawn": spawn,
            "exit": exit_tile,
            "tilemap": tilemap,
            "moving_platforms": mps,
        }
        # ensure exit cell itself is the exit tile
        ec, er = exit_tile
        if 0 <= er < len(tilemap) and 0 <= ec < width:
            tilemap[er][ec] = 2
        (out / f"{level_id}.json").write_text(
            json.dumps(data, separators=(",", ":")), encoding="utf-8")
        print(f"wrote {level_id}.json  ({width}x{len(tilemap)})")


if __name__ == "__main__":
    main()
