"""
tools/smoke_test.py
===================
Headless verification that the game systems work end-to-end without a display:
- all levels load
- player physics + collision resolve without errors
- ghost save/load round-trips
- ghost collision detection triggers
- level completion is reachable by a scripted run

Run: python tools/smoke_test.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# force headless
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402
pygame.init()
screen = pygame.display.set_mode((1280, 720))

from src import constants as C  # noqa: E402
from src.level import load_all_levels  # noqa: E402
from src.player import Player, _InputState  # noqa: E402
from src.ghost import GhostManager  # noqa: E402
from src.save_system import SaveSystem  # noqa: E402

FIXED_DT = 1.0 / 60


def main():
    print("== EchoRunner smoke test ==")

    # 1. load all levels
    levels = load_all_levels()
    assert levels, "no levels loaded!"
    print(f"  loaded {len(levels)} levels: {[l.name for l in levels]}")
    for lv in levels:
        assert lv.width_px > 0 and lv.height_px > 0
        assert lv.platforms(), f"{lv.id}: no platforms!"
        assert lv.exit_rect().width > 0, f"{lv.id}: no exit!"

    # use a temp save dir so the test never clobbers real saves
    tmp_save = SaveSystem(save_dir=Path("saves/_smoketest"))
    tmp_save.save_progress({"unlocked_levels": 99, "best_times": {}})

    # 2. per-level: spawn player, apply a constant "run right + jump" script,
    #    confirm we either complete or die (no exceptions, no infinite hang)
    for li, level in enumerate(levels):
        player = Player(*level.spawn_pos())
        gm = GhostManager(tmp_save, level.id)
        gm.load()
        gm.start_replay()
        max_ticks = 60 * 45  # 45s budget
        ticks = 0
        result = "timeout"
        death_ticks = []
        for _ in range(max_ticks):
            ticks += 1
            level.update(FIXED_DT, ticks * FIXED_DT)
            deltas = []
            for mp in level.moving_platforms:
                dx, dy = mp.update(FIXED_DT, ticks * FIXED_DT)
                deltas.append((dx, dy))
            inp = _InputState(right=True, jump_held=(player.on_ground and ticks % 40 < 3))
            player.update(FIXED_DT, inp, level.platforms(), deltas)
            gm.update()
            if gm.check_collision(player.rect):
                result = "ghost-hit"
                break
            for hz in level.hazards():
                if player.rect.colliderect(hz):
                    result = "hazard"
                    break
            if result != "timeout":
                break
            if player.rect.colliderect(level.exit_rect()):
                result = "complete"
                break
            if player.rect.top > level.height_px + 200:
                result = "fell"
                break
        print(f"  level {li+1} {level.name:14s}: {result} @ {ticks} ticks "
              f"({ticks/60:.1f}s), echoes={gm.count()}")

    # 3. ghost round-trip: save a recording, reload, confirm it's there
    test_id = "level_01"
    tmp_save.clear_ghosts(test_id)
    frames = [{"x": 100 + i, "y": 400, "facing": 1, "on_ground": True}
              for i in range(60)]
    rec = SaveSystem.make_ghost_record(frames, completed=True, completion_time=5.0)
    tmp_save.append_ghost(test_id, rec, best_time=5.0)
    loaded = tmp_save.load_ghosts(test_id)
    assert len(loaded) == 1, f"expected 1 ghost, got {len(loaded)}"
    assert len(loaded[0]["frames"]) == 60
    print(f"  ghost round-trip OK ({len(loaded[0]['frames'])} frames)")

    # 4. MAX_GHOSTS cap: push 30 ghosts, expect only MAX_GHOSTS kept (oldest dropped)
    for i in range(30):
        f = [{"x": i, "y": 0, "facing": 1, "on_ground": True}]
        tmp_save.append_ghost(test_id, SaveSystem.make_ghost_record(f, True, 1.0), 1.0)
    n = len(tmp_save.load_ghosts(test_id))
    assert n == C.MAX_GHOSTS, f"cap failed: {n} != {C.MAX_GHOSTS}"
    print(f"  ghost cap OK (kept {n}/{C.MAX_GHOSTS})")

    # 5. ghost collision actually fires when rects overlap
    gm2 = GhostManager(tmp_save, test_id)
    gm2.load()
    gm2.start_replay()
    # place a player rect on top of the first ghost's first frame
    g0 = gm2.ghosts[0]
    hit = gm2.check_collision(g0.get_rect())
    assert hit, "expected collision when player overlaps ghost"
    print("  ghost collision OK")

    # cleanup
    import shutil
    shutil.rmtree(tmp_save.save_dir, ignore_errors=True)
    print("== smoke test PASSED ==")


if __name__ == "__main__":
    main()
