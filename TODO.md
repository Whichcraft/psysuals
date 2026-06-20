# TODO

This document tracks bugs, memory leaks, performance bottlenecks, and other technical debt found during deep codebase inspection.

## 1. High Priority (Crashes & Compatibility Bugs)

- [x] **Startup Compatibility: deque keyword argument**
  - **File:** `psysualizer.py:105`
  - **Description:** `self.rms_buf = deque(maxlen=30, iterable=[self.target_rms])` uses `iterable` as a keyword argument. In python versions < 3.10, the built-in `deque` class constructor does not accept `iterable` as a keyword argument, causing a startup crash.
  - **Fix:** Change to positional initialization: `deque([self.target_rms], maxlen=30)`.

- [x] **Division-by-Zero in boundary repulsion**
  - **File:** `effects/butterflies.py:103`
  - **Description:** If the window is collapsed to a very small width or height, `config.WIDTH // 5` or `config.HEIGHT // 5` becomes `0`, making `m = 0`. The subsequent lines divide by `m`, throwing a `ZeroDivisionError`.
  - **Fix:** Check `if m > 0` before calculating repulsion.

- [x] **Startup Signal Handler AttributeError**
  - **File:** `psysualizer.py:54` (called `_setup_signals` before initializing display and audio engines).
  - **Description:** If SIGINT/SIGTERM is received during display/audio initialization, `_sig_handler` calls `self._quit()`, which references `self.display` and `self.audio` before they are defined, raising an `AttributeError`.
  - **Fix:** Register signals at the end of initialization, or add `hasattr` checks in `_quit()`.

## 2. Medium Priority (Resource Leaks & Performance)

- [x] **ModernGL GPU Program & VAO Leak**
  - **File:** `effects/plasma_gl.py:247`
  - **Description:** On mode switches, `release()` is called. `PlasmaGL` compiles shaders dynamically, but doesn't call `.release()` on its ModernGL program and vertex array object (`self._prog`, `self._vao`), leaking GPU context handles.
  - **Fix:** Explicitly release program and VAO in `release()`.

- [x] **Uncapped Cache Growth (Memory Leak)**
  - **File:** `effects/bubbles.py:48`
  - **Description:** Bubble surface cache keys are generated based on dynamic bubble sizes. As sizes fluctuate based on audio analysis, the cache dictionary grows indefinitely without eviction or size limits.
  - **Fix:** Round bubble sizes to nearest multiple of 8/16 to constrain cache key space, and implement an eviction cap.

- [x] **Branches Recursion Performance Bottleneck**
  - **File:** `effects/branches.py:33`
  - **Description:** Pure Python recursive drawing down to depth 7 with high branching factors slows down performance. The effect does not respect `config.LOW_SPEC` to scale down the recursion depth or arm counts on low-end machines.
  - **Fix:** Respect `config.LOW_SPEC` in branches configuration.

## 3. Low Priority / Maintenance

- [x] **Pygame Image tostring Deprecation**
  - **File:** `gl_renderer.py:169`, `gl_renderer.py:189`
  - **Description:** `pygame.image.tostring` is deprecated in modern Pygame (2.2+) in favor of `pygame.image.to_string`.
  - **Fix:** Replace with `to_string`.

- [x] **Relative Path Assumptions in Regression Tester**
  - **File:** `core/regression_tester.py:32`
  - **Description:** Tester relies on relative path glob `glob.glob("effects/*.py")`, failing to find files if run from outside the project root.
  - **Fix:** Resolve path relative to `__file__`.

- [x] **UI Font Scaling on Window Resize**
  - **File:** `core/ui_manager.py:10`
  - **Description:** UIManager calculates system font sizes once during `__init__`. When the visualizer screen undergoes resolution resizing or fullscreen toggle, font sizes and text labels do not re-scale to fit the new viewport.
  - **Fix:** Add a `recalculate_fonts()` method and trigger it during fullscreen/resize events.

- [x] **Audio Callback Blocksize Jitter Resilience**
  - **File:** `core/audio_engine.py:90`
  - **Description:** The `_audio_cb` callback assumes incoming block sizes are exactly `config.BLOCK_SIZE`. Under API/buffer mismatches on some host devices, block sizes may differ, causing shape mismatches with `_blackman_window` and silent analysis failures.
  - **Fix:** Pad or slice incoming audio blocks to ensure they match `config.BLOCK_SIZE`.
