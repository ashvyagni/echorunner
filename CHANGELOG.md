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
