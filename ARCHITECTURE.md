# psysuals — Architecture

## Overview

```
psysualizer.py   ← main CPU entry point: sounddevice callback + pygame loop
beat_tracking.py ← optional librosa beat/BPM refinement, off the render thread
config.py        ← shared mutable runtime state
effects/         ← one file per effect, registered in MODES
psysualizer_gl.py← experimental moderngl proof-of-concept
```

`psysualizer.py` owns the runtime: audio capture, beat/BPM extraction, device selection, mode switching, span mode, HUD, and render orchestration. Visual logic stays inside `effects/`.

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

Each frame in `psysualizer.py`:

1. Read `(waveform, fft, raw_beat, mid, treble, bpm, audio_time)` from `get_audio()`.
2. Optionally refine BPM and beat with `LibrosaBeatTracker`.
3. Publish shared state to `config.MID_ENERGY`, `config.TREBLE_ENERGY`, `config.BPM`, and `config.EFFECT_GAIN`.
4. Derive `draw_beat` either from `effect_gain` or the auto-gain RMS path.
5. Fade the frame using the active effect's `TRAIL_ALPHA`.
6. Draw the optional background effect into `bg_surf`.
7. Draw the foreground effect.
8. Blend the mode-switch crossfade overlay.
9. Draw tap-tempo flash and HUD.
10. `pygame.display.flip()` and `clock.tick(config.FPS)`.

Mode switches recreate the effect instance and reset foreground intensity to `config.DEFAULT_EFFECT_GAIN`.

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

Effects are simple classes that draw directly onto a `pygame.Surface`:

```python
class MyEffect:
    TRAIL_ALPHA = 28

    def __init__(self):
        ...

    def draw(self, surf, waveform, fft, beat, tick):
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
| `effects/utils.py` | `hsl()` and `_hsl_batch()` colour helpers |
| `effects/palette.py` | shared hue/saturation/lightness palette driven by audio |
| `settings.py` | persistent settings and preset storage under `~/.config/psysuals/` |
| `gl_renderer.py` | moderngl helper for the experimental GL path |

---

## File sizes

| File | Lines | Role |
|------|-------|------|
| `psysualizer.py` | `893` | main runtime |
| `config.py` | `20` | shared runtime state |
| `effects/__init__.py` | `40` | mode registry |
| `effects/utils.py` | `27` | colour helpers |
| `effects/*.py` | `18` modes + shared helpers | visual implementations |
