# psysuals — Architecture

## Overview

```
psysualizer.py   ← main entry point: sounddevice callback + pygame loop
                 (Supports --gl for hardware-accelerated ModernGL rendering)
beat_tracking.py ← optional librosa beat/BPM refinement, off the render thread
config.py        ← shared mutable runtime state
effects/         ← one file per effect, registered in MODES
requirements-gl.txt ← optional dependency set for the GL path
```

`psysualizer.py` owns the runtime: audio capture, beat/BPM extraction, device selection, saved display restoration, span mode, HUD, and render orchestration. It supports both a CPU/Pygame surface path and a GPU/ModernGL path.

---

## Audio pipeline

```
sounddevice InputStream callback
    │  1024-sample mono blocks at 44 100 Hz
    ▼
_audio_cb()
    │  push block to LibrosaBeatTracker history
    │  Blackman-windowed rfft → log1p scale → /10
    │  exponential smoothing (α = 0.50) → _smooth_fft
    │  spectral flux on bins 0..19 → raw beat energy
    │  onset timestamps → fallback BPM
    │  mid / treble rolling normalisation
    ▼
get_audio()
    returns (waveform, fft, raw_beat, mid_energy, treble_energy, bpm, audio_time)
```

The callback stays cheap and deterministic. It computes the always-available fallback beat/BPM path and pushes raw audio into `LibrosaBeatTracker`.

Input-stream startup is tolerant now: the app tries the saved device first, then the default device, and if both fail it keeps running with no live input stream so the UI can still come up.

`beat_tracking.py` is an optional refinement layer:

- `push_audio()` stores recent blocks in a bounded deque.
- `analyze()` returns the last cached BPM immediately and, when enough history exists, schedules heavier `librosa` onset / beat analysis on a background thread.
- `refine_beat()` combines the low-latency spectral-flux signal with recent onset strength and beat-grid proximity.

This keeps the visual loop responsive while still improving BPM stability and beat timing when `librosa` is present.

### Beat normalisation

The main loop converts callback-time raw beat energy into the value passed to effects:

```python
impulse = max(0.0, min(raw_beat / (avg + 1e-6) - 1.0, 3.0))
beat_decay = max(impulse, beat_decay * 0.90)
beat = beat_decay
```

`avg` is the rolling average of the last 40 raw-beat samples. The result is volume-adaptive and decays smoothly between kicks.

---

## Render loop

The render loop in `psysualizer.py` uses a dual-target strategy to support both CPU and GPU effects:

1. **Target Abstraction**: All drawing operations target a `target` surface.
   - In CPU mode: `target` is the display surface.
   - In GL mode: `target` is an offscreen transparent surface used for UI/HUD.
2. **Effect Execution**: Effects are instantiated with an optional `GLRenderer`.
   - If an effect supports GL (like `PlasmaGL`), it renders directly to the GL context.
   - Otherwise, it draws to the `target` surface.
3. **Compositing**: In GL mode, the `target` surface is uploaded as a texture and blitted over the GL-rendered effects every frame.
4. **Final flip**: `pygame.display.flip()` presents the frame.

Mode switches recreate the effect instance and reset foreground intensity to `config.DEFAULT_EFFECT_GAIN`.

Fullscreen/display changes also recreate the background effect so display-bound caches stay aligned with the new geometry.

---

## Display and Span Mode

- Startup display selection comes from saved settings unless `--display N` overrides it.
- On multi-monitor setups, the primary process can enter span mode and spawn one child process for every *other* monitor.
- Child windows are launched with `--span-child`, so they never recursively create more span children.
- `A` / `D` in span mode change the shared secondary-display mode across all spawned child windows.

---

## Shared config

`config.py` is mutable at runtime. After opening the display, the app writes the real monitor dimensions back into `config.WIDTH` and `config.HEIGHT`, so effects can treat `config` as the live source of truth.

