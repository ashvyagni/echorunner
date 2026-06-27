# EchoRunner — Revamp & Rebuild Brief

> **Audience:** AI coding agent (Claude Code, Cursor, Copilot, etc.) working directly in the
> `ashvyagni/echorunner` repository.
> **Mode:** Full portfolio-grade rebuild. Fix the root-caused bugs below FIRST, in order, then
> proceed to the rebuild scope. Do not skip the root-cause fixes to jump to new features — the
> existing bugs will undermine every new system built on top of them.
> **Repo:** https://github.com/ashvyagni/echorunner
> **Target:** Two real, double-clickable desktop apps (Windows `.exe`, macOS `.app`) — not
> "run `python main.py` in a terminal."

---

## 0. How to use this document

Work top to bottom. Each section is self-contained with file paths, exact root causes, and
acceptance criteria. After each section, run the smoke test (`tools/smoke_test.py`) and confirm
the acceptance criteria before moving to the next section. Commit after each section with a
descriptive message — this repo should end up with a commit history that reads like real
incremental engineering work, not one giant squash commit.

---

## 1. CRITICAL BUG FIXES (do these first, exactly as specified)

### 1.1 Screen shake is corrupted — "insane vibration," can't see what's happening

**File:** `src/camera.py`
**Root cause:** In `Camera.update()`, the shake angle is re-randomized **every physics tick**:

```python
ang = self._rng.uniform(0, 2 * math.pi)
self._shake_x = math.cos(ang) * shake * 25.0
self._shake_y = math.sin(ang) * shake * 25.0
```

At a 60Hz fixed timestep this recalculates a brand-new random direction roughly every 16ms with
no interpolation between samples. The eye perceives high-frequency, uncorrelated angular noise
as violent static, *regardless of the trauma magnitude* — this is why even the small landing
shake (`SHAKE_LAND = (1.5, 0.06)`) feels unreadable. The bug is in the **noise function**, not
the amplitude.

**Fix — replace single-sample angular shake with smoothed Perlin/value noise (offset, not
angle):**

```python
class Camera:
    def __init__(self) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self._trauma: float = 0.0
        self._shake_x: float = 0.0
        self._shake_y: float = 0.0
        self._shake_seed_x = random.uniform(0, 1000)
        self._shake_seed_y = random.uniform(0, 1000)
        self._shake_time = 0.0
        self._facing: int = 1

    def update(self, target_x, target_y, level_width, level_height, dt, facing=1):
        # ... existing lerp/deadzone/lookahead/clamp logic stays unchanged ...

        # ---- trauma / shake (FIXED: smooth noise, not per-tick random angle) ----
        self._trauma = max(0.0, self._trauma - C.SHAKE_TRAUMA_DECAY * dt)
        self._shake_time += dt
        shake = self._trauma ** 2
        # Sample smooth noise at two offset "channels" so x/y shake decorrelates
        # without ever jumping discontinuously between frames.
        freq = 18.0  # Hz-ish wobble rate — tune between 12-20, NOT 60+
        nx = math.sin(self._shake_time * freq + self._shake_seed_x)
        ny = math.sin(self._shake_time * freq * 1.3 + self._shake_seed_y)
        max_offset = 6.0  # px at full trauma — WAS implicitly 25px, far too strong
        self._shake_x = nx * shake * max_offset
        self._shake_y = ny * shake * max_offset
```

Also reduce shake constants in `src/constants.py` — the current values were tuned against the
broken noise function and will feel too strong even after the fix:

```python
SHAKE_DEATH    = (5.0, 0.30)   # was (9.0, 0.35)
SHAKE_LAND     = (0.6, 0.05)   # was (1.5, 0.06) — landing should be barely perceptible
SHAKE_COMPLETE = (2.5, 0.18)   # was (4.0, 0.18)
```

**Additionally:** gate landing shake so it only fires on *hard* landings, not every single
touch-down. In `src/game.py` where `self.camera.add_shake(C.SHAKE_LAND[0])` is called, check
fall speed before landing and scale (or skip) the shake:

```python
if self.player.just_landed:
    self.sound.play("land")
    fall_speed = abs(self.player.last_fall_vy)  # capture vy just before landing in player.py
    if fall_speed > 250:  # only shake on a real drop, not a small hop
        intensity = min(C.SHAKE_LAND[0] * (fall_speed / 400), C.SHAKE_LAND[0] * 1.5)
        self.camera.add_shake(intensity)
    self.particles.dust_landing(self.player.rect.centerx, self.player.rect.bottom)
```

