from src import constants as C
from src.save_system import SaveSystem

def test_ghost_cap(temp_save_system):
    test_id = "level_01"
    for i in range(30):
        f = [{"x": i, "y": 0, "facing": 1, "on_ground": True}]
        temp_save_system.append_ghost(test_id, SaveSystem.make_ghost_record(f, True, 1.0), 1.0)
    n = len(temp_save_system.load_ghosts(test_id))
    assert n == C.MAX_GHOSTS, f"cap failed: {n} != {C.MAX_GHOSTS}"
