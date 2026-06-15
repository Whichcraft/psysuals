# Changelog

All notable changes to psysuals are documented here.
Versions follow [Semantic Versioning](https://semver.org/).

---

## [3.7.0] — 2026-06-15

### Changed
- **Lissajous — calmer motion** — reduced mid influence on rotation velocity (`mid * 0.0015` → `0.0007`, `mid * 0.0020` → `0.0010`), tightened damping (`0.97` → `0.94`), and halved shape-distortion coefficients from mid/treble (`mid * 0.35` → `0.18`, `high * 0.40` → `0.22`, `high * 0.0004` → `0.0002`).
- **Tunnel — fewer triangles, lower speed** — reduced base travel speed (`0.03` → `0.022`), cut mid speed contribution (`0.06` → `0.04`), lowered triangle spawn rate (bass factor `2.0` → `1.2`, mid factor `3.0` → `1.5`, threshold `0.4` → `0.5`), and capped live triangles at 30 (was 50).
- **FlowField — edge recycling into cloud** — replaced random recycling with edge-proximity detection: particles within 8% of any screen edge are relocated to a random position within the central 60% of the screen, preventing edge clustering.
- **Branches — less reactive to mid/treble** — reduced mid jitter coefficients (`0.80` → `0.45`, `0.40` → `0.22`), treble jitter (`0.35` → `0.18`), spread (`mid * 0.55` → `0.28`, `high * 0.20` → `0.10`), ratio (`high * 0.12` → `0.06`), and extra arms from treble (`high * 1.8` → `0.8`).
- **Lattice — center-out frequency mapping** — changed column-to-frequency assignment from monotonic left→right to center-out: center columns respond to bass, edge columns respond to treble, creating a symmetric bloom on beats.
- **Lattice — dynamic grid density** — grid size now scales with display resolution: 14×9 on ≤1440p, 18×12 on 1440p–4K, 22×14 on 4K+. Column peak-normalization resets automatically on resize.

---

## [3.6.0] — 2026-06-15

### Added
- **Butterflies — two butterfly sizes** — each session now contains a mix of large (scale 5.04/4.79) and small (scale 2.52/2.39, half size) butterfly pairs in a big/small/big rotation. Total pair count unchanged (3 pairs, 6 butterflies).

### Fixed
- **BUG-023 (butterflies.py)** — mutual butterfly orbit/chase was completely non-functional: `solo_target`/`love_target` were being passed as the unused `t` parameter of `_Butterfly.update` instead of `chase_pos`, so butterflies always wandered. Orbit/chase now activates correctly.
- **Butterflies — smaller initial orbit radius** — reduced `_orbit_r` from 240 → 120 on pair creation, preventing overly wide initial sweeps when orbit first activates.
- **Butterflies — per-pair sync range** — wing-phase sync distance now scales with each pair's actual butterfly size instead of the hardcoded big-butterfly constant.

---

## [3.5.2] — 2026-06-11

### Fixed
- **BUG-017 (auto-gain)** — seed `rms_buf` with `target_rms` to prevent 2.0× spike on silence
- **BUG-018 (crossfade)** — set alpha to 0 before clearing previous frame, preventing remnant
- **BUG-019 (settings)** — atomic writes via `write-to-temp + os.replace()` in all 3 write paths
- **BUG-020 (audio callback)** — `try/except` around entire callback body prevents silent stream death
- **BUG-021 (GL blend modes)** — `BLEND_RGBA_MAX` → `BLEND_RGB_MAX` in 5 effects, `BLEND_ADD` → `BLEND_RGB_ADD` in aurora
- **BUG-022 (benchmarks)** — reset `tick = 0` per test to eliminate CPU/GL phase noise

## [3.5.1] — 2026-06-11

### Documented
- **BUG-018 (crossfade)** — off-by-one prevents full transparency on last frame
- **BUG-019 (settings)** — non-atomic writes silently reset user config on crash
- **BUG-020 (audio callback)** — unhandled exceptions silently kill audio stream
- **BUG-021 (GL blend modes)** — `BLEND_RGBA_MAX`/`BLEND_ADD` corrupt alpha on SRCALPHA targets
- **BUG-022 (benchmarks)** — shared tick counter introduces phase noise between CPU/GL tests

## [3.5.0] — 2026-06-11

### Fixed
- **BUG-016 (vortex.py)** — ember life off-by-one: decrement now applied to local variable before boundary check, preventing one extra frame of life and incorrect brightness on the last frame
- **BUG-017 (psysualizer.py)** — auto-gain spike on silence: documented (no code fix)

## [3.4.0] — 2026-06-03

### Changed
- **Creative Multi-band Audio Reactivity** — upgraded all 18 visualizer effects to use the new normalized audio engine parameters (`beat`, `config.MID_ENERGY`, and `config.TREBLE_ENERGY`) creatively and distinctively instead of relying on raw frequency splits. 

## [3.3.0] — 2026-06-03

### Added
- **Lattice Grid Sizing Adaption** — implemented dynamic canvas resolution divisor (`RES_DIV`) scaling (rendering at full resolution on 1440p/4K TV screens, half resolution on FHD, and 1/3 on laptops) and corrected the shockwave speed expansion formula to scale consistently with screen dimensions.
- **Lattice Column Normalization & Noise Gate** — introduced a dynamic peak-normalization tracking algorithm and noise gate filter to ensure balanced brightness and activity across all columns.
- **HUD Proportional Scaling** — scaled HUD font sizes dynamically based on screen width (from 20px on default windows up to 48px on 4K TV screens) and computed y-offsets dynamically to avoid overlap.

### Changed
- **Lattice Trail Rework** — removed the vortex/twisting rotation from the rotozoom feedback loop, making grid trails zoom straight back.
- **Lattice Column Cut-out** — completely cut out and hid the leftmost column (column 0) by positioning it off-screen and skipping its rendering.
- **Aurora Ribbons** — restored the original constant-thickness ribbon bands, reverting the edge-tapering fade logic.
- **FlowField Particles** — boosted particle count (baseline 12,000, max 50,000) and optimized rendering with `pygame.surfarray` vectorised assignment for an 18x speedup.
- **Butterflies Spawning** — reduced spawning offset, partner-joining, and death respawn delays for a much faster pace.

### Fixed
- **Pygame Dependency** — replaced `pygame` with `pygame-ce` in `requirements.txt` to provide precompiled wheels on Python 3.14, resolving installation and compilation errors.
- **FlowField Boundaries** — clipped particle coordinate arrays in `FlowField` to prevent out-of-bounds `IndexError` crashes.
- **VisualizerApp GL Initialization** — resolved an `AttributeError` by initializing `fade_alpha` before calling `_update_target_res` in OpenGL mode.

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
