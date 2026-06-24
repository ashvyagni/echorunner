from src.ghost import GhostManager
from src.save_system import SaveSystem

def test_ghost_collision(temp_save_system):
    test_id = "level_01"
    frames = [{"x": 100, "y": 400, "facing": 1, "on_ground": True} for _ in range(60)]
    rec = SaveSystem.make_ghost_record(frames, completed=True, completion_time=5.0)
    temp_save_system.append_ghost(test_id, rec, best_time=5.0)

    gm = GhostManager(temp_save_system, test_id)
    gm.load()
    gm.start_replay()

    g0 = gm.ghosts[0]
    hit = gm.check_collision(g0.get_rect())
    assert hit, "expected collision when player overlaps ghost"