| Variable | Default | Notes |
|----------|---------|-------|
| `WIDTH` | `0` | Placeholder until the display opens |
| `HEIGHT` | `0` | Placeholder until the display opens |
| `FPS` | `60` | Target frame rate |
| `SAMPLE_RATE` | `44100` | Audio sample rate |
| `BLOCK_SIZE` | `1024` | Audio callback / FFT block size |
| `CHANNELS` | `1` | Mono input |
| `MID_ENERGY` | `0.0` | Normalised mid-band energy, updated each frame |
| `TREBLE_ENERGY` | `0.0` | Normalised treble energy, updated each frame |
| `BPM` | `0.0` | Live BPM estimate or tap-tempo override |
| `DEFAULT_EFFECT_GAIN` | `0.7` | Reset value used on startup and mode changes |
| `EFFECT_GAIN` | `0.7` | Current foreground intensity |

---

## Effect contract

Effects are simple classes that can draw to a `pygame.Surface` or use a `GLRenderer`:

```python
class MyEffect(Effect):
    TRAIL_ALPHA = 28

    def __init__(self, renderer=None, **kwargs):
        super().__init__(renderer=renderer, **kwargs)
        ...

    def draw(self, surf, waveform, fft, beat, tick):
        if self.renderer:
            # GL path
            ...
        else:
            # Pygame path (surf is a pygame.Surface)
            ...
```

Inputs passed to `draw()`:

| Parameter | Type | Meaning |
|-----------|------|---------|
| `surf` | `pygame.Surface` | Destination surface |
| `waveform` | `np.ndarray` `(1024,)` | Raw mono PCM block |
| `fft` | `np.ndarray` `(512,)` | Smoothed log-scaled spectrum |
| `beat` | `float` | Normalised beat impulse after gain / decay |
| `tick` | `int` | Frame counter |

Effects may also read:

- `config.WIDTH`, `config.HEIGHT`
- `config.MID_ENERGY`, `config.TREBLE_ENERGY`
- `config.BPM`
- `config.EFFECT_GAIN`
- `effects.palette.palette`

Conventional band splits used across the codebase:

| Band | Bins | Approx. use |
|------|------|-------------|
| bass | `fft[:6]` | kick, sub, low-end pulse |
| mid | `fft[6:30]` | body, synths, melodic motion |
| high | `fft[30:]` | hats, shimmer, edge detail |

---

## Adding an effect

1. Create `effects/myeffect.py`.
2. Implement `draw(surf, waveform, fft, beat, tick)`.
3. Import it in `effects/__init__.py`.
4. Add it to `MODES`.

Rules that matter in this repo:

- Modes 1–9 are the number-key modes.
- `Spectrum` and `Waterfall` must remain the final two `MODES` entries, in that order.
- If an effect owns its own persistent trail surface, set `TRAIL_ALPHA = 0` and manage fading internally.

---

## Helper modules

| File | Role |
|------|------|
| `core/audio_engine.py` | `AudioEngine`: capture, FFT, beat/genre detection |
| `core/display_manager.py` | `DisplayManager`: monitors, X11, windowing, span mode |
| `core/ui_manager.py` | `UIManager`: HUD, pane, picker rendering |
| `effects/utils.py` | `hsl()` and `_hsl_batch()` colour helpers |
| `effects/palette.py` | shared hue/saturation/lightness palette driven by audio |
| `settings.py` | persistent settings and preset storage under `~/.config/psysuals/` |
| `gl_renderer.py` | moderngl helper for the experimental GL path |
| `effects/shaders/` | tracked GLSL assets loaded by `gl_renderer.py` |
| `requirements-gl.txt` | optional dependency set for the GL path |

---

## File sizes

| File | Lines | Role |
|------|-------|------|
| `psysualizer.py` | `~340` | thin orchestrator |
| `core/audio_engine.py` | `~160` | audio logic |
| `core/display_manager.py` | `~130` | window/span logic |
| `core/ui_manager.py` | `~90` | UI rendering |
| `config.py` | `20` | shared runtime state |
| `effects/__init__.py` | `40` | mode registry |
| `effects/utils.py` | `27` | colour helpers |
| `gl_renderer.py` | `144` | GL helper and shader-asset loader |
| `settings.py` | `72` | settings and preset persistence |
| `effects/*.py` | `18` modes + shared helpers | visual implementations |


