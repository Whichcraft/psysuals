# TODO

Ranked on 2026-04-21 from `codebot-test` (`~/bin/codebot.sh -s`) plus local verification.

1. ~~Restore a runnable `psysualizer.py` (`P0`)~~ [DONE]
   - Unified entrypoint is runnable and placeholders removed.

2. ~~Resolve the split pygame/ModernGL architecture (`P0`)~~ [DONE]
   - Aligned around a stable rendering contract; `psysualizer.py --gl` handles both paths.

3. ~~Add a smoke-test gate for entrypoints and effects (`P0`)~~ [DONE]
   - Added `smoke_test.py` for automated instantiation and import checks.

4. ~~Refresh stale architecture and user docs (`P1`)~~ [DONE]
   - Updated `ARCHITECTURE.md`, `README.md`, `EFFECTS.md`, `CHANGELOG.md`, and `CLAUDE.md`.
   - All docs now match the current mode count, renderer status, and OO architecture.

5. ~~Pin or constrain runtime dependencies (`P1`)~~ [DONE]
   - Constrained `requirements.txt` and `requirements-gl.txt` to known working minimum versions using ranges.

6. ~~Break `psysualizer.py` into smaller modules (`P1`)~~ [DONE]
   - Extracted `AudioEngine`, `DisplayManager`, and `UIManager` into `core/` package.
   - Refactored `psysualizer.py` into an object-oriented `VisualizerApp`.

7. ~~Improve beat and BPM detection quality (`P1`)~~ [DONE]
   - Refined spectral flux normalization and smoothing in `AudioEngine`.
   - Constrained BPM range and improved local onset detection stability.

8. ~~Harden startup/config validation and fallback behavior (`P2`)~~ [DONE]
   - Added geometry validation and robust fallback paths in `DisplayManager`.
   - Improved audio device validation and silent mode degradation in `AudioEngine`.

9. ~~Add regression checks for the effect registry contract (`P2`)~~ [DONE]
   - Created `core/regression_tester.py` and integrated it into `smoke_test.py`.
   - Guards mode ordering (Spectrum/Waterfall last) and Effect inheritance.

10. ~~Add performance benchmarks for CPU vs GPU render paths (`P2`)~~ [DONE]
    - Created `benchmarks.py` to measure and compare effect frame rates.

---

# Backlog & Enhancements

