# Project rules

## Release cycle

After completing any feature or fix work, always follow this release cycle in order:

1. **Bump minor version** — update the version number in `README.md` (badge) and add a new entry at the top of `CHANGELOG.md`. Minor bump: `x.y.z → x.(y+1).0`.
2. **Update all docs** — ensure `README.md` (What's new section, modes table, project structure) and `CHANGELOG.md` are accurate and complete.
3. **Update qmd index** — run `qmd update && qmd embed` so the local search index and embeddings reflect all changes.
4. **Push to dev** — commit all changes on the `dev` branch and push: `git push origin dev`.
5. **Sync to main** — merge dev into main and push: `git checkout main && git merge dev && git push origin main && git checkout dev`.

## Android integration (androsaver)

These visuals will be used in an Android live wallpaper / screensaver app
called **androsaver** (Kotlin/Java).  Keep this in mind when touching the
effects or audio pipeline.

### Planned bridge architecture

Run Python via **Chaquopy** embedded in the Android app.  Each effect exposes
a `draw_frame(width, height, waveform, fft, beat, tick) → np.ndarray (RGBA uint8)`
method that renders into a numpy pixel buffer instead of a pygame surface.
Kotlin receives the buffer and paints it onto a `Bitmap` / `SurfaceView`.

This keeps all audio math and effect logic in Python; only a thin
numpy-based renderer needs to be added alongside each existing pygame draw().

### Rules for new/modified effects

- **No pygame at module level** — gate all `pygame.*` calls behind a
  `HAS_PYGAME` flag so the module imports cleanly on Android:
  ```python
  try:
      import pygame; HAS_PYGAME = True
  except ImportError:
      HAS_PYGAME = False
  ```
- **config.WIDTH / config.HEIGHT must be set by the host** before calling
  draw — already the case; never hard-code screen dimensions in effects.
- **No sounddevice in effects** — audio is passed in as arguments.
  `sounddevice` is only used in `psysualizer.py` and will be replaced on
  Android by `AudioRecord` data piped in via JNI/Chaquopy.

### Android target
- Min SDK: API 26 (Android 8, `WallpaperService` / `DaydreamService`)
- Frame budget: 16 ms at 60 fps on mid-range hardware
- Pinned dependencies for Android build: `numpy >= 1.24` (no scipy, no
  sounddevice, no pygame)

---

## Effect order

**Spectrum and Waterfall must always be the last two entries in `MODES`** (in `effects/__init__.py`), in that order: Spectrum second-to-last, Waterfall last. When adding new effects, insert them before Spectrum.
