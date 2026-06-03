# Changelog

All notable changes to psysuals are documented here.
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

## [3.2.0] — 2026-06-03

### Changed
- **Aurora Effect** — tapered ribbon boundaries and outer glows to zero at screen edges, eliminating straight vertical line cut-offs for a more organic look.
- **Lattice Effect** — added resolution-aware, multi-layered soft glows to nodes and beams, dynamically scaling their sizes and properties for large/4K displays.
- **Lattice Dynamic Resizing** — implemented real-time render surface and node layout adjustments during screen/window size changes.
- **Lattice Robustness** — added safe FFT slicing to prevent index/range errors.

## [3.1.0] — 2026-04-21

### Added
- **Reworked Lattice** — complete visual overhaul with a dynamic rotozoom feedback tunnel
- **Installation Guide** — added step-by-step setup and hardware acceleration instructions to README

### Changed
- **Massive FPS Boost** — optimized Butterflies, Vortex, and FlowField (now handling 8,000 particles smoothly)
- **Smoother Lissajous** — dampened rotation and beat response for a more stable visual flow
- **Improved Exit Responsiveness** — app now terminates instantly and reliably with a single `Esc` or `Q` keypress

### Fixed
- **Plasma GL** — fixed blank screen issue by ensuring the GL backbuffer is cleared correctly each frame
- **Dependency Import** — resolved `NameError: name 'pygame' is not defined` in `GLRenderer`
- **AudioEngine Bug** — restored the missing `get_audio` method to resolve application startup crashes

### Added
- **Super-Duper Massive Release** — Psysuals v3 is here!
- **Modular OO Architecture** — complete refactor of `psysualizer.py` into specialized classes (`AudioEngine`, `DisplayManager`, `UIManager`, `VisualizerApp`)
- **Performance Benchmarks** — added `benchmarks.py` to measure and compare effect frame rates (CPU vs GPU)
- **Regression Testing** — integrated `core/regression_tester.py` into `smoke_test.py` to guard effect contract and registry order

### Changed
- **Enhanced Beat Detection** — improved spectral flux normalization and constrained BPM range for higher stability
- **Hardened Validation** — robust display geometry and audio device validation with safe fallback paths
- **Relaxed Dependencies** — updated `requirements.txt` to use minimum version ranges instead of fixed pins

### Fixed
- **Improved Process Termination** — app and all span-mode children now exit immediately and reliably on `Esc` or `Q`
- **Saved Display Selection** — `display_idx` is now restored from settings on startup unless `--display N` overrides it

---

## [2.16.0] — 2026-04-21

### Added
- **Unified ModernGL architecture** — `psysualizer.py` now supports both CPU (Pygame) and GPU (ModernGL) rendering via the `--gl` flag
- **GL/UI Compositing** — UI elements (HUD, pane, picker) are now rendered as textures and blitted over OpenGL content in GL mode
- **`smoke_test.py`** — automated instantiation and import check for all 18 effects
- **`requirements-gl.txt`** — optional GL dependency set for the ModernGL path

### Changed
- **Effect Contract** — all effects now inherit from a base `Effect` class and accept an optional `renderer`
- **Span mode** — the primary instance now spawns one child process for every non-primary monitor
- **GL shader assets** — `gl_renderer.py` now owns loading the tracked GLSL files under `effects/shaders/`
- **Plasma** — now uses `PlasmaGL` by default, providing hardware acceleration with a transparent CPU fallback

### Fixed
- **No-input startup and device switching** — failure to open the saved or default input device now degrades to a live silent mode instead of aborting the app
- **Background effect rebuild on display changes** — fullscreen toggles now recreate the background visualiser as well as the foreground one
- **Span-child recursion** — child windows launched by span mode no longer recursively enter span mode themselves

### Removed
- **`psysualizer_gl.py`** — redundant experimental entry point removed in favour of the unified `--gl` flag
- **Dead Particles module** — removed the unregistered `effects/rhythmic_particles.py` file

---

## [2.15.0] — 2026-04-21
...
