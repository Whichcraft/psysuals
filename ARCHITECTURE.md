# psysuals — Architecture

## Overview

```
psysualizer.py   ← entry point: audio capture thread + pygame main loop
config.py        ← shared mutable display/audio constants
effects/         ← one file per visualisation effect
```

`psysualizer.py` owns two things only: the audio pipeline (sounddevice → FFT → beat detection) and the pygame event/render loop. All visual logic lives in `effects/`.

---

## Audio pipeline

```
sounddevice (background thread)
    │  1024-sample PCM blocks at 44 100 Hz
    ▼
_audio_cb()
    │  Hann-windowed rfft → log1p scale → divide by 10
    │  Exponential moving average (α = 0.50) → _smooth_fft
    │  Bass-band mean (bins 0–19) → _beat_energy
    ▼
get_audio()  ← called once per frame from the main loop
    returns (waveform, fft, raw_beat)
```

Beat normalisation happens in the main loop, not in the callback:

```python
beat = max(0.0, min(raw_beat / (rolling_avg + 1e-6) - 1.0, 3.0))
```

A 15-frame rolling average makes the beat signal self-calibrating — it stays reactive regardless of playback volume.

---

## Render loop

Each frame:

1. Blit a semi-transparent black surface (`fade`) over the screen — this produces motion trails. Trail length is controlled per-effect via the optional `TRAIL_ALPHA` class attribute (default 28; lower = longer trails).
2. Call `vis.draw(screen, waveform, fft, beat * effect_gain, tick)`.
3. Draw the HUD overlay if enabled.
4. `pygame.display.flip()` + `clock.tick(FPS)`.

`effect_gain` (0.0–2.0, default 1.0, adjusted with ↑/↓) multiplies only the `beat` signal before passing it to `draw()`. FFT values are unaffected.

---

## config.py

Holds mutable module-level variables. After `pygame.display.set_mode()` resolves the actual screen size, the main loop writes back:

```python
config.WIDTH, config.HEIGHT = screen.get_size()
```

Effects always read `config.WIDTH` / `config.HEIGHT` at draw time, so they automatically use the correct dimensions after a fullscreen toggle. Effects are also re-instantiated on toggle, so `__init__` can safely read `config.WIDTH` / `config.HEIGHT` for one-time setup (e.g. Plasma's grid).

| Variable | Default | Notes |
|----------|---------|-------|
| `WIDTH` | `1280` | Updated after display init and fullscreen toggle |
| `HEIGHT` | `720` | — |
| `FPS` | `60` | Target frame rate |
| `SAMPLE_RATE` | `44100` | Audio capture sample rate |
| `BLOCK_SIZE` | `1024` | FFT / capture block size; half = number of FFT bins |
| `CHANNELS` | `1` | Mono capture |

---

## Effect interface

Every effect is a class with:

```python
class MyEffect:
    # Optional — controls trail fade speed (lower = longer trails, default 28)
    TRAIL_ALPHA = 28

    def __init__(self):
        # One-time setup. May read config.WIDTH / config.HEIGHT.
        ...

    def draw(self, surf: pygame.Surface, waveform: np.ndarray,
             fft: np.ndarray, beat: float, tick: int) -> None:
        # Called once per frame. Draw directly onto surf.
        ...
```

### Signal reference

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `waveform` | `np.ndarray` (1024,) | −1 … 1 | Raw mono PCM samples |
| `fft` | `np.ndarray` (512,) | 0 … ~1 | Smoothed log-scaled spectrum |
| `beat` | `float` | 0 … 3 | Normalised beat intensity (0 = silence, >1 = strong kick) |
| `tick` | `int` | 0, 1, 2 … | Frame counter since launch |

Frequency bands by convention (matching all existing effects):

| Band | Bins | Approx. Hz | Usage |
|------|------|-----------|-------|
| bass | `fft[:6]` | 0–260 | Kick drum, sub-bass |
| mid | `fft[6:30]` | 260–1 300 | Snare, melody |
| high | `fft[30:]` | 1 300+ | Hi-hats, cymbals |

---

## Adding a new effect

1. Create `effects/myeffect.py` — implement the interface above. Import `config` for screen dimensions and `from .utils import hsl` for colour.
2. Add to `effects/__init__.py`:
   ```python
   from .myeffect import MyEffect
   # add to MODES list:
   ("MyEffect", MyEffect),  # gets next available key
   ```

That's it. The main loop picks it up automatically; no other files need touching.

---

## effects/utils.py

| Function | Signature | Description |
|----------|-----------|-------------|
| `hsl` | `(h, s=1.0, l=0.5) → (r,g,b)` | Single HSL colour → RGB tuple |
| `_hsl_batch` | `(h, l, s=1.0) → uint8 array (...,3)` | Vectorised HSL for numpy arrays; used by Spiral and Lissajous for per-point trail colouring |

---

## File sizes (approximate)

| File | Lines | Role |
|------|-------|------|
| `psysualizer.py` | 245 | Audio + main loop |
| `config.py` | 9 | Constants |
| `effects/__init__.py` | 16 | MODES registry |
| `effects/utils.py` | 28 | Colour helpers |
| `effects/*.py` (×11) | 45–115 each | Individual effects |
