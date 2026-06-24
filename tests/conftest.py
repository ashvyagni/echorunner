import os
import sys
from pathlib import Path
import pytest
import shutil

# force headless
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.save_system import SaveSystem

import pygame
pygame.init()
pygame.display.set_mode((1280, 720))

@pytest.fixture
def temp_save_system(tmp_path):
    save_dir = tmp_path / "saves"
    save = SaveSystem(save_dir=save_dir)
    save.save_progress({"unlocked_levels": 99, "best_times": {}})
    yield save
    shutil.rmtree(save_dir, ignore_errors=True)
