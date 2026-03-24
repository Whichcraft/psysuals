# Changelog

All notable changes to psysuals are documented here.
Versions follow [Semantic Versioning](https://semver.org/).

---

## [1.0.0] — 2026-03-24

First stable release. Ten visualisation modes, all tuned for psytrance (138–148 BPM).

### Visualisation modes
- **Yantra** — Psychedelic sacred-geometry mandala with 6 concentric polygon rings, web connections, neon spokes, and beat-driven spring pulses
- **Cube** — Dual wireframe cubes with slow graceful rotation and spectrum colour-fade
- **Plasma** — Full-screen sine-interference plasma with four overlapping wave fields
- **Tunnel** — First-person ride through a curving neon tube; beat spawns triangles that fly toward the camera
- **Lissajous** — 3-D trefoil Lissajous knot with two-pass neon glow and hard beat spring burst
- **Nova** — Waveform kaleidoscope with 7-fold mirror symmetry across 4 spinning layers
- **Spiral** — Neon helix vortex with 6 arms, audio-reactive radius breathing, cross-ring polygon connections
- **Bubbles** — Translucent full-screen rising bubbles driven by bass energy; synchronized beat pulse
- **Spectrum** — Log-spaced spectrum analyser with peak markers and waveform overlay
- **Waterfall** — Scrolling time-frequency spectrogram; beat flashes the leading edge

### Features
- Real-time audio capture via `sounddevice` with configurable input device
- Interactive in-app device picker (D key)
- Beat detection via bass-band energy with per-mode spring physics
- Fullscreen-first launch with toggle (F key)
- HUD/legend overlay with toggle (H key)
- Number keys 1–9 and 0 to jump directly to any mode
- Window caption and HUD show current mode, device, and controls
