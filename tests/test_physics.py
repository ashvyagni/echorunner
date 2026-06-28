from src import constants as C
from src.level import load_all_levels
from src.player import Player, _InputState
from src.ghost import GhostManager

FIXED_DT = 1.0 / 60

def test_physics_smoke(temp_save_system):
    levels = load_all_levels()
    assert levels, "no levels loaded!"
    for level in levels:
        assert level.width_px > 0 and level.height_px > 0
        assert level.platforms(), f"{level.id}: no platforms!"
        assert level.exit_rect().width > 0, f"{level.id}: no exit!"

        player = Player(*level.spawn_pos())
        gm = GhostManager(temp_save_system, level.id)
        gm.load()
        gm.start_replay()
        max_ticks = 60 * 120  # 120s budget (larger levels need more time)
        ticks = 0
        result = "timeout"
        for _ in range(max_ticks):
            ticks += 1
            level.update(FIXED_DT, ticks * FIXED_DT)
            deltas = []
            for mp in level.moving_platforms:
                dx, dy = mp.update(FIXED_DT, ticks * FIXED_DT)
                deltas.append((dx, dy))
            inp = _InputState(right=True, jump_held=(player.on_ground and ticks % 40 < 3))
            player.update(FIXED_DT, inp, level.platforms(), deltas)
            gm.update(FIXED_DT)
            if gm.check_collision(player.rect):
                result = "ghost-hit"
                break
            for hz in level.hazards():
                if player.rect.colliderect(hz):
                    result = "hazard"
                    break
            if result != "timeout":
                break
            # Generous exit check matching game.py
            exit_check = level.exit_rect().inflate(0, C.PLAYER_SIZE * 2)
            if player.rect.colliderect(exit_check):
                result = "complete"
                break
            if player.rect.top > level.height_px + 200:
                result = "fell"
                break
        assert result in ("complete", "hazard", "fell", "ghost-hit"), f"Level {level.id} timed out"
