# TODO

Ranked on 2026-04-21 from `codebot-test` (`~/bin/codebot.sh -s`) plus local verification.

1. ~~Restore a runnable `psysualizer.py` (`P0`)~~ [DONE]
   - Unified entrypoint is runnable and placeholders removed.

2. ~~Resolve the split pygame/ModernGL architecture (`P0`)~~ [DONE]
   - Aligned around a stable rendering contract; `psysualizer.py --gl` handles both paths.

3. ~~Add a smoke-test gate for entrypoints and effects (`P0`)~~ [DONE]
   - Added `smoke_test.py` for automated instantiation and import checks.

4. Refresh stale architecture and user docs (`P1`)
   - Update `ARCHITECTURE.md`, `README.md`, and related docs to match the current mode count, config defaults, and renderer status. [IN PROGRESS: ARCHITECTURE.md updated]
   - Evidence: `config.py` defaults and effect counts still need a pass in `README.md`.

5. Pin or constrain runtime dependencies (`P1`)
   - Add tested version ranges for `pygame`, `sounddevice`, and `librosa`, and document the optional GL extra in `requirements-gl.txt`.
   - Evidence: `requirements.txt` and `requirements-gl.txt` currently contain unpinned top-level packages only.

6. Break `psysualizer.py` into smaller modules (`P1`)
   - Extract audio analysis, display/window management, HUD/input handling, and mode switching into separate units.
   - Evidence: the main file is trying to own audio capture, event handling, display control, span mode, settings, and renderer setup all at once.

7. Improve beat and BPM detection quality (`P1`)
   - Revisit the current spectral-flux pipeline and compare it against a more robust tempo/onset path before adding more effect logic on top.
   - Evidence: the old improvement list still carries beat-detection work as open, and beat/BPM quality directly affects every effect.

8. Harden startup/config validation and fallback behavior (`P2`)
   - Validate display size, audio device availability, and renderer prerequisites early, with clean fallbacks when GPU or device setup fails.
   - Evidence: `config.py` now defaults `WIDTH` and `HEIGHT` to `0`, and the app depends on runtime monitor/audio initialization to become valid.

9. Add regression checks for the effect registry contract (`P2`)
   - Guard mode ordering, mode count, and effect-instantiation rules with a lightweight test so docs and code do not drift apart again.
   - Evidence: `effects/__init__.py` has ordering constraints (`Spectrum` and `Waterfall` last), while the docs already disagree with the live registry.

10. Add performance benchmarks for CPU vs GPU render paths (`P2`)
   - Measure frame time, CPU usage, and effect coverage before expanding the ModernGL port further.
   - Evidence: the project already invested in a GL proof of concept, but the desktop path is still mixed and there is no benchmark-driven rollout plan in the repo.
