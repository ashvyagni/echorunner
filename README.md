# EchoRunner

> **Race your own echoes. Survive yourself.**

A 2D platformer where every run you play becomes a collidable ghost obstacle in the next one.
Touch a ghost — you die. The better you get, the more the level fills with echoes of your own mistakes.

Built in **Python / Pygame** with **zero external asset files** — all sprites and sounds are synthesized at runtime. Ships as a double-clickable desktop app for Windows and macOS.

---

## Download ( doesnt work yet btw :> working on this )

| Platform | Link |
|----------|------|
| Windows  | [EchoRunner-Windows.zip](https://github.com/ashvyagni/echorunner/releases/latest) |
| macOS    | [EchoRunner-macOS.zip](https://github.com/ashvyagni/echorunner/releases/latest)   |

No Python required — just download, extract, and double-click.

---

## Run from Source

**Requirements:** Python 3.10+, pygame 2.6+

```bash
git clone https://github.com/ashvyagni/echorunner
cd echorunner
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

> No image or audio files are needed — sprites are drawn from shapes and
> sound effects are synthesized at runtime using pure math.

---

## How It Works

1. Complete (or die during) a level — your run is recorded frame-by-frame at 60 Hz.
2. On your next run, every past attempt replays simultaneously as a ghost (an **echo**).
3. Ghosts are collidable — touch one and your run resets immediately.
4. Death runs also become ghosts, so the level accumulates pressure over time.
5. Clear ghosts from the pause or level-select menu whenever it gets overwhelming.

---

## Controls

| Key | Action |
|-----|--------|
| A / ← | Move left |
| D / → | Move right |
| Space / ↑ / W | Jump (hold for higher, tap for a short hop) |
| Shift | Run (faster movement) |
| Esc | Pause |
| F11 | Toggle fullscreen |

Physics uses **coyote time** (grace period after leaving a ledge) and **jump buffering**
(jumps pressed just before landing still register) so controls feel responsive and forgiving.

---

## Features

### Core Mechanic
- **Ghost replay system** — every run is recorded and replayed as a collidable obstacle.
- **Frame-locked determinism** — 60 Hz fixed timestep means ghosts replay exactly as recorded, every time.
- **Persistent echoes** — ghosts and best times survive between sessions in human-readable JSON in `saves/`.
- **Up to 20 simultaneous ghosts** per level (oldest is dropped past the cap).

### Visual Feedback
- **Age-based ghost desaturation** — older ghosts fade toward gray so you can read "ancient mistake" vs. "just happened" at a glance.
- **Near-miss echo flash** — a bright outline pulses on any ghost your hitbox grazes without colliding.
- **Echo shimmer** — a subtle chromatic aberration effect on ghost sprites makes them feel otherworldly.
- **Parallax starfield** — three-layer background with twinkling stars and nebula wisps for visual depth.
- **Squash/stretch player animation**, afterimage trail, wall-slide, landing squash, and death spin.

### Audio (all synthesized in code — no audio files)
- **Near-miss whoosh** — distinct airy sound when you graze a ghost without dying.
- **Ghost despawn tone** — subtle ethereal fade when a ghost finishes its replay cycle.
- **Ghost proximity hum** — eerie low drone that activates as you approach active ghosts.
- Jump, land, death, complete, and footstep SFX with pitch variation.
- Procedural ambient music bed (A-minor pad).

### Levels (6 handcrafted)
| # | Name | Focus |
|---|------|-------|
| 1 | First Steps | Movement & jump arc |
| 2 | The Gap | Timing jumps around early ghosts |
| 3 | Rising Risk | Moving platforms + ghost navigation |
| 4 | The Maze | Multi-tier branching routes |
| 5 | Echo Vault | Dense platforms, ghost-crowded layout |
| 6 | Speed Run | Fast execution, moving platforms, par-time challenge |

### UI
- **Settings screen** — music toggle, SFX toggle, fullscreen toggle, screen-shake accessibility toggle.
- **Level select cards** with best time and echo count per level.
- Ghost proximity warning banner in the HUD.
- Screen fade transitions, time dilation on death/completion, particle bursts.

---

## Project Structure

```
EchoRunner/
├── main.py              # Entry point
├── requirements.txt     # pygame
├── build.spec           # PyInstaller spec (Windows)
├── build_mac.spec       # PyInstaller spec (macOS .app bundle)
├── src/
│   ├── game.py          # State machine + main loop (fixed timestep)
│   ├── player.py        # Player physics, input, frame recording
│   ├── ghost.py         # Ghost entity + GhostManager (replay/collision/near-miss)
│   ├── level.py         # Tilemap loader, moving platforms, rendering
│   ├── save_system.py   # JSON persistence (ghosts + progress)
│   ├── hud.py           # In-game timer / best / echo count
│   ├── camera.py        # Smooth-follow camera + smoothed screen shake
│   ├── background.py    # Three-layer parallax starfield
│   ├── particles.py     # Particle system (dust, sparkles, shimmer)
│   ├── sound.py         # Procedural SFX + music (graceful fallback)
│   ├── fonts.py         # Robust font loader (font → freetype → blocky fallback)
│   └── constants.py     # All tunable values in one place
├── levels/
│   └── level_0X.json    # Tilemaps + moving-platform data
├── saves/               # Auto-generated ghost & progress data (gitignored)
├── tests/               # pytest test suite
│   ├── test_physics.py
│   ├── test_ghost_save_load.py
│   ├── test_ghost_cap.py
│   ├── test_collision.py
│   └── test_fonts.py
└── tools/
    ├── build_levels.py  # Regenerates level JSON from ASCII art
    └── smoke_test.py    # Headless verification of all systems
```

---

## Testing

```bash
# Full test suite (pytest)
python -m pytest tests/ -v

# Headless smoke test (verifies all 6 levels, physics, ghost save/load)
python tools/smoke_test.py
```

CI runs the full suite on every push via `.github/workflows/test.yml`.

---

## Building Standalone Executables

```bash
pip install pyinstaller

# Windows (produces dist/EchoRunner/EchoRunner.exe)
pyinstaller build.spec

# macOS (produces dist/EchoRunner.app)
pyinstaller build_mac.spec
```

Tagged releases are built automatically via `.github/workflows/build.yml` and attached to GitHub Releases.

---

## Designing Levels

Levels are plain JSON. Edit `tools/build_levels.py` and re-run it to regenerate from ASCII art:

```
Legend: ' ' air  ·  '#' platform  ·  'E' exit  ·  '^' hazard (spikes)
Tile values: 0=air, 1=platform, 2=exit, 3=hazard
```

Moving platforms are declared in the `moving_platforms` list with `axis` (`"x"`/`"y"`),
`range` (tiles), `speed` (px/s), and `phase` (stagger offset).

---

## Technical Notes

- **Why procedural audio?** Keeps the project dependency-free and trivial to bundle into a single executable — no audio files to track, no licensing concerns.
- **Why a fixed timestep?** Ghost recordings are frame-locked at 60 Hz. Running physics on a fixed accumulator means replays are perfectly deterministic regardless of frame rate.
- **Screen shake** uses smoothed sinusoidal noise (not per-tick random angles) to avoid the "violent static" artifact common in naive trauma systems.
- **Ghost hitboxes** are slightly smaller than the visible body (`GHOST_HITBOX_SHRINK = 6px`) so near-misses feel fair rather than cheap.

---

## Known Limitations / Roadmap

The following are explicitly **out of scope** for the current version (intentional design decisions, not missing features):

| Feature | Status |
|---------|--------|
| Multiplayer / online ghost sharing | Out of scope |
| Mobile / touch support | Out of scope |
| Cloud save sync | Out of scope |
| Gamepad / controller support | Out of scope (groundwork in input layer) |
| Pixel-art sprite sheets | Placeholder rectangles by design (procedural aesthetic) |
| Echo point puzzle mechanic (dual-body pressure plates) | Planned for future level pack |

---

## Built With

- Python 3.10+
- Pygame 2.6

## License

MIT
