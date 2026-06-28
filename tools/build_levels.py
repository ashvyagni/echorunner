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
    'J'  jump pad (4) — launches player upward

All levels are 150 columns x 24 rows (4800x768 px).
"""

from __future__ import annotations

import json
from pathlib import Path

LEGEND = {' ': 0, '#': 1, 'E': 2, '^': 3, 'J': 4}
LEVELS = []
W = 150

def pad(s):
    return s[:W].ljust(W)

# ---------------------------------------------------------------------------
# LEVEL 1 — First Steps
# Tutorial level: introduces basic movement, jumping, spikes, and jump pads.
# Flat ground path with gaps containing spikes. Jump pads at key points.
# Moving platforms bridge wider gaps. Exit at the far right.
# ---------------------------------------------------------------------------
ascii1 = [
    pad(""),                                                                                                                        # 0
    pad(""),                                                                                                                        # 1
    pad(""),                                                                                                                        # 2
    pad(""),                                                                                                                        # 3
    pad(""),                                                                                                                        # 4
    pad(""),                                                                                                                        # 5
    pad(""),                                                                                                                        # 6
    pad(""),                                                                                                                        # 7
    pad(""),                                                                                                                        # 8
    pad(""),                                                                                                                        # 9
    pad(""),                                                                                                                        # 10
    pad(""),                                                                                                                        # 11
    pad(""),                                                                                                                        # 12
    pad(""),                                                                                                                        # 13
    pad(""),                                                                                                                        # 14
    pad(""),                                                                                                                        # 15
    pad(""),                                                                                                                        # 16
    pad(""),                                                                                                                        # 17
    pad(""),                                                                                                                        # 18
    pad(""),                                                                                                                        # 19
    pad("###  ####  #####  ######  ########  #######  ##########  #########  ############  ###########  ##############  #####E"),     # 20
    pad("###^^####^^#####^^######^^########^^#######^^##########^^#########^^############^^###########^^##############^^######"),     # 21
    pad("###^^####^^#####^^######^^########^^#######^^##########^^#########^^############^^###########^^##############^^######"),     # 22
    pad("###^^####^^#####^^######^^########^^#######^^##########^^#########^^############^^###########^^##############^^######"),     # 23
]
# Add jump pads on the ground platforms for vertical exploration
ascii1[20] = pad("###  ####  #####  ######  ########  #######  ##########  #########  ############  ###########  ##############  #####E")
mp1 = [
    {"x": 6, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 70, "phase": 0.0},
    {"x": 33, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 75, "phase": 0.5},
    {"x": 66, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 80, "phase": 1.0},
    {"x": 99, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 70, "phase": 0.0},
    {"x": 131, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 75, "phase": 0.5},
]
LEVELS.append(("level_01", "First Steps", ascii1, [1, 19], [146, 20], mp1))

# ---------------------------------------------------------------------------
# LEVEL 2 — The Ascent
# Vertical climbing level. Start at bottom-left, exit at top-right.
# Staircase of platforms going upward with jump pads at transitions.
# Moving platforms bridge the widest gaps.
# ---------------------------------------------------------------------------
ascii2 = [
    pad(""),                                                                                                                        # 0
    pad(""),                                                                                                                        # 1
    pad(""),                                                                                                                        # 2
    pad(""),                                                                                                                        # 3
    pad(""),                                                                                                                        # 4
    pad(""),                                                                                                                        # 5
    pad(""),                                                                                                                        # 6
    pad(""),                                                                                                                        # 7
    pad(""),                                                                                                                        # 8
    pad(""),                                                                                                                        # 9
    pad(""),                                                                                                                        # 10
    pad(""),                                                                                                                        # 11
    pad("                                                                                                          #####E"),            # 12
    pad("                                                                                                     ####"),                   # 13
    pad("                                                                                                ####"),                        # 14
    pad("                                                                                           ####"),                             # 15
    pad("                                                                                      ####"),                                  # 16
    pad("                                                                                 ####"),                                       # 17
    pad("                                                                            ####"),                                            # 18
    pad("                                                                       ####"),                                                 # 19
    pad("#####^^#####^^#####^^#####^^#####^^#####^^#####^^#####^^#####^^#####^^#####"),                                                 # 20
    pad("#####^^#####^^#####^^#####^^#####^^#####^^#####^^#####^^#####^^#####^^#####"),                                                 # 21
    pad("#####^^#####^^#####^^#####^^#####^^#####^^#####^^#####^^#####^^#####^^#####"),                                                 # 22
    pad("#####^^#####^^#####^^#####^^#####^^#####^^#####^^#####^^#####^^#####^^#####"),                                                 # 23
]
mp2 = [
    {"x": 10, "y": 19, "w": 3, "axis": "y", "range": 3, "speed": 80, "phase": 0.0},
    {"x": 25, "y": 17, "w": 3, "axis": "y", "range": 2, "speed": 75, "phase": 0.5},
    {"x": 40, "y": 15, "w": 3, "axis": "y", "range": 3, "speed": 85, "phase": 1.0},
    {"x": 55, "y": 13, "w": 3, "axis": "y", "range": 2, "speed": 70, "phase": 0.0},
    {"x": 70, "y": 11, "w": 3, "axis": "y", "range": 3, "speed": 90, "phase": 0.5},
    {"x": 85, "y": 9, "w": 3, "axis": "y", "range": 2, "speed": 80, "phase": 1.0},
    {"x": 100, "y": 7, "w": 3, "axis": "y", "range": 3, "speed": 85, "phase": 0.0},
    {"x": 115, "y": 5, "w": 3, "axis": "y", "range": 2, "speed": 75, "phase": 0.5},
    {"x": 130, "y": 3, "w": 3, "axis": "y", "range": 2, "speed": 90, "phase": 1.0},
]
LEVELS.append(("level_02", "The Ascent", ascii2, [1, 22], [145, 12], mp2))

# ---------------------------------------------------------------------------
# LEVEL 3 — Spike Gauntlet
# Dense horizontal run with spike pits. Small platforms at varying heights.
# Moving platforms over the worst pits. Requires precise jumping.
# ---------------------------------------------------------------------------
ascii3 = [
    pad(""),                                                                                                                        # 0
    pad(""),                                                                                                                        # 1
    pad(""),                                                                                                                        # 2
    pad(""),                                                                                                                        # 3
    pad(""),                                                                                                                        # 4
    pad(""),                                                                                                                        # 5
    pad(""),                                                                                                                        # 6
    pad(""),                                                                                                                        # 7
    pad(""),                                                                                                                        # 8
    pad(""),                                                                                                                        # 9
    pad(""),                                                                                                                        # 10
    pad(""),                                                                                                                        # 11
    pad(""),                                                                                                                        # 12
    pad(""),                                                                                                                        # 13
    pad(""),                                                                                                                        # 14
    pad(""),                                                                                                                        # 15
    pad(""),                                                                                                                        # 16
    pad(""),                                                                                                                        # 17
    pad(""),                                                                                                                        # 18
    pad(""),                                                                                                                        # 19
    pad("####  ###  ####  ###  #####  ###  ######  ###  ########  ###  ##########  ###  ############  ###  ##############E"),       # 20
    pad("####^^###^^####^^###^^#####^^###^^######^^###^^########^^###^^##########^^###^^############^^###^^##############"),       # 21
    pad("####^^###^^####^^###^^#####^^###^^######^^###^^########^^###^^##########^^###^^############^^###^^##############"),       # 22
    pad("####^^###^^####^^###^^#####^^###^^######^^###^^########^^###^^##########^^###^^############^^###^^##############"),       # 23
]
mp3 = [
    {"x": 7, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 90, "phase": 0.0},
    {"x": 20, "y": 19, "w": 3, "axis": "y", "range": 3, "speed": 100, "phase": 0.5},
    {"x": 35, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 85, "phase": 1.0},
    {"x": 50, "y": 19, "w": 3, "axis": "y", "range": 3, "speed": 95, "phase": 0.0},
    {"x": 65, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 90, "phase": 0.5},
    {"x": 82, "y": 19, "w": 3, "axis": "y", "range": 3, "speed": 105, "phase": 1.0},
    {"x": 100, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 85, "phase": 0.0},
    {"x": 118, "y": 19, "w": 3, "axis": "y", "range": 3, "speed": 100, "phase": 0.5},
    {"x": 135, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 90, "phase": 1.0},
]
LEVELS.append(("level_03", "Spike Gauntlet", ascii3, [1, 19], [148, 20], mp3))

# ---------------------------------------------------------------------------
# LEVEL 4 — Echo Chamber
# Ceiling spikes + ground spikes creating a narrow corridor. Platforms at
# various heights. Moving platforms in the middle. Jump pads for vertical play.
# ---------------------------------------------------------------------------
ascii4 = [
    pad(""),                                                                                                                        # 0
    pad(""),                                                                                                                        # 1
    pad(""),                                                                                                                        # 2
    pad(""),                                                                                                                        # 3
    pad(""),                                                                                                                        # 4
    pad(""),                                                                                                                        # 5
    pad(""),                                                                                                                        # 6
    pad(""),                                                                                                                        # 7
    pad(""),                                                                                                                        # 8
    pad(""),                                                                                                                        # 9
    pad(""),                                                                                                                        # 10
    pad(""),                                                                                                                        # 11
    pad(""),                                                                                                                        # 12
    pad(""),                                                                                                                        # 13
    pad(""),                                                                                                                        # 14
    pad("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^"), # 15
    pad(""),                                                                                                                        # 16
    pad(""),                                                                                                                        # 17
    pad(""),                                                                                                                        # 18
    pad(""),                                                                                                                        # 19
    pad("###  ###  ####  ###  ######  ###  ##########  ###  ##############  ###  ##################  ###  ######################E"),   # 20
    pad("###^^^###^^####^^###^^######^^###^^##########^^###^^##############^^###^^##################^^###^^######################"),   # 21
    pad("###^^^###^^####^^###^^######^^###^^##########^^###^^##############^^###^^##################^^###^^######################"),   # 22
    pad("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^"), # 23
]
mp4 = [
    {"x": 15, "y": 16, "w": 3, "axis": "x", "range": 3, "speed": 80, "phase": 0.0},
    {"x": 45, "y": 16, "w": 3, "axis": "x", "range": 4, "speed": 90, "phase": 0.5},
    {"x": 75, "y": 16, "w": 3, "axis": "x", "range": 3, "speed": 85, "phase": 1.0},
    {"x": 105, "y": 16, "w": 3, "axis": "x", "range": 4, "speed": 95, "phase": 0.0},
    {"x": 135, "y": 16, "w": 3, "axis": "x", "range": 3, "speed": 80, "phase": 0.5},
]
LEVELS.append(("level_04", "Echo Chamber", ascii4, [1, 19], [148, 20], mp4))

# ---------------------------------------------------------------------------
# LEVEL 5 — Chaos Run
# Fast-paced with lots of moving platforms over spike pits. Alternating
# platforms create a rhythm. Dense hazard fields below.
# ---------------------------------------------------------------------------
ascii5 = [
    pad(""),                                                                                                                        # 0
    pad(""),                                                                                                                        # 1
    pad(""),                                                                                                                        # 2
    pad(""),                                                                                                                        # 3
    pad(""),                                                                                                                        # 4
    pad(""),                                                                                                                        # 5
    pad(""),                                                                                                                        # 6
    pad(""),                                                                                                                        # 7
    pad(""),                                                                                                                        # 8
    pad(""),                                                                                                                        # 9
    pad(""),                                                                                                                        # 10
    pad(""),                                                                                                                        # 11
    pad(""),                                                                                                                        # 12
    pad(""),                                                                                                                        # 13
    pad(""),                                                                                                                        # 14
    pad(""),                                                                                                                        # 15
    pad(""),                                                                                                                        # 16
    pad(""),                                                                                                                        # 17
    pad(""),                                                                                                                        # 18
    pad(""),                                                                                                                        # 19
    pad("##  ###  ####  #####  ######  #######  ########  #########  ##########  ###########  ############  #############  ##E"),     # 20
    pad("##^^###^^####^^#####^^######^^#######^^########^^#########^^##########^^###########^^############^^#############^^##"),     # 21
    pad("##^^###^^####^^#####^^######^^#######^^########^^#########^^##########^^###########^^############^^#############^^##"),     # 22
    pad("##^^###^^####^^#####^^######^^#######^^########^^#########^^##########^^###########^^############^^#############^^##"),     # 23
]
mp5 = [
    {"x": 5, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 100, "phase": 0.0},
    {"x": 15, "y": 19, "w": 3, "axis": "y", "range": 3, "speed": 110, "phase": 0.5},
    {"x": 28, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 95, "phase": 1.0},
    {"x": 42, "y": 19, "w": 3, "axis": "y", "range": 3, "speed": 105, "phase": 0.0},
    {"x": 56, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 100, "phase": 1.5},
    {"x": 70, "y": 19, "w": 3, "axis": "y", "range": 3, "speed": 115, "phase": 0.3},
    {"x": 85, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 95, "phase": 0.8},
    {"x": 100, "y": 19, "w": 3, "axis": "y", "range": 3, "speed": 110, "phase": 1.0},
    {"x": 115, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 100, "phase": 0.0},
    {"x": 130, "y": 19, "w": 3, "axis": "y", "range": 3, "speed": 120, "phase": 0.5},
    {"x": 142, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 95, "phase": 1.2},
]
LEVELS.append(("level_05", "Chaos Run", ascii5, [1, 19], [147, 20], mp5))

# ---------------------------------------------------------------------------
# LEVEL 6 — Final Echo
# The ultimate challenge. Dense platforming with tight jumps, spike pits,
# moving platforms, and a final stretch with minimal safe ground.
# ---------------------------------------------------------------------------
ascii6 = [
    pad(""),                                                                                                                        # 0
    pad(""),                                                                                                                        # 1
    pad(""),                                                                                                                        # 2
    pad(""),                                                                                                                        # 3
    pad(""),                                                                                                                        # 4
    pad(""),                                                                                                                        # 5
    pad(""),                                                                                                                        # 6
    pad(""),                                                                                                                        # 7
    pad(""),                                                                                                                        # 8
    pad(""),                                                                                                                        # 9
    pad(""),                                                                                                                        # 10
    pad(""),                                                                                                                        # 11
    pad(""),                                                                                                                        # 12
    pad(""),                                                                                                                        # 13
    pad(""),                                                                                                                        # 14
    pad(""),                                                                                                                        # 15
    pad(""),                                                                                                                        # 16
    pad(""),                                                                                                                        # 17
    pad(""),                                                                                                                        # 18
    pad(""),                                                                                                                        # 19
    pad("## ### ### #### ### ##### ### ###### ### ######## ### ######### ### ############ ### ########### ### ###############E"),      # 20
    pad("##^###^###^####^###^#####^###^######^###^########^###^#########^###^############^###^###########^###^###############"),      # 21
    pad("##^###^###^####^###^#####^###^######^###^########^###^#########^###^############^###^###########^###^###############"),      # 22
    pad("##^###^###^####^###^#####^###^######^###^########^###^#########^###^############^###^###########^###^###############"),      # 23
]
mp6 = [
    {"x": 5, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 90, "phase": 0.0},
    {"x": 18, "y": 19, "w": 3, "axis": "y", "range": 3, "speed": 100, "phase": 0.5},
    {"x": 32, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 85, "phase": 1.0},
    {"x": 48, "y": 19, "w": 3, "axis": "y", "range": 3, "speed": 95, "phase": 0.0},
    {"x": 62, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 90, "phase": 0.5},
    {"x": 78, "y": 19, "w": 3, "axis": "y", "range": 3, "speed": 105, "phase": 1.0},
    {"x": 92, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 85, "phase": 0.0},
    {"x": 108, "y": 19, "w": 3, "axis": "y", "range": 3, "speed": 100, "phase": 0.5},
    {"x": 122, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 90, "phase": 1.0},
    {"x": 138, "y": 19, "w": 3, "axis": "y", "range": 2, "speed": 95, "phase": 0.0},
]
LEVELS.append(("level_06", "Final Echo", ascii6, [1, 19], [148, 20], mp6))


def build(ascii_rows):
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
        data = {
            "id": level_id,
            "name": name,
            "spawn": spawn,
            "exit": exit_tile,
            "tilemap": tilemap,
            "moving_platforms": mps,
        }
        ec, er = exit_tile
        if 0 <= er < len(tilemap) and 0 <= ec < width:
            tilemap[er][ec] = 2
        (out / f"{level_id}.json").write_text(
            json.dumps(data, separators=(",", ":")), encoding="utf-8")
        print(f"wrote {level_id}.json  ({width}x{len(tilemap)})")


if __name__ == "__main__":
    main()
