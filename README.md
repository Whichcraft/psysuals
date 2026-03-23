# psysuals

Real-time music visualizer — listens to audio input and renders animated visuals driven by the frequency spectrum and beat detection.

![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## Visualisation modes

| # | Mode | Description |
|---|------|-------------|
| 1 | **Spiral** | 7 logarithmic spiral arms that warp with every frequency band |
| 2 | **Tentacles** | 14 segmented arms that writhe and sway with audio |
| 3 | **Cube** | Dual wireframe cubes — slow graceful rotation, gentle spring bounce, slow colour-fade across the spectrum |
| 4 | **Spectrum** | Log-spaced spectrum analyser with peak markers and a waveform overlay |
| 5 | **Particles** | Coloured particles burst from the centre on every beat |
| 6 | **Tunnel** | First-person ride through a curving tube — rings and longitudinal wall lines, centre shifts as the path bends |
| 7 | **Lissajous** | 3-D rotating Lissajous figure that morphs with audio |
| 8 | **Mandelbrot** | Animated zoom through 7 curated boundary points — auto-advances when the frame goes dark, speed and palette driven by bass |
| 9 | **Bubbles** | Translucent rising bubbles with specular highlights — size and spawn rate driven by bass |
| 10 | **Flax** | Flow-field particle strands following a noise field modulated by the spectrum — silk/fibre-like motion |
| 11 | **Glow Squares** | Grid of squares with multi-layer bloom glow — each column tracks a frequency band |

## Requirements

- Python 3.8+
- A working audio input device (microphone, line-in, or loopback)

## Installation

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Usage

```bash
.venv/bin/python visualizer.py
```

### Controls

| Key / Action | Effect |
|---|---|
| `Space` or click | Cycle to next mode |
| `1` – `9` | Jump to modes 1–9 |
| `0` | Jump to mode 10 (Flax) |
| `-` | Jump to mode 11 (Glow Squares) |
| `D` | Open device picker (↑↓ navigate, Enter confirm, Esc cancel) |
| `F` | Toggle fullscreen (effects re-render at native resolution) |
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
├── visualizer.py    # Main app — all visualisers and audio pipeline
├── requirements.txt
└── README.md
```

## License

MIT
