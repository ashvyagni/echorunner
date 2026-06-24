"""
main.py
=======
Entry point for EchoRunner.

Run from source:
    python main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make sure `src` is importable regardless of working directory / when frozen.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.game import Game  # noqa: E402


def main() -> None:
    game = Game()
    try:
        game.run()
    except KeyboardInterrupt:
        pass
    finally:
        game.quit()


if __name__ == "__main__":
    main()
