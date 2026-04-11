# psysuals

Real-time music visualizer — listens to audio input and renders animated visuals driven by the frequency spectrum and beat detection. Tuned for psytrance (138–148 BPM): aggressive beat response, long neon trails, hard kick-drum pulses.

![Version](https://img.shields.io/badge/version-2.10.0-orange) ![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

See [CHANGELOG.md](CHANGELOG.md) for release history.
See [EFFECTS.md](EFFECTS.md) for a detailed reference of all effects and their parameters.

## What's new in v2.10.0 — moderngl GPU engine + dual-screen span

### moderngl render engine
A new GPU-accelerated rendering path sits alongside the existing pygame CPU path. `gl_renderer.py` wraps a moderngl context with a shared fullscreen-quad VBO, offscreen FBO helpers, and pixel readback to numpy — the foundation for the Android `draw_frame()` bridge.

`effects/plasma_gl.py` is the first effect ported: the four-wave interference plasma runs as a GLSL fragment shader, evaluated per pixel on the GPU instead of in a numpy CPU loop. `psysualizer_gl.py` is the standalone GL entry point (pygame OpenGL window).

Install the extra dependency: `pip install moderngl` (or `sudo apt install python3-moderngl`), then run `python psysualizer_gl.py`.

### Dual-screen span mode
On multi-monitor setups, `Shift+M` now runs **two independent effect instances** — one per physical screen — split at the real monitor boundary (detected via `pygame.display.get_desktop_sizes()`). Both halves receive the same audio data each frame but maintain completely separate visual state. On a single monitor, span mode behaves as before (one effect, NOFRAME full-screen).

Use `A` / `D` while in span mode to cycle the right-screen effect independently.

### F-key fix in span mode
Pressing `F` while in span mode now exits span mode and returns to the previous fullscreen state instead of also toggling the fullscreen flag.

---

## What's new in v2.9.0 — two new effects (Aurora & Lattice)

### Aurora
Five translucent sinusoidal curtains sweep across the screen like the Northern Lights. Each ribbon is built from three harmonics at different wavelengths and drift speeds, drawn additively so overlapping bands bloom together. Bass swells the amplitude; treble drives shimmer speed; beat triggers a brightness bloom and hue shift.

### Lattice
A 14×9 crystal grid of glowing nodes connected by double-stroke neon beams. Each column is mapped to a frequency band (bass left → treble right), so the grid reads the spectrum spatially. A shockwave ring expands from the centre on every beat — nodes near the wavefront flare white. Bass drives a subtle scale-breath; hue rotates with a radial offset (cyan core, violet edges).

Both effects replace the previous Particles effect.

---

## What's new in v2.8.0 — audio-driven forces

### FlowField
Bass energy now pulls all 4 000 particles gently toward the screen centre — strong kicks cause a brief convergence. Treble energy fires random scatter kicks in any direction, so hi-hats and cymbals send particles dispersing outward in bursts.

### Lissajous
The knot animation speed now scales with detected BPM — the knot spins faster at 148 BPM than at 138. Treble energy also brightens the glow passes in real time, so hi-hat bursts make the trail shimmer whiter.

### Bubbles
Strong bass hits now trigger a `bass_flash` swell that inflates all visible bubbles' rendered radius for ~10 frames. Beats above 0.7 also spawn 1–3 mega-bubbles (2–4× normal radius) that rise faster and burst with wider glow halos.

## What's new in v2.7.0 — effect polish

### Tunnel
Triangles now spawn only in the far third of the tube and the live cap is reduced (50 instead of 120), so the mid-range stays clear and the effect feels calmer between beats.

### Butterflies
Both butterflies in a pair now chase each other in a mutual pursuit spiral — solo steers toward love's position and love steers toward solo's, each targeting a rotating offset point. The orbit radius tightens from 240 px down to 40 px over the pair's lifetime. All butterflies are 70 % of their former size.

### Vortex fireworks
Auto-launch rate doubled at default intensity (every 40 frames instead of 85). The interval now scales linearly with `effect_gain` so higher intensity settings yield fewer background rockets (beat-triggered rockets remain unchanged).

## What's new in v2.6.0 — UX improvements

### Presets
Save the current mode, intensity, and background layer as a named preset with `P`. Cycle through saved presets with `Shift+P`. The active preset name is shown in the HUD.

### Real-time settings pane
Press `Tab` to open a right-side overlay with three live sliders: effect gain, background alpha, and crossfade length. Use `↑`/`↓` to navigate between sliders and `←`/`→` to adjust values while the music plays. Settings are saved on quit.

### Span mode
Press `Shift+M` to stretch the window across all connected monitors using the full virtual desktop dimensions. Press `Shift+M` again to return to single-display mode.

### HUD customisation
`H` toggles the HUD on/off as before. `Shift+H` now cycles through three detail levels: **full** (all rows + bars), **minimal** (mode name + BPM only), **off**.

### Multi-band energy bars
Three small vertical bars anchored to the bottom-left corner show real-time bass (red), mid (green), and treble (purple) energy at a glance — always visible whenever the HUD is on.

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
| — | **Aurora** | Northern Lights curtains — 5 sinusoidal ribbons with additive glow; bass swells amplitude, treble drives shimmer speed, beat triggers bloom flash and hue shift |
| — | **Lattice** | Crystal grid of 14×9 glowing nodes and neon beams — each column maps bass→treble across the FFT; beat fires a shockwave ring; bass drives scale-breath; radial hue offset (cyan core → violet edge) |
| — | **Spectrum** | Log-spaced spectrum analyser with peak markers and a waveform overlay |
| — | **Waterfall** | Scrolling time-frequency spectrogram — newest slice at top, log-spaced bins, hue = frequency, brightness = energy; beat flashes the leading edge |

Modes 1–9 are reachable with number keys. Use ←/→ to cycle through all modes including Plasma, Branches, Butterflies, FlowField, Vortex, Aurora, Lattice, Spectrum, and Waterfall.

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
| `←` / `→` or `Space` or click | Cycle to previous / next mode (or adjust pane slider when pane is open) |
| `↑` / `↓` | Increase / decrease effect intensity (or navigate pane sliders when pane is open) |
| `1` – `9` | Jump to modes 1–9 |
| `Tab` | Toggle real-time settings pane (effect gain, bg alpha, crossfade length) |
| `P` | Save current state as a preset |
| `Shift+P` | Cycle through saved presets |
| `A` | Toggle auto-gain (auto-scales beat to current volume) · in span mode: cycle right-screen effect backward |
| `B` | Toggle background layer (renders a second effect at configurable opacity behind the active one) |
| `Shift+B` | Cycle background effect (modes 1–9) |
| `M` | Tap tempo — tap 2+ times to lock BPM for 8 s |
| `Shift+M` | Toggle span mode — single monitor: one effect NOFRAME full-screen; multi-monitor: independent effect per screen |
| `D` | Open device picker (↑↓ navigate, Enter confirm, Esc cancel) · in span mode: cycle right-screen effect forward |
| `F` | Toggle fullscreen (effects re-render at native resolution) |
| `H` | Toggle HUD on / off |
| `Shift+H` | Cycle HUD detail: full → minimal → off |
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
│   ├── aurora.py             # Aurora effect
│   ├── lattice.py            # Lattice effect
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