**Acceptance criteria:**
- Landing from a normal jump produces shake so subtle it's barely noticeable.
- Landing from a big fall produces a soft, smooth bump — never a flicker or jitter.
- Death shake is noticeable but settles within ~0.3s with a smooth decay curve, not jagged noise.
- Record a 10-second gameplay clip with repeated jumps/landings and confirm the camera offset
  never visibly "vibrates" or flickers frame to frame.

---

### 1.2 HUD/menu text renders as garbled `////` characters

**File:** `src/fonts.py`
**Root cause:** The blocky bitmap font fallback builds its glyph table with a broken `zip()`:

```python
_GLYPHS = {ch: _g for ch, _g in zip(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 :.!-+/%'",
    [0b01110, 0b10001, 0b10011, ...]  # flat list of 322 individual row-ints
)}
```

`zip()` pairs each character 1:1 with a single integer from the flat list, instead of grouping
the list into chunks of 7 (one glyph = 7 row-ints) first. The result: `_GLYPHS['A']` is bound to
`0b01110` alone (just one row, not the full glyph), and every subsequent character is bound to
the *next single int in the flat list* — completely misaligned from its intended glyph. Digits
and punctuation (used constantly in the HUD timer string `"0:18.42"`) end up mapped to whatever
row-fragment happens to land on them, which is why you're seeing repeating slash-like garbage —
the `/` glyph's row pattern (and other malformed single-row values) leak into completely
unrelated characters.

This path is normally dormant — it only activates when **both** `pygame.font` and
`pygame._freetype` fail to initialize. That this is firing on your machine means your installed
pygame/SDL2_ttf combination is failing silently. Fix both the immediate bug and the silent
fallback.

**Fix 1 — group the flat list into rows-of-7 before zipping:**

```python
_RAW_ROWS = [
    0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110,  # A
    0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110,  # B
    # ... (keep all existing rows exactly as they are, just stop treating
    #      this as a flat list to zip against individual characters)
]
_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 :.!-+/%'"
assert len(_RAW_ROWS) == len(_CHARS) * 7, (
    f"Glyph table misaligned: {len(_RAW_ROWS)} rows for {len(_CHARS)} chars "
    f"(expected {len(_CHARS) * 7})"
)
_GLYPHS = {
    ch: _RAW_ROWS[i * 7:(i + 1) * 7]
    for i, ch in enumerate(_CHARS)
}
```

And update `_blocky_render` to consume a *list of 7 row-ints* per glyph instead of a single packed
int:

```python
def _blocky_render(text: str, size: int, color) -> pygame.Surface:
    scale = max(1, size // 8)
    gw, gh = 5, 7
    w = max(1, (len(text) * 6 - 1)) * scale
    h = gh * scale
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for i, ch in enumerate(text.upper()):
        rows = _GLYPHS.get(ch, [0] * 7)
        for row in range(gh):
            bits = rows[row] & 0b11111
            for col in range(gw):
                if bits & (1 << (gw - 1 - col)):
                    px = (i * 6 + col) * scale
                    py = row * scale
                    surf.fill(color, (px, py, scale, scale))
    return surf
```

Add a unit test in `tools/smoke_test.py` that renders every character in `_CHARS` through
`_blocky_render` and asserts the resulting surface is non-empty (catches future glyph-table
regressions automatically).

**Fix 2 — stop silently swallowing the real font failure.** Right now `_pick_backend()` catches
every exception from `pygame.font` and `pygame._freetype` with a bare `except Exception: pass`
and falls through with no diagnostic. Add a one-time warning so this is debuggable instead of a
silent mystery next time:

```python
import logging
log = logging.getLogger("echorunner.fonts")

def _pick_backend(size: int, bold: bool):
    try:
        f = pygame.font
        if f.get_init() or _try_font_init():
            return f.SysFont("arial,helvetica,verdana", size, bold=bold), "font"
    except Exception as e:
        log.warning("pygame.font backend failed: %s", e)

    try:
        ft = importlib.import_module("pygame._freetype")
        if not ft.get_init():
            ft.init()
        fnt = ft.Font(None, size)
        fnt.style = ft.STYLE_NORMAL if not bold else ft.STYLE_BOLD
        return fnt, "freetype"
    except Exception as e:
        log.warning("pygame._freetype backend failed: %s", e)

    log.warning("Both font backends unavailable — using blocky bitmap fallback. "
                "Check your pygame/SDL2_ttf installation.")
    return None, "blocky"
```