This backlog is compiled from the model findings located in the `FINDINGS-*/*` directories (including [FINDINGS-GL.md](file:///home/tstocke/github.com/psysuals/FINDINGS-GL.md), [FINDINGS-REASONING.md](file:///home/tstocke/github.com/psysuals/FINDINGS-REASONING.md), and [FINDINGS-TODO.md](file:///home/tstocke/github.com/psysuals/FINDINGS-TODO.md)). It outlines critical performance optimizations, mathematical corrections, visual polish, and architecture/OpenGL enhancements.

## 🚀 Priority 1: Critical Fixes & Performance Bottlenecks

### 11. Optimize Trail Surface Scaling and Resizing
- **Priority**: High (P1)
- **Source**: [FINDINGS-GL.md/qwen3.6_35b-a3b-q8_0.txt](file:///home/tstocke/github.com/psysuals/FINDINGS-GL.md/qwen3.6_35b-a3b-q8_0.txt) & [FINDINGS-TODO.md/qwen3.6_35b-a3b-q8_0.txt](file:///home/tstocke/github.com/psysuals/FINDINGS-TODO.md/qwen3.6_35b-a3b-q8_0.txt)
- **Problem**: In effects such as [vortex.py](file:///home/tstocke/github.com/psysuals/effects/vortex.py) and [butterflies.py](file:///home/tstocke/github.com/psysuals/effects/butterflies.py), calling `pygame.transform.scale` or `pygame.transform.rotozoom` every frame to downsample or handle trails is CPU-intensive. Additionally, if the window size (`config.WIDTH` or `config.HEIGHT`) changes, the trail surface does not dynamically resize and may become out-of-sync or throw errors.
- **Action Items**:
  - [ ] Implement a window resize hook / change detector to recreate trail surfaces only when dimensions change.
  - [ ] Cache scaled trail surfaces and avoid calling scale operations every single frame.
  - [ ] Use `pygame.transform.smoothscale` selectively or investigate pre-rendering at logical resolutions.

### 12. Address Trail Color Drift and Blend Mode Issues
- **Priority**: High (P1)
- **Source**: [FINDINGS-REASONING.md/qwen3.6_35b-a3b-q8_0.txt](file:///home/tstocke/github.com/psysuals/FINDINGS-REASONING.md/qwen3.6_35b-a3b-q8_0.txt) & [FINDINGS-GL.md/qwen3.6_35b-a3b-q8_0.txt](file:///home/tstocke/github.com/psysuals/FINDINGS-GL.md/qwen3.6_35b-a3b-q8_0.txt)
- **Problem**: Multiplicative fading via `special_flags=pygame.BLEND_RGB_MULT` (e.g. `self._trail.fill(self._FADE_FILL, special_flags=pygame.BLEND_RGB_MULT)`) dims all color channels equally. Over ~10 frames, brightness drops to ~23%, causing colors to turn desaturated, muddy, or black. Furthermore, some effects use `BLEND_RGBA_MAX`, which takes the maximum component across RGBA and can cause harsh visual clipping or non-standard alpha compositing.
- **Action Items**:
  - [ ] Switch to a semi-transparent `pygame.SRCALPHA` surface with `blit(..., special_flags=pygame.BLEND_RGBA_MULT)` and a lower alpha overlay to prevent muddy color drift.
  - [ ] Experiment with standard alpha blending or additive blending (`pygame.BLEND_RGBA_ADD` / `pygame.BLEND_ALPHA_ADD`) to achieve smoother glows.

### 13. Safe FFT Data Slicing
- **Priority**: High (P1)
- **Source**: [FINDINGS-REASONING.md/qwen3.6_35b-a3b-q8_0.txt](file:///home/tstocke/github.com/psysuals/FINDINGS-REASONING.md/qwen3.6_35b-a3b-q8_0.txt)
- **Problem**: Audio analysis slices hardcoded ranges (e.g., `bass = float(np.mean(fft[:6]))`), assuming the FFT output has at least 6 bins. If the FFT configuration changes at runtime, this will crash with an out-of-bounds error or analyze the wrong frequency spectrum.
- **Action Items**:
  - [ ] Implement safe slicing via bounds checking: `fft[:min(6, len(fft))]`.
  - [ ] Transition to relative/percentage-based frequency bands (e.g., `fft[:int(len(fft) * 0.03)]`) for a more stable and sample-rate-independent low-frequency band.

---

## 🎨 Priority 2: Visual Enhancements & Physics Tweaks

### 14. Fix Boundary Clamping "Sticking" in Steering Behaviors
- **Priority**: Medium (P2)
- **Source**: [FINDINGS-GL.md/qwen3.6_35b-a3b-q8_0.txt](file:///home/tstocke/github.com/psysuals/FINDINGS-GL.md/qwen3.6_35b-a3b-q8_0.txt) & [FINDINGS-REASONING.md/qwen3.6_35b-a3b-q8_0.txt](file:///home/tstocke/github.com/psysuals/FINDINGS-REASONING.md/qwen3.6_35b-a3b-q8_0.txt)
- **Problem**: Clamping positions directly using `max(cl, min(..., self.x))` in [butterflies.py](file:///home/tstocke/github.com/psysuals/effects/butterflies.py) causes entities to "stick" against screen edges if their velocity vectors keep pushing them outward.
- **Action Items**:
  - [ ] Apply a small outward nudge or reflective force when entities reach the boundaries (e.g., `if self.x <= cl: self.x += 0.5`).
  - [ ] Refactor boundaries to apply a steering force away from the screen boundaries instead of hard coordinate clamping.

### 15. Flocking & Mutual Steering for Swarm Effects
- **Priority**: Medium (P2)
- **Source**: [FINDINGS-REASONING.md/qwen3.6_35b-a3b-q8_0.txt](file:///home/tstocke/github.com/psysuals/FINDINGS-REASONING.md/qwen3.6_35b-a3b-q8_0.txt)
- **Problem**: Butterflies and particles clump together, overlapping in an unnatural manner and reducing visual clarity.
- **Action Items**:
  - [ ] Add basic flocking behaviors, specifically mutual repulsion (separation force) and attraction (cohesion force), to prevent excessive clustering.
  - [ ] Tune separation radius based on beat intensity.

### 16. Expose Configurable Magic Numbers
- **Priority**: Medium (P2)
- **Source**: [FINDINGS-REASONING.md/qwen3.6_35b-a3b-q8_0.txt](file:///home/tstocke/github.com/psysuals/FINDINGS-REASONING.md/qwen3.6_35b-a3b-q8_0.txt)
- **Problem**: Many effects contain hardcoded visual thresholds, timers, and particle limits (e.g. `MAX_PAIRS`, `orbit_r`, `_break_cd`, explosion ember limits).
- **Action Items**:
  - [ ] Consolidate magic constants into a configurations dictionary per effect class.
  - [ ] Integrate these parameters into the real-time configuration/settings UI.

### 17. Expand Audio Reactivity Bindings (COMPLETED)
- **Status**: Completed
- **Problem**: Reactivity is primarily mapped to simple `bass` amplitude or `beat` indicators.
- **Fixes Implemented**:
  - [x] Bound visual parameters (wing-flap speed, flight velocity, camera path sway, 3-D vertex jitter, obstacle rotation speed, particle outward scatter) to the new normalized audio engine bands (`beat`, `config.MID_ENERGY`, and `config.TREBLE_ENERGY`) across all 18 effects.

---

## ⚡ Priority 3: Deep OpenGL Integration & Infrastructure

### 18. Optimize Shape Rendering (Cached Surface vs. Real-Time Drawing)
- **Priority**: Medium (P2)
- **Source**: [FINDINGS-REASONING.md/qwen3.6_35b-a3b-q8_0.txt](file:///home/tstocke/github.com/psysuals/FINDINGS-REASONING.md/qwen3.6_35b-a3b-q8_0.txt)
- **Problem**: Drawing polygons via `pygame.draw.polygon()` for multiple entities (e.g., butterfly wings) every frame is computationally expensive.
- **Action Items**:
  - [ ] Precompute wing polygons at start or scale change, draw them to a cached transparent `pygame.Surface`.
  - [ ] Draw using `pygame.transform.rotate()` from the cache rather than recalculating vertices on the fly.

### 19. Dynamic HiDPI Scale & Resolution Adjustments
- **Priority**: Medium (P2)
- **Source**: [FINDINGS-GL.md/qwen3.6_35b-a3b-q8_0.txt](file:///home/tstocke/github.com/psysuals/FINDINGS-GL.md/qwen3.6_35b-a3b-q8_0.txt)
- **Problem**: Hardcoded scaling ratios (e.g. `RES_DIV = 2` or `3`) cause pixelation/aliasing on high resolution (HiDPI) displays or large windows.
- **Action Items**:
  - [ ] Query native dimensions using `pygame.display.Info()` or check `config.WIDTH * config.SCALE_FACTOR`.
  - [ ] Dynamically compute `RES_DIV` scaling factor to balance performance and visual fidelity.

### 20. Precompute/Optimize Random Updates (Reducing GC Pressure)
- **Priority**: Medium (P2)
- **Source**: [FINDINGS-GL.md/qwen3.6_35b-a3b-q8_0.txt](file:///home/tstocke/github.com/psysuals/FINDINGS-GL.md/qwen3.6_35b-a3b-q8_0.txt)
- **Problem**: Frequent calls to `random.randint` and `random.gauss` inside update loops generate massive garbage collection pressure and prevent deterministic visualization.
- **Action Items**:
  - [ ] Replace scalar `random` loop invocations with pre-generated random arrays or utilize `numpy.random` vectors where applicable.
  - [ ] Implement optional session-seeding for deterministic runs.

### 21. GL Shader Offloading for Trails and entity animations
- **Priority**: Medium (P2)
- **Source**: [FINDINGS-REASONING.md/qwen3.6_35b-a3b-q8_0.txt](file:///home/tstocke/github.com/psysuals/FINDINGS-REASONING.md/qwen3.6_35b-a3b-q8_0.txt)
- **Problem**: The visualizer is CPU-bound when processing trails and scaling operations in software rendering.
- **Action Items**:
  - [ ] Implement feedback trails and animations (e.g., wing flapping, particle offsets) via GL fragment/vertex shaders in the ModernGL backend.
  - [ ] Move the expensive rotozoom-based feedback loop in `Vortex` to a dedicated shader program.

### 22. Complete ModernGL Release Lifecycle
- **Priority**: Low (P3)
- **Source**: [gl_renderer.py](file:///home/tstocke/github.com/psysuals/gl_renderer.py#L140-L154) & [FINDINGS-GL.md/qwen3.6_35b-a3b-q8_0.txt](file:///home/tstocke/github.com/psysuals/FINDINGS-GL.md/qwen3.6_35b-a3b-q8_0.txt)
- **Problem**: ModernGL objects like Vertex Arrays (VAO) and Programs must be explicitly released to prevent GPU resource leaks.
- **Action Items**:
  - [ ] Audit `GLRenderer.release()` to ensure all allocated vertex buffer objects, textures, and vertex array bindings are cleanly released.
  - [ ] Set up GLES / Android context verification wrappers for mobile compatibility.

### 23. Resolved NVIDIA OpenGL Compatibility Issues (COMPLETED)
- **Status**: Resolved
- **Problem**: When running with the `--gl` flag, NVIDIA drivers failed to render certain effects or displayed blank screens due to strict context profile checks and shader specifications.
- **Fixes Implemented**:
  - [x] Requested OpenGL 3.3 Core Profile explicitly in [display_manager.py](file:///home/tstocke/github.com/psysuals/core/display_manager.py) before window initialization.
  - [x] Standardized all shader version declarations to `#version 330 core` in [plasma_gl.py](file:///home/tstocke/github.com/psysuals/effects/plasma_gl.py) and [gl_renderer.py](file:///home/tstocke/github.com/psysuals/gl_renderer.py) for Core Profile compliance.
  - [x] Initialized the `rgb` variable in [plasma_gl.py](file:///home/tstocke/github.com/psysuals/effects/plasma_gl.py)'s `hsl2rgb` shader function to prevent undefined compilation/optimization results on strict NVIDIA compilers.
  - [x] Cleaned up invalid comments in unused shader files [rect.vert](file:///home/tstocke/github.com/psysuals/effects/shaders/rect.vert) and [rect.frag](file:///home/tstocke/github.com/psysuals/effects/shaders/rect.frag).

### 24. Scale FlowField Particle Count by Screen Size (COMPLETED)
- **Status**: Completed
- **Problem**: On large TV screens, the 8000 (or static) particle limit in FlowField looks sparse, whereas 4000 is sufficient for laptops.
- **Fixes Implemented**:
  - [x] Defined dynamic particle count `self._n` in [flowfield.py](file:///home/tstocke/github.com/psysuals/effects/flowfield.py) based on pixel area (`W * H`), using a baseline of 4000 for a 1080p screen.
  - [x] Clamped the count between 1,000 (minimum for small windows) and 16,000 (maximum for 4K TVs to preserve framerate) to guarantee both visual richness and smooth performance.
  - [x] Updated data structures and loops in [flowfield.py](file:///home/tstocke/github.com/psysuals/effects/flowfield.py) to dynamically respect the scaled particle count.

### 25. Remove Visual Gaps/Pops in Tunnel and Corridor Effects (COMPLETED)
- **Status**: Completed
- **Problem**: In Tunnel and Corridor, the nearest rings/frames recycled prematurely when crossing Z_NEAR, leaving visual gaps on the screen boundaries before they were fully offscreen.
- **Fixes Implemented**:
  - [x] Decreased the near recycling threshold `Z_NEAR` from 0.18 to 0.06 in [tunnel.py](file:///home/tstocke/github.com/psysuals/effects/tunnel.py).
  - [x] Decreased the near recycling threshold `Z_NEAR` from 0.28 to 0.06 in [corridor.py](file:///home/tstocke/github.com/psysuals/effects/corridor.py).
  - [x] This forces the flying geometry to grow larger than the display dimensions and fully clear the screen boundaries before being recycled, running smooth without pops or gaps.


