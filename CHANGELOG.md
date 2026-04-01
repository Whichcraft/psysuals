# Changelog

All notable changes to psysuals are documented here.
Versions follow [Semantic Versioning](https://semver.org/).

---

## [1.6.5] — 2026-04-01

### Changes
- **TriFlux** — effect renamed from TriWall to TriFlux everywhere (class file `triflux.py`, mode name, docs)
- **TriFlux** — activation now bass-beat triggered (`beat > 0.2 AND bass > 0.25`); max simultaneous active tiles raised 2 → 3
- **TriFlux** — active lifetime is now random per activation: 1–6 s (`ACTIVE_LIFE_MIN=60`, `ACTIVE_LIFE_MAX=360`)
- **TriFlux** — `MIN_LIFE` set to 60 frames (1 s); beats that fire while slots are full extend existing tiles' remaining life to at least `MIN_LIFE`
- **TriFlux** — vertex coordinates clamped to ±16383 (SDL safe range) to prevent `TypeError: points must be number pairs` on extreme scale values; active tile scale capped at 12.0
- **TriFlux** — two independent rainbow sweeps (vel 3.2 and 4.1 px/frame, staggered start) so at least one is crossing the screen at all times
- **Mode order** — TriFlux on key `3`; Plasma moved to ←/→ only
- **Docs** — EFFECTS.md fully rewritten with correct section order, updated TriFlux parameter table, all mode numbers corrected; README and project structure updated

---

## [1.6.4] — 2026-04-01

### Changes
- **TriFlux** — active tiles now bounce off screen edges: centroid velocity is reflected and the tile is pushed back inside when any vertex crosses a boundary; no vertex ever leaves the screen
- **TriFlux** — rainbow sweep draw order fixed: sweep glow now renders before tile fill and rainbow edges so edges always show on top; sweep brightness raised

---

## [1.6.3] — 2026-04-01

### Changes
- **Effects order** — TriFlux moved to slot 3 (`3` key); Plasma moved to ←/→ only

---

## [1.6.2] — 2026-04-01

### Changes
- **TriFlux** — active tiles now drift their centroid toward screen centre while alive so even large bass-pulsed tiles (up to 8.5×) never clip the screen edges; on fallback the centroid springs back to its home grid position before the tile snaps in
- Renamed `effects/attractor.py` → `effects/triflux.py`

---

## [1.6.1] — 2026-04-01

### Changes
- **TriFlux** — fallen-back tiles now spring their rotation to 0° so they snap back into grid alignment
- **TriFlux** — rainbow sweep: a glowing wave at a random angle (left-to-right, diagonal, etc.) sweeps across all triangles continuously, cycling through the rainbow; picks a new angle each pass
- **TriFlux** — active tiles pulse harder to bass: target scale raised from `4.5 + bass×1.8` to `4.5 + bass×4.0` (up to ~8.5× on strong bass beat); spring stiffness increased for snappier response

---

## [1.6.0] — 2026-04-01

### Features
- **Attractor** (mode 10) — Lorenz strange attractor; single particle traces the chaotic butterfly trajectory on a dedicated slow-fade surface (alpha 4) so the full double-wing accumulates over time; bass warps sigma, beat kicks rho, slow Y-axis rotation gives 3-D depth
- **Branches** (mode 11) — recursive fractal lightning tree; 6 arms from centre split to depth 6 (64+ tips); mid frequencies jitter every branch angle live; bass drives trunk length; beat fires extra arms with a brightness burst
- Spectrum and Waterfall shifted to modes 12/13; number key `0` removed (use ←/→ for modes 10+)
- All docs updated: EFFECTS.md, README.md

---

## [1.5.0] — 2026-04-01

### Version bump
- Minor version bump: consolidates recent feature additions (Tunnel spark layer, Cube satellite trails, mode reordering)

---

## [1.4.3] — 2026-04-01

### Changes
- **Tunnel** — sparks now rendered on a dedicated persistent layer (fade alpha 10) always composited above tunnel geometry; fewer sparks spawn; trails are significantly longer; bass drives tube radius, ring width, triangle size, and tunnel speed more aggressively
- **Cube** — satellite cubes now leave long trailing lines via a dedicated persistent surface (fade alpha 8) composited with additive blend on top of the main cubes; satellites start at reduced intensity and brighten with energy
- **Effects order** — Lissajous moved to slot 4 (`4` key), Tunnel moved to slot 5 (`5` key); all docs updated to match

---

## [1.4.2] — 2026-04-01

### Fixes
- **Cube** — satellite cubes no longer distort; each satellite is projected from its orbit centre with a uniform screen-space scale so all edges remain square regardless of rotation
- **Cube** — satellite cubes are clamped to stay fully within screen boundaries at all times

---

## [1.4.1] — 2026-04-01

### Fixes
- **Corridor** — sparks now always stay inside the tunnel; `ox`/`oy` offsets are bounded to corridor half-extents and spark path centre tracks the corridor frame at the same depth
- **Corridor** — frames and sparks are now depth-sorted together (back-to-front) so near frames can no longer paint over nearer sparks

---

## [1.4.0] — 2026-04-01

### Features
- **Corridor** (mode 6) — first-person neon rainbow corridor; concentric rounded-rectangle frames fly toward the camera with a full rainbow sweep across depth; beat flares nearest frames and spawns glowing sparks; path curves gently over time

### Refactor
- Modularised codebase: `psysualizer.py` reduced from 1383 → 245 lines; each effect moved to its own file under `effects/`; shared colour helpers extracted to `effects/utils.py`; display constants live in `config.py`
- Added `ARCHITECTURE.md` documenting code structure and the effect extension pattern

---

## [1.3.0] — 2026-03-26

Backport of tuning improvements from the AndroSaver fork.

### Audio engine
- FFT smoothing: 0.75 → 0.50 for faster audio reaction
- Energy history window: 30 → 15 frames for snappier beat detection

### Mode tuning
- **Yantra** — ~1.5× beat reactivity on ring pulse, brightness, spoke reach, and opacity; centre dot substantially reduced
- **Cube** — 2× beat reactivity on rotation; base spin ~65% faster; scale pulse driven by both beat + bass; longer trails (slower fade)
- **Plasma** — idle time increment reduced ~60% for a slower, calmer default
- **Tunnel** — default speed/reactivity reduced; path swing reduced; tube radius increased so viewer stays inside; triangle burst larger on bass hits; spawn count now continuous (bass + beat); triangle cap 80 → 120
- **Lissajous** — across-the-board reactivity reduction: trace speed, phase drift, frequency drift, scale burst, rotation inertia, hue jump
- **Nova** — replaced oversized centre circle with two counter-rotating rings of 3 triangles each; beat energy redistributed to rings and brightness
- **Bubbles** — initial pool 400 → 200; beat spawn capped at 1.0 to prevent flooding; extra neon rings only appear at beat > 1.0; wider hue spread at high intensity
- **Spectrum** — smoothed display buffer added; lerp speed scales 0.25 (silence) → 1.0 (full beat)
- **Waterfall** — minimum lightness floor (no black tiles); removed low-energy skip (all bins always rendered)

---

## [1.2.0] — 2026-03-25

### Features
- **Arrow-key navigation** — `←`/`→` scroll through visualisation modes; `↑`/`↓` increase/decrease effect intensity (beat-response gain, 0.0–2.0, default 1.0)
- HUD now shows current effect intensity alongside mode name and device

---

## [1.1.0] — 2026-03-24

### Performance
- Vectorised hot paths; ~40% reduction in per-frame Python overhead

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