**Fix 3 (recommended over the bitmap fallback entirely):** Bundle a real open-source pixel font
(e.g. a license-clean font like "Press Start 2P" or "Pixeloid Sans," both free for commercial
use — verify license before bundling) as a `.ttf` in `assets/fonts/` and load it directly via
`pygame.font.Font(path, size)` as the **primary** path, ahead of `SysFont`. This removes
dependency on whatever fonts happen to be installed on the user's OS entirely, which is the
actual long-term fix — system font availability should never be a single point of failure for a
shipped game.

**Acceptance criteria:**
- All HUD text (timer, echo count, best time), menu text, and pause/complete screens render
  legible characters with correct kerning — verified visually on a machine where `pygame.font`
  is intentionally disabled (to force the blocky path) and on a normal machine.
- `tools/smoke_test.py` includes a glyph-table integrity assertion that fails loudly if the table
  is ever misaligned again.
- No more silent exception swallowing in the font backend selector — failures log a warning.

---

### 1.3 Game only runs via `python main.py` in a terminal, not as a real app

**Root cause:** `build.spec` already exists and is correctly configured for PyInstaller, but it
has never actually been built into a distributable artifact, and there's no macOS-specific spec
or CI to produce one.

**Fix — produce real installers for both platforms:**

1. **Windows:** Run `pyinstaller build.spec` on a Windows machine/runner to produce
   `dist/EchoRunner/EchoRunner.exe`. Add a proper `.ico` icon (see Section 3.7 — Branding) and
   wire it into `build.spec`'s `icon=` parameter (currently `None`).
2. **macOS:** PyInstaller's `.spec` format differs slightly for `.app` bundles. Add a second
   spec, `build_mac.spec`, using `BUNDLE()`:
   ```python
   app = BUNDLE(
       coll,
       name='EchoRunner.app',
       icon='assets/icon.icns',
       bundle_identifier='com.ashvyagni.echorunner',
       info_plist={
           'NSHighResolutionCapable': 'True',
           'CFBundleShortVersionString': '2.0.0',
       },
   )
   ```
3. **Automate both builds with GitHub Actions** so every tagged release produces downloadable
   artifacts without manual building. Add `.github/workflows/build.yml`:
   ```yaml
   name: Build Releases
   on:
     push:
       tags: ['v*']
   jobs:
     build-windows:
       runs-on: windows-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with: { python-version: '3.11' }
         - run: pip install -r requirements.txt pyinstaller
         - run: pyinstaller build.spec
         - uses: actions/upload-artifact@v4
           with: { name: EchoRunner-Windows, path: dist/EchoRunner }
     build-macos:
       runs-on: macos-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with: { python-version: '3.11' }
         - run: pip install -r requirements.txt pyinstaller
         - run: pyinstaller build_mac.spec
         - uses: actions/upload-artifact@v4
           with: { name: EchoRunner-macOS, path: dist/EchoRunner.app }
   ```
4. Attach both build artifacts to a GitHub Release on tag push (`softprops/action-gh-release` or
   similar) so `Releases` on the repo page has real downloadable binaries — right now it says
   "No releases published."

**Acceptance criteria:**
- A user with zero Python installed can download a `.zip`/`.dmg` from GitHub Releases, extract,
  and double-click to play on both Windows and macOS.
- `saves/` is created next to the executable on first run (already handled per the existing
  spec comments — verify this still works in the built artifact, not just `python main.py`).
- App has a real icon, not the default Python/Tk icon, in the dock/taskbar and window title bar.

---

## 2. Why this rebuild matters (context for the agent)

This project is going into a developer's GitHub as a portfolio piece. The core mechanic — your
own past runs become collidable ghost obstacles — is genuinely original and worth showcasing,
but a portfolio reviewer will bounce off broken juice/feel and bugs in the first 30 seconds
regardless of how clever the underlying system is. Treat this rebuild as if a senior engineer
is doing a full pass before a 1.0 release: correctness first, then depth, then presentation.

---

## 3. Full Rebuild Scope

### 3.1 Mechanical depth — give the ghost system more to say

The current ghost system (record → replay → AABB collision → death) is solid as an MVP but is a
single idea repeated five times. Add mechanical variety that *uses* the ghost concept instead of
just scaling ghost count:

- **Ghost "echo points":** Certain tiles/pickups can only be activated by *two bodies standing on
  them simultaneously* — meaning the player must position a ghost (from a deliberate prior run)
  on one plate while standing on another. This turns ghosts from pure hazards into puzzle tools,
  which is a much stronger pitch than "more ghosts = harder."
- **Ghost decay visual storytelling:** Older ghosts should visually fade in saturation/opacity
  over many runs (not just alpha — desaturate toward gray) so the player can intuit "this is an
  ancient mistake" vs. "this just happened," reinforcing the core theme (your past haunting you)
  rather than treating ghosts as undifferentiated clutter.
