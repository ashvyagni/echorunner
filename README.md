# EchoRunner

A 2D platformer where you race against ghost recordings of your own previous attempts.
**Every run you play becomes an obstacle in the next one.** Touch a ghost — you die.
The better you get, the more crowded the level becomes with your own echoes.

Built in **Python 3.10+ / Pygame**, with no external asset files (all sprites and
sounds are generated in code) so it packages cleanly into a single executable.

---

## How It Works

1. Complete (or die during) a level — your run is recorded frame-by-frame.
2. On your next run, every past attempt replays simultaneously as a ghost.
3. Ghosts are collidable — touch one and your run resets.
4. Death runs also become ghosts, so the level keeps getting harder.
5. Clear ghosts any time from the pause or level-select menu when it's too much.

---

## Installation

**Requirements:** Python 3.10 or newer.

```bash
git clone <your-repo-url> echorunner
cd echorunner
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

> The game is fully self-contained — there are no image or audio files to download.
> Sprites are drawn from shapes and sound effects are synthesized at runtime.

---

## Controls

| Key | Action |
|-----|--------|
| A / ← | Move left |
| D / → | Move right |
| Space / ↑ / W | Jump (hold for higher, tap for a short hop) |
| Shift | Run (optional — faster movement) |
| Esc | Pause |
| F11 | Toggle fullscreen |

Movement uses **coyote time** (grace period after leaving a ledge) and **jump
buffering** (jumps pressed just before landing still register), so controls feel
forgiving and responsive.

---

## Features

- **Ghost replay system** — every run is recorded and replayed as a collidable obstacle.
- **Persistent echoes** — ghosts and best times survive between sessions (human-readable JSON in `saves/`).
- **Up to 20 simultaneous ghosts** per level (oldest is dropped past the cap).
- **Local best-time leaderboard** per level.
- **5 handcrafted levels** with escalating difficulty:
  1. **First Steps** — basic movement and gentle jumps
  2. **The Gap** — pits with spikes beneath
  3. **Rising Risk** — moving platforms across a void
  4. **The Maze** — multi-tier routes, find the right path
  5. **Ghost Town** — dense platforms built to get crowded fast
- **Procedural audio** — jump, land, death, and complete jingles plus an ambient music bed, all synthesized in code (degrades silently if audio is unavailable).
- **Fixed-timestep simulation** (60 Hz) so ghost replays are deterministic and frame-locked to the original recording.
- **Forgiving hitboxes** — ghost collision boxes are slightly smaller than the visible body so near-misses feel fair.

---

## Project Structure

```
EchoRunner/
├── main.py              # Entry point
├── requirements.txt     # pygame
├── src/
│   ├── game.py          # State machine + main loop (fixed timestep)
│   ├── player.py        # Player physics, input, frame recording
│   ├── ghost.py         # Ghost entity + GhostManager (replay/collision)
│   ├── level.py         # Tilemap loader, moving platforms, rendering
│   ├── save_system.py   # JSON persistence (ghosts + progress)
│   ├── hud.py           # In-game timer / best / echo count
│   ├── camera.py        # Smooth-follow camera, clamped to level bounds
│   ├── background.py    # Parallax starfield backdrop
│   ├── sound.py         # Procedural SFX + music (graceful fallback)
│   ├── fonts.py         # Robust font loader (font → freetype → blocky)
│   └── constants.py     # All tunable values in one place
├── levels/
│   └── level_0X.json    # Tilemaps + moving-platform data
├── saves/               # Auto-generated ghost & progress data (gitignore this)
└── tools/
    ├── build_levels.py  # Regenerates level JSON from ASCII art
    └── smoke_test.py    # Headless verification of all systems
```

---

## Designing Your Own Levels

Levels are plain JSON. Edit `tools/build_levels.py` and re-run
`python tools/build_levels.py` to regenerate — editing ASCII art is far easier
than hand-typing nested arrays.

Legend: `' '` air · `#` platform · `E` exit · `^` hazard (spikes). Moving
platforms are declared in the `moving_platforms` list with `axis` (`"x"`/`"y"`),
`range` (in tiles), `speed`, and `phase`.

Tilemap values: `0` air, `1` platform, `2` exit, `3` hazard.

---

## Building a Standalone Executable (.exe)

EchoRunner is designed to freeze into a single distributable file with
[PyInstaller](https://pyinstaller.org/).

```bash
pip install pyinstaller
pyinstaller build.spec
```

The standalone executable appears in `dist/`. Because there are no external
asset files, nothing else needs bundling — the `levels/` directory is included
via the spec, and `saves/` is created next to the exe on first run.

---

## Testing

A headless smoke test verifies level loading, physics, ghost save/load
round-trips, the 20-ghost cap, and collision detection without opening a window:

```bash
python tools/smoke_test.py
```

---

## Built With

- Python 3.10+
- Pygame 2.6

## License

MIT
