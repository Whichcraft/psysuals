# psysuals

Real-time music visualizer — listens to audio input and renders animated visuals driven by the frequency spectrum and beat detection. Tuned for psytrance (138–148 BPM): aggressive beat response, long neon trails, hard kick-drum pulses.

![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## Visualisation modes

| # | Mode | Description |
|---|------|-------------|
| 1 | **Yantra** | Psychedelic sacred-geometry mandala — 6 concentric polygon rings (triangle→octagon) alternating rotation, web connections between rings, neon spokes, beat-driven spring pulses |
| 2 | **Cube** | Dual wireframe cubes — slow graceful rotation, gentle spring bounce, slow colour-fade across the spectrum |
| 3 | **Plasma** | Full-screen sine-interference plasma — four overlapping wave fields create a flowing psychedelic texture; bass shifts the palette, beat flashes the whole screen |
| 4 | **Tunnel** | First-person ride through a curving tube — rings physically fly toward you and wrap to the far end, bass and beat control speed |
| 5 | **Lissajous** | Psytrance trefoil — 3-D Lissajous knot drawn with 3-fold symmetry and two-pass neon glow (wide dim halo + thin bright core); beat explodes the scale outward with spring physics |
| 6 | **Particles** | 3-D particle burst — beats eject spherical shells; perspective projection gives depth |
| 7 | **Spiral** | Fly through a curving 3-D helix vortex — 6 arms with rainbow trails that fade from black in the distance to bright colour up close, axis drifts like Tunnel |
| 8 | **Bubbles** | Translucent rising bubbles filling the full screen — size and spawn rate driven by bass |
| 9 | **Spectrum** | Log-spaced spectrum analyser with peak markers and a waveform overlay |
| 10 | **Waterfall** | Scrolling time-frequency spectrogram — newest slice at top, log-spaced bins, hue = frequency, brightness = energy; beat flashes the leading edge |

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
