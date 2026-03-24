# psysuals

Real-time music visualizer — listens to audio input and renders animated visuals driven by the frequency spectrum and beat detection. Tuned for psytrance (138–148 BPM): aggressive beat response, long neon trails, hard kick-drum pulses.

![Version](https://img.shields.io/badge/version-1.0.0-orange) ![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

See [CHANGELOG.md](CHANGELOG.md) for release history.

## Visualisation modes

| # | Mode | Description |
|---|------|-------------|
| 1 | **Yantra** | Psychedelic sacred-geometry mandala — 6 concentric polygon rings (triangle→octagon) alternating rotation, web connections between rings, neon spokes, beat-driven spring pulses |
| 2 | **Cube** | Dual wireframe cubes — slow graceful rotation, gentle spring bounce, slow colour-fade across the spectrum |
| 3 | **Plasma** | Full-screen sine-interference plasma — four overlapping wave fields create a flowing psychedelic texture; bass shifts the palette, beat flashes the whole screen |
| 4 | **Tunnel** | First-person ride through a curving tube — neon glow rings, rotating inner polygon (3–6 sides) per ring, full rainbow sweep across depth, beat flares nearest rings and spawns triangles that fly toward the camera |
| 5 | **Lissajous** | Psytrance trefoil — 3-D Lissajous knot with 3-fold symmetry, two-pass neon glow; beat explodes scale (0.55 impulse), jumps the hue palette, cranks head-dot radius, and draws extra glow halos |
| 6 | **Nova** | Waveform kaleidoscope — audio waveform mapped to polar sectors with 7-fold mirror symmetry across 4 spinning layers; each layer reacts to a different band, beat explodes all outward |
| 7 | **Spiral** | Neon helix vortex — 6 arms fly toward the viewer with audio-reactive radius breathing and two-pass neon glow; cross-ring polygons connect arms at every depth interval; beat spring explodes the structure outward and jumps the palette |
| 8 | **Bubbles** | Translucent rising bubbles filling the full screen — size and spawn rate driven by bass |
| 9 | **Spectrum** | Log-spaced spectrum analyser with peak markers and a waveform overlay |
| 10 | **Waterfall** | Scrolling time-frequency spectrogram — newest slice at top, log-spaced bins, hue = frequency, brightness = energy; beat flashes the leading edge |

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
| `Space` or click | Cycle to next mode |
| `1` – `9` | Jump to modes 1–9 |
| `0` | Jump to mode 10 (Waterfall) |
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
2. A Hann-windowed FFT is computed each block; the spectrum is log-scaled and smoothed with an exponential moving average (α = 0.25).
3. Beat energy is derived from the bass band (first 20 FFT bins) and normalised against a ~1-second rolling average so the visuals stay reactive at any volume.
4. `pygame` renders each frame with a semi-transparent black overlay for motion-trail / persistence effects.

## Project structure

```
psysuals/
├── psysualizer.py   # Main app — all visualisers and audio pipeline
├── requirements.txt
└── README.md
```

## License

MIT
