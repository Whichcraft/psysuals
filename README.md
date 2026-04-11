# psysuals

Real-time music visualizer — listens to audio input and renders animated visuals driven by the frequency spectrum and beat detection. Tuned for psytrance (138–148 BPM): aggressive beat response, long neon trails, hard kick-drum pulses.

![Version](https://img.shields.io/badge/version-2.5.0-orange) ![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

See [CHANGELOG.md](CHANGELOG.md) for release history.
See [EFFECTS.md](EFFECTS.md) for a detailed reference of all effects and their parameters.

## What's new in v2.5.0 — audio engine upgrade + new features

### Particles
Hundreds of neon particles erupt from the screen centre on every kick drum and trickle continuously at a rate driven by the hi-hat energy. Velocity scales with beat intensity. Hue drifts with mid-frequency content. Trails slowly fade, leaving glowing streaks.

### Audio engine improvements
- **Spectral flux beat detection** — beats are detected from the *change* in the bass spectrum rather than absolute level, giving sharper kick response especially in psytrance.
- **BPM detection** — onset timestamps are tracked and the median inter-beat interval is used to estimate tempo (60–200 BPM), displayed live in the HUD.
- **Multi-band energy** — bass, mid (~860 Hz–4.3 kHz), and treble (~4.3–11 kHz) are computed separately. Effects can read `config.MID_ENERGY` and `config.TREBLE_ENERGY` directly.
- **Blackman window** replaces Hann for better spectral leakage suppression.

### New visualizer features
- **Crossfade on mode switch** — smooth 45-frame dissolve when switching effects.
- **Background layer** (`B`) — overlay any of the first 9 effects at 40 % opacity behind the active foreground effect. `Shift+B` cycles the background effect.
- **Auto-gain** (`A`) — automatically scales beat intensity based on rolling RMS so the visuals stay reactive at any playback volume without manual adjustment.
- **Multi-screen** (`--display N` / `M` key) — launch on a specific display or cycle through available displays at runtime.
- **Enhanced HUD** — live BPM readout, colour-coded energy bars for beat / mid / treble, particle count when the Particles effect is active.
- **Settings persistence** — device, mode, intensity, HUD visibility, auto-gain, background state, and display index are saved and restored between sessions.

## What's new in v2.2.0 — two new effects

### FlowField
4 000 particles surf a continuously-evolving three-layer sine/cosine noise field and paint vivid rainbow trails on a slow-fade surface. Bass warps the field intensity and particle speed. Beat fires a phase jump that instantly reshapes every flow line, causing all trails to lurch and twist.

### Vortex
Each frame the previous frame is zoom-rotated and multiplied dark — building an infinite falling psychedelic tunnel. Firework rockets launch from the bottom, arc upward under gravity, and explode into 80–120 glowing embers at the apex. Embers fall back down with gravity, their trails swallowed by the feedback wormhole. Beat fires extra rockets and cranks the zoom and rotation speed.

## What's new in v2.1.0 — new effect

### Butterflies
One butterfly starts dancing to the music — wings flapping in sync with the bass. After 10–30 seconds a second butterfly enters from the edge, drawn by invisible attraction, and begins to orbit the first. As they grow closer their wing-flapping syncs up and sparkles burst between them on the beat.

## What's new in v2.0.0 — three stunning new effects

### TriFlux
The wall is alive. An equilateral triangle mosaic fills the screen with wireframe tiles, their edges blazing with per-angle rainbow colour. On every bass kick up to three tiles explode to the foreground — growing up to 8× their size, spinning, pulsing with the music, bouncing off screen edges — before springing back into perfect grid alignment. Two independent rainbow sweep waves constantly wash across the whole wall at shifting angles, bathing every tile in flowing colour. Nothing sits still. Everything reacts.

### Branches
Six neon lightning arms fire from the centre of the screen and fractal-split to depth 6, growing 64+ electric tips per arm. Every single branch angle jitters live to the mid frequencies — the whole tree writhes organically with the music. Bass drives the trunk length; strong beats fire extra arms and flood the screen with a brightness burst. The entire structure rotates slowly, never repeating the same shape twice.

### Corridor
A first-person ride through a glowing neon tunnel of rainbow rounded-rectangle frames that rush toward you and stretch to infinity. The path curves sinusoidally, pulling you through sweeping bends. Beat flares the nearest frames white-hot and erupts a shower of glowing sparks that streak toward the camera on their own independent trail layer — sparks always burn above the geometry, never buried behind it.

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
| — | **Butterflies** | Two butterflies dancing to the music — one starts solo, a second joins after 10–30 s and orbits in love; wing flapping syncs when they're close; sparkles burst between them on the beat |
| — | **FlowField** | 4 000 particles riding a 3-layer sine/cosine noise field — vivid rainbow trails on a slow-fade surface; bass warps field intensity; beat phase-jumps all flow lines |
| — | **Vortex** | Pixel feedback wormhole — zoom-rotate tunnel of decaying trails; firework rockets launch from bottom, explode into 80–120 gravity-affected embers at the apex; beat fires extra rockets |
| — | **Particles** | Neon particle system — beat bursts from centre, treble drives continuous trickle; velocity scales with beat, hue drifts with mid energy; numpy-batch rendering |
| — | **Spectrum** | Log-spaced spectrum analyser with peak markers and a waveform overlay |
| — | **Waterfall** | Scrolling time-frequency spectrogram — newest slice at top, log-spaced bins, hue = frequency, brightness = energy; beat flashes the leading edge |

Modes 1–9 are reachable with number keys. Use ←/→ to cycle through all modes including Plasma, Branches, Butterflies, FlowField, Vortex, Particles, Spectrum, and Waterfall.

## Requirements

- Python 3.8+
- A working audio input device (microphone, line-in, or loopback)
- PortAudio (system library required by `sounddevice`)

## Installation

**Ubuntu / Debian — install system dependencies first:**
```bash
sudo apt install python3-venv libportaudio2
```

**macOS:**
```bash
brew install portaudio
```

**Then install Python dependencies:**
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
| `A` | Toggle auto-gain (auto-scales beat to current volume) |
| `B` | Toggle background layer (renders a second effect at 40 % opacity behind the active one) |
| `Shift+B` | Cycle background effect (modes 1–9) |
| `M` | Move visualizer to next available display |
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
2. A Blackman-windowed FFT is computed each block; the spectrum is log-scaled and smoothed with an exponential moving average (α = 0.50).
3. **Beat detection** uses spectral flux — the mean positive difference between successive bass spectra (bins 0–20), normalised against a long-term rolling average. Beats are sharper and more kick-accurate than simple energy thresholding.
4. **BPM** is estimated from the median interval between detected onset timestamps, updated in real time and clamped to 60–200 BPM.
5. **Multi-band energy** — mid (bins 20–100, ~860 Hz–4.3 kHz) and treble (bins 100–256, ~4.3–11 kHz) are each normalised independently and exposed as `config.MID_ENERGY` / `config.TREBLE_ENERGY` for effects to read.
6. Genre classification runs every ~5 seconds (300 frames) from the accumulated spectrum and adjusts beat-weight presets for electronic, rock, or classical content.
7. `pygame` renders each frame with a per-effect semi-transparent black overlay for motion-trail / persistence effects. Mode switches dissolve over 45 frames.

## Project structure

```
psysuals/
├── psysualizer.py            # Entry point — audio pipeline and main loop
├── config.py                 # Shared mutable state (WIDTH, HEIGHT, FPS, BPM, MID_ENERGY, …)
├── settings.py               # User settings persistence (~/.config/psysuals/settings.json)
├── effects/
│   ├── __init__.py           # MODES list and package re-exports
│   ├── utils.py              # Shared colour helpers: hsl(), _hsl_batch()
│   ├── palette.py            # Shared colour palette driven by beat/mid/treble
│   ├── yantra.py             # Yantra effect
│   ├── cube.py               # Cube effect
│   ├── triflux.py            # TriFlux effect
│   ├── lissajous.py          # Lissajous effect
│   ├── tunnel.py             # Tunnel effect
│   ├── corridor.py           # Corridor effect
│   ├── nova.py               # Nova effect
│   ├── spiral.py             # Spiral effect
│   ├── bubbles.py            # Bubbles effect
│   ├── plasma.py             # Plasma effect
│   ├── branches.py           # Branches effect
│   ├── butterflies.py        # Butterflies effect
│   ├── flowfield.py          # FlowField effect
│   ├── vortex.py             # Vortex effect
│   ├── rhythmic_particles.py # Particles effect
│   ├── spectrum.py           # Spectrum (Bars) effect
│   └── waterfall.py          # Waterfall effect
├── ARCHITECTURE.md           # Code structure and extension guide
├── EFFECTS.md                # Full parameter reference for all effects
├── requirements.txt
└── README.md
```

To add a new effect: create `effects/youreffect.py` with a class implementing `draw(surf, waveform, fft, beat, tick)`, then add it to `MODES` in `effects/__init__.py` (before the Spectrum and Waterfall entries). Effects can also read `config.MID_ENERGY`, `config.TREBLE_ENERGY`, and `config.BPM`, and use `from effects.palette import palette` for consistent colour generation.

## License

MIT
