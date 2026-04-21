# psysuals v3 — The Ultimate Psychedelic Experience

**Welcome to the super-duper greatest music visualizer ever made.** psysuals v3 is a massive leap forward, re-engineered from the ground up to deliver uncompromising visual intensity and rock-solid performance. Whether you're blasting psytrance in a dark room or driving a multi-monitor stage setup, v3 is built to melt your mind with precision and style.

![Version](https://img.shields.io/badge/version-3.1.0-orange)
 ![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

---

## 🚀 Biggest Changes in v3

- **✨ Unified ModernGL Engine** — Harness the power of your GPU. v3 merges experimental hardware acceleration into the core app. Run with `--gl` for blistering frame rates and per-pixel shader fluid motion.
- **🏗️ Modular Object-Oriented Architecture** — Re-written from a monolithic script into a sleek, professional engine. Specialized `AudioEngine`, `DisplayManager`, and `UIManager` classes ensure a clean, maintainable, and high-performance foundation.
- **🖥️ Ultimate Multi-Monitor "Span Mode"** — Gone are the days of fixed dual-screen limits. v3 scales dynamically, spawning child processes for every monitor you own, with synchronized mode switching across the entire span.
- **🔊 Battle-Hardened Audio Pipeline** — Bulletproof audio capture that never crashes. v3 features intelligent no-input fallback, live device switching, and a refined spectral-flux beat detection system tuned for maximum response.
- **⚖️ Built-in Benchmarking & Regression Gates** — Measure your speed with `benchmarks.py` and sleep easy knowing our automated smoke tests guard all 18 effects from regressions.

---

## ⚙️ Installation

### 1. Requirements
- Python 3.8+
- Audio input device (microphone or loopback monitor)
- (Optional) OpenGL 3.3+ capable GPU for hardware acceleration

### 2. Setup
Clone the repository and create a virtual environment:
```bash
git clone https://github.com/Whichcraft/psysuals.git
cd psysuals
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Hardware Acceleration (Optional)
To enable the high-performance ModernGL path:
```bash
pip install -r requirements-gl.txt
```

---

## Usage

```bash
.venv/bin/python psysualizer.py
```

Run with ModernGL hardware acceleration:
```bash
.venv/bin/python psysualizer.py --gl
```

The app restores the last saved display index on startup. Use `--display N` to override that for a single launch.

### Controls

| Key / Action | Effect |
|---|---|
| `←` / `→` or `Space` or click | Cycle to previous / next mode (or adjust pane slider when pane is open) |
| `↑` / `↓` | Increase / decrease effect intensity (or navigate pane sliders when pane is open) |
| `1` – `9` | Jump to modes 1–9 |
| `Tab` | Toggle real-time settings pane (effect gain, bg alpha, crossfade length) |
| `P` | Save current state as a preset |
| `Shift+P` | Cycle through saved presets |
| `A` | Toggle auto-gain (auto-scales beat to current volume) · in span mode: cycle the shared secondary-display effect backward |
| `B` | Toggle background layer (renders a second effect at configurable opacity behind the active one) |
| `Shift+B` | Cycle background effect (modes 1–9) |
| `M` | Tap tempo — tap 2+ times to lock BPM for 8 s |
| `Shift+M` | Toggle span mode — single monitor: one effect NOFRAME full-screen; multi-monitor: one child process per other display |
| `D` | Open device picker (↑↓ navigate, Enter confirm, Esc cancel) · in span mode: cycle the shared secondary-display effect forward |
| `F` | Toggle fullscreen (effects re-render at native resolution) |
| `H` | Toggle HUD on / off |
| `Shift+H` | Cycle HUD detail: full → minimal → off |
| `Q` / `Esc` | Quit |

Changing modes with `←` / `→`, `Space`, number keys, or mouse click resets intensity to the default `0.7`. Saved presets can still restore a custom intensity deliberately.

## Selecting an audio input device

Press `D` while running to open the interactive device picker. Use `↑`/`↓` to navigate the list of available input devices, `Enter` to switch, `Esc` to cancel. The active device is shown in the HUD at the top of the screen.

If no input device is available at startup, psysuals stays open in silent mode instead of crashing. The HUD shows `no input` until a device is selected successfully.

## Project structure

```
psysuals/
├── psysualizer.py            # Entry point — clean orchestrator
├── core/
│   ├── audio_engine.py       # Capture, FFT, beat & genre detection
│   ├── display_manager.py    # Monitors, X11, windowing, span mode
│   └── ui_manager.py         # HUD, pane, picker rendering
├── beat_tracking.py          # Optional librosa-based BPM/beat refinement
├── config.py                 # Shared mutable state
├── settings.py               # User settings persistence
├── gl_renderer.py            # Shared moderngl renderer utilities
├── requirements-gl.txt       # Optional moderngl dependency set
├── smoke_test.py             # Automated instantiation and import check
├── benchmarks.py             # Performance measurement tool
├── effects/
│   ├── __init__.py           # MODES list and package re-exports
│   ├── base.py               # Effect base class and contract
│   ├── utils.py              # Shared colour helpers
│   ├── palette.py            # Shared colour palette
│   └── (18 modes).py         # Visual implementations
├── ARCHITECTURE.md           # Code structure and extension guide
├── EFFECTS.md                # Full parameter reference for all effects
├── requirements.txt
└── README.md
```

## License

MIT
