"""
save_system.py
==============
Loads and writes the two JSON save files described in the GDD:

* saves/{level_id}_ghosts.json — recorded runs per level + best time
* saves/progress.json           — which levels are unlocked

All file IO is defensive: a missing or corrupt file is treated as "fresh game"
so first-time players and corrupted saves never crash the game.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List

from . import constants as C


class SaveSystem:
    """Human-readable JSON persistence for ghosts and progress."""

    def __init__(self, save_dir: Path | None = None) -> None:
        self.save_dir = save_dir or C.SAVES_DIR
        self.save_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------- paths
    def _ghost_path(self, level_id: str) -> Path:
        return self.save_dir / f"{level_id}_ghosts.json"

    def _progress_path(self) -> Path:
        return self.save_dir / "progress.json"

    # --------------------------------------------------------------- ghosts
    def load_ghosts(self, level_id: str) -> List[dict]:
        """Return the list of ghost dicts for a level ([] if none/corrupt)."""
        path = self._ghost_path(level_id)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("ghosts", [])
        except (json.JSONDecodeError, OSError):
            return []

    def save_ghosts(self, level_id: str, ghosts: List[dict],
                    best_time: float | None) -> None:
        """Overwrite the ghost file for a level."""
        path = self._ghost_path(level_id)
        payload = {
            "level_id": level_id,
            "ghosts": ghosts,
            "best_time": best_time,
        }
        path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")

    def append_ghost(self, level_id: str, ghost: dict,
                     best_time: float | None) -> List[dict]:
        """Add a ghost, enforce the MAX_GHOSTS cap (drop oldest), persist.

        Returns the resulting list of ghosts for convenience.
        """
        ghosts = self.load_ghosts(level_id)
        ghosts.append(ghost)
        if len(ghosts) > C.MAX_GHOSTS:
            ghosts = ghosts[-C.MAX_GHOSTS:]
        self.save_ghosts(level_id, ghosts, best_time)
        return ghosts

    def clear_ghosts(self, level_id: str) -> None:
        """Wipe all ghost recordings for a level (keeps best_time)."""
        path = self._ghost_path(level_id)
        best = self.get_best_time(level_id)
        self.save_ghosts(level_id, [], best)

    def get_best_time(self, level_id: str) -> float | None:
        path = self._ghost_path(level_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("best_time")
        except (json.JSONDecodeError, OSError):
            return None

    def set_best_time(self, level_id: str, best_time: float) -> None:
        ghosts = self.load_ghosts(level_id)
        self.save_ghosts(level_id, ghosts, best_time)

    def get_ghost_count(self, level_id: str) -> int:
        return len(self.load_ghosts(level_id))

    # --------------------------------------------------------------- progress
    def load_progress(self) -> dict:
        """Return unlocked-levels + best-times. Defaults to level 1 unlocked."""
        path = self._progress_path()
        default = {"unlocked_levels": 1, "best_times": {}}
        if not path.exists():
            return default
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data.setdefault("unlocked_levels", 1)
            data.setdefault("best_times", {})
            return data
        except (json.JSONDecodeError, OSError):
            return default

    def save_progress(self, progress: dict) -> None:
        path = self._progress_path()
        path.write_text(json.dumps(progress, separators=(",", ":")), encoding="utf-8")

    def unlock_next(self, current_index_1based: int) -> None:
        """Mark the next level as unlocked (level numbers are 1-based)."""
        progress = self.load_progress()
        if current_index_1based >= progress["unlocked_levels"]:
            progress["unlocked_levels"] = current_index_1based + 1
            self.save_progress(progress)

    def is_unlocked(self, level_index_1based: int) -> bool:
        return level_index_1based <= self.load_progress()["unlocked_levels"]

    # --------------------------------------------------------------- helpers
    @staticmethod
    def make_ghost_record(frames: List[dict], completed: bool,
                          completion_time: float | None) -> dict:
        """Build a ghost dict in the schema documented in the GDD."""
        return {
            "id": f"ghost_{int(time.time() * 1000)}",
            "timestamp": int(time.time()),
            "completed": completed,
            "completion_time": completion_time,
            "frames": frames,
        }
