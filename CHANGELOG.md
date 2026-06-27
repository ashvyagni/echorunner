# Changelog

All notable changes to EchoRunner will be documented in this file.

## [2.0.0] - Full Revamp

### Fixed
- **Screen Shake Corruption:** Fixed the jagged, high-frequency camera jitter on landing and death. Replaced with smooth, noise-based deterministic offsets. Shake intensity is now gated by actual landing velocity.
- **HUD Font Rendering:** Fixed a misalignment in the blocky fallback font glyph table that caused text (like digits and symbols) to render as garbage. Added fallback warnings.
- **Build Configurations:** Fixed PyInstaller bundling. Added a functional `build_mac.spec` for `.app` builds alongside the existing Windows `.spec`.

### Added
- **Tests & CI Setup:** Fully ported existing headless smoke tests into a `pytest` suite. Added `.github/workflows/test.yml` to run tests on all PRs/pushes, and `build.yml` for release builds.
- **Linting & Formatting:** Introduced `ruff` for fast linting/formatting and `mypy` for static type checking across the entire repository. Added `pre-commit` hooks.
- **Ghost Age-Based Desaturation:** Older ghosts now progressively fade toward gray, so players can visually distinguish "ancient mistake" from "just happened" at a glance.
- **Near-Miss Detection:** When the player's hitbox passes within 60px of a ghost without colliding, the ghost flashes a bright white outline and a distinct airy "whoosh" SFX plays. Near-miss events have a per-ghost 0.5s cooldown to prevent spam.
- **Ghost Despawn Audio:** A soft, ethereal twin-tone plays when a ghost finishes its replay cycle and disappears — clearly distinguishable from the death/collision sound.
- **Echo Shimmer (chromatic aberration):** Ghost sprites render with a subtle red/blue chromatic offset overlay, making them feel otherworldly rather than just transparent copies.
- **Three-Layer Parallax Background:** The starfield now has far/mid/near star layers plus dim nebula wisps, all with independent scroll speeds and twinkling. The background updates every frame (star twinkle uses a sine-wave timer).
- **Settings Screen:** Accessible from the main menu and pause screen. Toggles for Music, Sound FX, Fullscreen, and Screen Shake (accessibility). Animated selection cursor and ON/OFF indicators.
- **Near-Miss Whoosh SFX:** Procedurally synthesized airy sweep (noise + high-frequency tone sweep) synthesized in `sound.py`.
- **Ghost Despawn SFX:** Procedurally synthesized soft twin-tone fade synthesized in `sound.py`.
- **Level 5 renamed:** "Ghost Town" → "Echo Vault" — better reflects the design intent.
- **Level 6 — Speed Run:** New bonus level with tight platforms, hazard gaps, and four moving platforms of varying speed and phase. Designed for high-tempo play and replay optimization.
- **README overhaul:** Download links, full feature table, technical notes, known limitations / roadmap section, and developer setup instructions.
