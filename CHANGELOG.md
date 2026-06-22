# Changelog

All notable changes to psysuals are documented here.
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

## [3.10.0] — 2026-06-22

### Changed
- **Mycelium** — Completely reworked from a single central burst into a multi-colony bioluminescent hyphae network with rotating satellite rings and swirling orbital spore particles.
- **Persistence** — Reworked nested rotating polygons into 3D perspective projection space with depth cueing (depth-based thickness and brightness shading) and non-coplanar axis rotation.
- **Clifford Attractor** — Rewritten to use high-speed 2D density mapping via `np.bincount`, logarithmic density scaling, dynamic percentile framing, and 3D diffuse relief shading from a rotating light source.
- **Butterflies** — Reverted to the stable April 2026 version to remove size variations and swarm forces, restoring classic chase/orbit motion behavior.
- **FlowField** — Shifted initial resolution divisor to start 2 levels faster (`RES_DIV = 3`).
- **Lattice** — Shifted initial resolution divisor up by 1 level to start 1 level faster.
- **TriFlux** — Moderated active rotation speeds, spin acceleration, and damping to reduce jitter and make the effect less nervous.

### Fixed
- **deque keyword crash** — Resolved Python < 3.10 startup crash by using positional arguments for `deque` in `psysualizer.py`.
- **Signal handler AttributeError** — Robustly delayed signal setup during initialization and added safety checks in `_quit()` to avoid referencing undefined display/audio managers.
- **ModernGL resource leak** — Released GPU shader programs and VAOs explicitly on `release()` in `PlasmaGL`.
- **Unbounded cache growth** — Quantized bubble surface cache keys to multiples of 8 and enforced a cache capacity limit of 128 in `Bubbles` to prevent memory leaks.
- **Branches recursion performance** — Optimized recursive tree rendering to scale depth based on `config.LOW_SPEC` settings.
- **Pygame image deprecation** — Updated `pygame.image.tostring` calls to `to_string` in `GLRenderer` to align with modern Pygame-ce.
- **Regression tester path** — Resolved relative path glob check to use absolute paths based on `__file__`.
- **UI Font scale on resize** — Added dynamic recalculation of font sizes in `UIManager` when window size/resolution updates.
- **Audio Callback Blocksize Jitter** — Padded/sliced incoming audio chunks in `AudioEngine` to prevent failures when the host ALSA/PortAudio block size varies.
- **Division-by-zero check** — Added safety checks in `Butterflies` boundary repulsion to prevent crashes on tiny viewport sizing.

## [3.9.0] — 2026-06-19