- **One-shot "Echo Save" mechanic for level 6 (bonus/speedrun level):** Let the player manually
  snapshot a ghost mid-run (a deliberate, single recorded loop they can study), separate from the
  automatic per-attempt recording — useful for the speedrun-optimization level called out in the
  original design doc.
- **Near-miss tension beat:** When the player's hitbox passes within N pixels of a ghost without
  colliding, trigger a subtle audio "whoosh" + a 1-frame ghost outline flash. Right now a near
  miss is mechanically identical to "nothing happened," which wastes the tension the concept is
  built around.

### 3.2 Level design — replace flat escalation with actual teaching moments

Current levels scale "ghost density" linearly (0→20) with no new spatial ideas. Redesign the
level set so each level teaches one new *spatial* lesson, not just "more obstacles":

| Level | New teaching focus | Notes |
|---|---|---|
| 1 — First Steps | Movement & jump arc, zero ghosts | Keep as-is, it's correctly scoped |
| 2 — The Gap | Timing jumps around 1-2 of your own ghosts | Fewer, more deliberate ghost placements vs. current density-only scaling |
| 3 — Rising Risk | Moving platforms + ghosts that ALSO ride moving platforms (currently ghosts likely ignore platform deltas during replay — verify and fix if so) | This is a correctness check, not just design |
| 4 — The Maze | Branching paths where wrong branches accumulate ghosts faster — punishes exploration in a way that's legible, not punishing | |
| 5 — Echo Vault (rename from "Ghost Town") | Introduces the "echo point" puzzle mechanic from 3.1 | |
| 6 — Speed Run (bonus) | Manual echo-save mechanic, tight par time, leaderboard-focused | |

