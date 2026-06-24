from src.save_system import SaveSystem

def test_ghost_round_trip(temp_save_system):
    test_id = "level_01"
    temp_save_system.clear_ghosts(test_id)
    frames = [{"x": 100 + i, "y": 400, "facing": 1, "on_ground": True} for i in range(60)]
    rec = SaveSystem.make_ghost_record(frames, completed=True, completion_time=5.0)
    temp_save_system.append_ghost(test_id, rec, best_time=5.0)
    loaded = temp_save_system.load_ghosts(test_id)
    assert len(loaded) == 1, f"expected 1 ghost, got {len(loaded)}"
    assert len(loaded[0]["frames"]) == 60