### Changed
- **Lightweight Dependencies** — Moved `librosa` from core requirements to an optional setup step. The visualizer and beat engine remain fully functional without it, drastically reducing installation size and time.
- **HUD Readability** — Added a semi-transparent black background panel behind both the top-left HUD text lines and the bottom-left multiband energy bars to guarantee visibility during dark, bright, or chaotic visuals.
- **Silence & No-input Modulations** — Added dynamic LFO (low-frequency oscillator) and soft heartbeat BPM-based modulation to visual idle parameters (beat decay, mid/treble floors) when silent or when no audio device is active, keeping visuals organic and avoiding static freezing.
- **Performance `--low-spec` Mode** — Added a `--low-spec` command-line argument that caps frame rate at 30 FPS and dynamically halves the active particle, slime agent, neural node/signal, and Mycelium growth budgets in performance-heavy effects (FlowField, SlimeMold, Vortex, Bubbles, Mycelium, Synapse).
- **Cleanup** — Purged `BUGS.md`, empty `results/` folder, and cleared tasks in `TODO.md`.
- **Bootstrap and hardening** — restored a runnable entrypoint, split the CPU/ModernGL architecture, added smoke tests and benchmarks, modularized the app, tightened dependencies, improved beat/BPM detection, hardened startup validation, and added regression checks for the registry contract.
- **Audio startup fallback** — startup now prefers concrete input devices (such as PipeWire/Pulse or explicit hardware devices) before falling back to Linux's generic `default` wrapper, reducing ALSA startup failures that aborted the app before the UI appeared.
- **Silence handling** — added RMS/FFT-based silence detection with hysteresis so effects drop to a deliberate low-motion idle level before and after tracks instead of reacting to noise-floor normalization spikes.
- **Crossfade scaling** — cached the scaled previous-frame surface used during mode crossfades, reducing repeated full-frame scaling work on every transition frame.
- **Aurora** — ribbon fills now use successive strip quads instead of one large polygon per band, avoiding the straight-line/spoke artifacts seen on Android.
- **FlowField** — removed the edge recycling behavior so particles wrap across the full viewport and no longer leave a dark border.
- **Butterflies** — trail scaling now uses a cached resize-aware surface instead of allocating a fresh full-screen scale result every frame.
- **Butterflies** — wing polygons are now pre-rendered into cached flap frames and rotated from those masks instead of being recomputed every draw.
- **Butterflies** — boundary handling now bounces butterflies back into view instead of pinning them to the edge.
- **Butterflies** — added light cohesion/separation steering so the swarm does not collapse into a single clump.
- **Butterflies** — centralized the main motion and lifecycle tuning values into named constants for easier adjustment.
- **HiDPI scaling** — internal render divisors now adapt to the actual display size so low-res effects stay sharper on large screens without forcing every frame to full resolution.
- **Magnetar** — particle density now scales higher on large displays, and the internal particle state is rebuilt on resize so the field stays full after geometry changes.
- **SlimeMold** — increased internal simulation fidelity, added resize-safe buffer rebuilds, and smooth-scaled the output to reduce chunky Android pixels.
- **Clifford** — replaced unconstrained random parameter jumps with curated presets plus dynamic framing and collapse recovery, keeping the attractor broad instead of collapsing into a tiny bright point.
- **Möbius** — removed the interior longitude wires so the band reads cleanly without straight cross-lines.
- **Chromatic** — replaced concentric RGB circles with wavy chromatic raindrop ripples that read properly on Android.
- **Mycelium** — reworked from a single center-out burst into a multi-colony swirling growth pattern for fuller, more psychedelic screen coverage.
- **Synapse** — bounded live pulse count and cascade fan-out to prevent runaway signal growth and improve stability on lower-power platforms.
- **Vortex** — feedback upscaling now reuses a cached surface and recreates internal buffers cleanly on resize.
- **Vortex** — the feedback zoom/rotation step now runs through a GL shader when ModernGL is available instead of relying solely on CPU rotozoom.
- **Vortex** — centralized the main launch, trail, feedback, and culling tuning values into named constants.
- **Random updates** — batched several scalar random paths into `numpy` vector draws and added optional `PSYSUALS_SEED` session seeding for reproducible runs.
- **Audio reactivity** — fixed FFT band handling so genre and energy calculations clamp safely to the available spectrum instead of assuming fixed bin ranges.
- **Import hygiene** — removed unused imports, lazy-loaded optional `librosa`, and deferred GL helper imports until the `--gl` path is actually used.
- **ModernGL lifecycle** — offscreen FBOs are now cached and released by `GLRenderer`, and the GL effects clear their local framebuffer caches on shutdown.
- **NVIDIA OpenGL compatibility** — requested a 3.3 core context explicitly and standardized shader versions so `--gl` works on stricter desktop drivers.
- **FlowField** — scaled particle count by screen area to keep large displays visually dense without overloading smaller ones.
- **Tunnel / Corridor** — lowered the near recycling threshold so geometry clears the screen before being recycled, removing boundary pops and gaps.

### Removed
- **Droste** — removed from the active mode registry.
- **OilSlick** — removed from the active mode registry.
- **Coral** — removed from the active mode registry.

### Documented
- **Mode count** — updated current docs to match the active 27-mode registry.

## [3.8.0] — 2026-06-15

### Added
- **Mycelium** — spreading fungal hyphal network; tips grow outward leaving decaying filament segments; beat fires a central bloom burst.
- **Magnetar** — ~6 000 particles riding an analytical rotating magnetic dipole field; beat fires an equatorial shockwave.
- **SlimeMold** — Physarum-style multi-agent trail simulation; self-organising vein network that pulses and reforms with the music.
- **Droste** — infinite self-similar recursive zoom portal with spiralling geometry fed into the feedback loop.
- **Clifford** — 40 000-walker strange attractor with audio-morphing parameters (a, b, c, d); beat jumps to a new attractor shape.
- **Möbius** — perspective-projected 3-D Möbius strip wireframe with twist shiver on beat.
- **Chromatic** — expanding ring waves that split red, green, and blue channels outward, creating prismatic aberration halos.
- **Persistence** — nested counter-rotating polygons with very long trail persistence for wagon-wheel moiré accumulation.
- **OilSlick** — full-screen thin-film interference pattern; two wave families mapped continuously to hue across the pixel grid.
- **Synapse** — neural graph with ~55 nodes and visible signal pulses cascading along edges on beat.
- **Coral** — bioluminescent fractal coral growing upward from the bottom edge with gravitropic branching and bloom pulse.
- **Heartbeat** — concentric pressure waves morphing between circle and polygon depending on bass intensity.

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