**Verify before redesigning:** check `src/level.py` and `src/ghost.py` for whether ghost replay
correctly re-applies the moving-platform delta that was active *during the original recording*
(not the platform's *current* position) — if ghosts are recorded as raw world coordinates without
re-deriving platform-relative offsets, replaying them on a level with moving platforms will look
subtly wrong (ghost foot position drifts off the platform it was "standing" on). This is worth a
dedicated correctness pass given level 3 already uses moving platforms.

### 3.3 Visual presentation — move off placeholder rectangles

The doc specifies "28x28 filled rect (placeholder for sprite)" as final art. For a portfolio
piece, replace this:

- Commission or generate a small pixel-art spritesheet for the player: idle, run (4-6 frames),
  jump, fall, death poses. 32x32 grid per the original spec.
- Ghosts should reuse the player spritesheet (per original design) but the fix in 3.1 (desaturate
  over age) needs the sprite to support a grayscale/tint shader pass — confirm
  `pygame.Surface` tinting approach handles both the existing color-cycling AND the new
  age-based desaturation without conflicting.
- Replace flat-color platform/exit tiles with a small tileset: at minimum platform-top edge
  variants (left-cap, middle, right-cap) so platforms don't look like undifferentiated gray bars.
- Background: the repo already has `src/background.py` for a parallax starfield — confirm it's
  actually wired into the render loop for every level (not just menu screens) and extend it with
  2-3 parallax layers for depth.
- Add a subtle vignette + chromatic "echo shimmer" shader effect (simple alpha-blended overlay,
  no need for real shaders) specifically on ghost sprites to make them read as otherworldly
  rather than just "transparent copy of the player."

### 3.4 UI/UX — make menus feel designed, not default

- Main menu, level select, pause, and level-complete screens should share one consistent visual
  language (typography scale, button states: idle/hover/pressed, consistent spacing grid) —
  audit `src/hud.py` and wherever menu screens are drawn in `src/game.py` for consistency.
- Level select cards should show a small thumbnail/icon per level, not just text — even a simple
  generated silhouette of the level's tilemap shape is enough to make the screen feel finished.
- Add basic input-method-aware prompts (if using keyboard, show "Press SPACE"; this groundwork
  also makes future gamepad support — currently explicitly out of scope — easy to add later
  without a UI rewrite).
- Add a settings screen: music/SFX volume sliders, fullscreen toggle (F11 currently undocumented
  in-game), and a "reduce screen shake" accessibility toggle — directly relevant given the shake
  bug just fixed; give players control over it going forward regardless of how well-tuned the
  default ends up being.

### 3.5 Audio — verify and extend the procedural audio system

`src/sound.py` already synthesizes audio in code rather than shipping asset files, which is a
nice technical detail worth highlighting in the README (keep this). Extend it:

- Add a distinct, subtle audio cue specifically for "a ghost just despawned near you" vs. "ghost
  collision death" — right now these are likely sonically similar, which muddies feedback.
- Tie music intensity/layering to ghost density per the original "Ghost Town gets crowded" theme
  — e.g., add a low synthesized drone layer that increases in volume as ghost count rises, so the
  audio reinforces the escalating-tension pitch even before the player notices visually.

### 3.6 Code quality & repo hygiene (portfolio signal)

A GitHub reviewer skims structure before code. Bring the repo up to "A-class" signal:

- **Tests:** `tools/smoke_test.py` exists — expand it into a proper `tests/` directory using
  `pytest`, with separate test modules for physics, ghost save/load round-trips, the 20-ghost cap,
  collision detection, and the new glyph-table integrity check from 1.2. Add a `pytest.ini` or
  `pyproject.toml` test config.
- **CI:** Add `.github/workflows/test.yml` running the test suite on every push/PR (separate from
  the release-build workflow in 1.3) so the README can show a passing CI badge.
- **Linting/formatting:** Add `ruff` (fast, modern) config and run it across `src/`. Fix whatever
  it flags. Add a pre-commit config so this stays enforced.
- **Type hints:** The existing code already uses `from __future__ import annotations` and partial
  type hints (good sign) — finish the job across every module in `src/` so `mypy --strict` (or at
  least non-strict) passes cleanly. Add a `mypy.ini`.
- **Docstrings:** Original spec calls for docstrings on every class/public method — audit and fill
  gaps, especially in `game.py` which is the largest file (32K) and most likely to have drifted.
- **CHANGELOG.md:** Add one, and backfill a "2.0.0 — Full Revamp" entry summarizing the bug fixes
  and new systems from this brief. This single file does more to signal active, careful
  maintenance than almost anything else in a portfolio repo.
- **Remove dead weight:** `saves/` should never be committed with actual save data in it — verify
  `.gitignore` covers `saves/*.json` (keep the directory via `.gitkeep` if needed) so cloning the
  repo doesn't hand new players someone else's ghosts.

### 3.7 Branding & README polish

- Design a small logo/icon (used for the `.exe`/`.app` icon from Section 1.3 and the README
  header) — simple geometric mark playing on the "echo/ghost" concept works well at small sizes.
- Replace the README's `![gameplay screenshot placeholder]` with real, current screenshots/GIFs:
  one of normal gameplay, one specifically showing several ghosts replaying at once (the
  signature visual of the whole game — this should be the hero image), and one of the new
  echo-point puzzle mechanic from 3.1.
- Add a short (15-30s) GIF or embedded video link to the top of the README — this is the single
  highest-leverage thing for making a game repo feel "real" to a visitor in the first 3 seconds.
- Update install instructions to lead with the new prebuilt binaries from Section 1.3
  ("Download EchoRunner for Windows/macOS — no Python required") and move the
  `pip install -r requirements.txt` path to a "Run from source" section below it for
  contributors/developers, not as the primary install path for players.
- Add a "Known limitations / roadmap" section listing the explicit out-of-scope items already
  defined in the original PRD (multiplayer, mobile, cloud saves, gamepad) — this reads as
  intentional scoping rather than missing features when stated upfront.

---

## 4. Suggested execution order

1. Section 1 (all three critical bugs) — these block everything else from being evaluated fairly.
2. Section 3.6 (tests + CI) — get a safety net in place before touching mechanics/art, so the
   rebuild doesn't silently regress the working ghost/save/collision systems.
3. Section 3.2 correctness check (ghost replay vs. moving platforms) — small, isolated, high risk
   if skipped.
4. Section 3.1 (mechanical depth) and 3.2 (level redesign) together, since new levels need the
   new mechanics to showcase them.
5. Section 3.3–3.5 (visual/UI/audio polish) — easiest to iterate once mechanics are locked.
6. Section 1.3 (real builds) + 3.7 (branding/README) last, once there's something worth screenshotting.

---

## 5. Definition of done

- [ ] Screen shake is smooth and subtle; no flicker on landing, soft decay on death.
- [ ] All in-game text renders correctly under both the normal font path and a forced fallback.
- [ ] Windows `.exe` and macOS `.app` builds exist, are attached to a GitHub Release, and run
      with zero Python/pygame installed on the target machine.
- [ ] Ghost replay correctly tracks moving platforms during playback.
- [ ] At least one new mechanic (echo points) is implemented and used in a real level.
- [ ] Player/ghost sprites are real pixel art, not placeholder rectangles.
- [ ] Test suite + CI badge are green in the README.
- [ ] README has real screenshots/GIF, updated install instructions, and a roadmap section.
