# TODO

Ranked on 2026-04-21 from `codebot` (`~/bin/codebot.sh -s`) plus local verification.

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

## 🚀 Priority 2: Visual Enhancements & Physics Tweaks

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
