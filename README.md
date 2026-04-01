# psysuals

Real-time music visualizer — listens to audio input and renders animated visuals driven by the frequency spectrum and beat detection. Tuned for psytrance (138–148 BPM): aggressive beat response, long neon trails, hard kick-drum pulses.

![Version](https://img.shields.io/badge/version-1.6.5-orange) ![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

See [CHANGELOG.md](CHANGELOG.md) for release history.
See [EFFECTS.md](EFFECTS.md) for a detailed reference of all effects and their parameters.

## Visualisation modes

| # | Mode | Description |
|---|------|-------------|
| 1 | **Yantra** | Psychedelic sacred-geometry mandala — 6 concentric polygon rings (triangle→octagon) alternating rotation, web connections between rings, neon spokes, beat-driven spring pulses |
| 2 | **Cube** | Dual wireframe cubes — slow graceful rotation, gentle spring bounce, slow colour-fade across the spectrum; orbiting satellite cubes stay undistorted and within screen bounds |
| 3 | **TriFlux** | Equilateral triangle mosaic wall — all tiles wireframe with rainbow edges; 4–6 filled at any time; on beats a tile pops to the front way bigger (up to 8× on strong bass), spins and pulses to bass, then springs back into grid alignment; a glowing rainbow sweep crosses the whole screen at random angles |
| 4 | **Lissajous** | Psytrance trefoil — 3-D Lissajous knot with 3-fold symmetry, two-pass neon glow; beat explodes scale (0.55 impulse), jumps the hue palette, cranks head-dot radius, and draws extra glow halos |
| 5 | **Tunnel** | First-person ride through a curving tube — neon glow rings, rotating inner polygon (3–6 sides) per ring, full rainbow sweep across depth, beat flares nearest rings and spawns triangles that fly toward the camera; sparks always render above the tunnel geometry |
| 6 | **Corridor** | First-person ride through a neon rainbow corridor — concentric rounded-rectangle frames fly toward the camera with a full rainbow sweep across depth; beat flares nearest frames and spawns glowing sparks |
| 7 | **Nova** | Waveform kaleidoscope — audio waveform mapped to polar sectors with 7-fold mirror symmetry across 4 spinning layers; each layer reacts to a different band, beat explodes all outward |
| 8 | **Spiral** | Neon helix vortex — 6 arms fly toward the viewer with audio-reactive radius breathing and two-pass neon glow; cross-ring polygons connect arms at every depth interval; beat spring explodes the structure outward and jumps the palette |
| 9 | **Bubbles** | Translucent rising bubbles filling the full screen — size and spawn rate driven by bass |
| — | **Plasma** | Full-screen sine-interference plasma — four overlapping wave fields create a flowing psychedelic texture; bass shifts the palette, beat flashes the whole screen |
| — | **Branches** | Recursive fractal lightning tree — 6 neon arms radiate from centre, each splitting to depth 6 (64 tips); mid frequencies jitter branch angles live; bass drives length; beat fires extra arms with a brightness burst |
| — | **Spectrum** | Log-spaced spectrum analyser with peak markers and a waveform overlay |
| — | **Waterfall** | Scrolling time-frequency spectrogram — newest slice at top, log-spaced bins, hue = frequency, brightness = energy; beat flashes the leading edge |

Modes 1–9 are reachable with number keys. Use ←/→ to cycle through all modes including Plasma, Branches, Spectrum, and Waterfall.

## Requirements

- Python 3.8+
- A working audio input device (microphone, line-in, or loopback)

## Installation

```bash
git clone https://github.com/tstocke/psysuals.git
cd psysuals
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Usage

```bash
.venv/bin/python psysualizer.py
```

### Controls

| Key / Action | Effect |
|---|---|
| `←` / `→` or `Space` or click | Cycle to previous / next mode |
| `↑` / `↓` | Increase / decrease effect intensity (0.0 – 2.0, default 1.0) |
| `1` – `9` | Jump to modes 1–9 |
| `0` | Jump to mode 10 (first ←/→-only mode) |
| `D` | Open device picker (↑↓ navigate, Enter confirm, Esc cancel) |
| `F` | Toggle fullscreen (effects re-render at native resolution) |
| `H` | Toggle HUD / legend visibility |
| `Q` / `Esc` | Quit |

## Selecting an audio input device

Press `D` while running to open the interactive device picker. Use `↑`/`↓` to navigate the list of available input devices, `Enter` to switch, `Esc` to cancel. The active device is shown in the HUD at the top of the screen.

To visualise music playing through your speakers rather than a microphone, first set up a loopback device on your OS:

| OS | Method |
|----|--------|
| **Linux** | PulseAudio/PipeWire monitor source — visible in `pavucontrol` → Recording tab as *Monitor of …* |
| **macOS** | Install [BlackHole](https://github.com/ExistentialAudio/BlackHole) or Soundflower, then route output to it |
| **Windows** | Enable *Stereo Mix* in Sound settings |

Then press `D` in-app and select it from the list.

## How it works

1. `sounddevice` streams raw PCM from the input device in 1 024-sample blocks.
2. A Hann-windowed FFT is computed each block; the spectrum is log-scaled and smoothed with an exponential moving average (α = 0.50).
3. Beat energy is derived from the bass band (first 20 FFT bins) and normalised against a ~0.5-second rolling average so the visuals stay reactive at any volume.
4. `pygame` renders each frame with a semi-transparent black overlay for motion-trail / persistence effects.

## Project structure

```
psysuals/
├── psysualizer.py       # Entry point — audio pipeline and main loop
├── config.py            # Shared mutable state (WIDTH, HEIGHT, FPS, audio constants)
├── effects/
│   ├── __init__.py      # MODES list and package re-exports
│   ├── utils.py         # Shared colour helpers: hsl(), _hsl_batch()
│   ├── yantra.py        # Yantra effect
│   ├── cube.py          # Cube effect
│   ├── triflux.py       # TriFlux effect
│   ├── lissajous.py     # Lissajous effect
│   ├── tunnel.py        # Tunnel effect
│   ├── corridor.py      # Corridor effect
│   ├── nova.py          # Nova effect
│   ├── spiral.py        # Spiral effect
│   ├── bubbles.py       # Bubbles effect
│   ├── plasma.py        # Plasma effect
│   ├── branches.py      # Branches effect
│   ├── spectrum.py      # Spectrum (Bars) effect
│   └── waterfall.py     # Waterfall effect
├── ARCHITECTURE.md      # Code structure and extension guide
├── EFFECTS.md           # Full parameter reference for all effects
├── requirements.txt
└── README.md
```

To add a new effect: create `effects/youreffect.py` with a class implementing `draw(surf, waveform, fft, beat, tick)`, then add it to `MODES` in `effects/__init__.py`.

## License

MIT
