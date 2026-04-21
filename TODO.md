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
