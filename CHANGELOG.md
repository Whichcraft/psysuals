# Changelog

All notable changes to psysuals are documented here.
Versions follow [Semantic Versioning](https://semver.org/).

---

## [2.6.0] — 2026-04-11

### Added
- **Presets** — `P` saves current mode/intensity/background as a named preset to `~/.config/psysuals/presets.json`; `Shift+P` cycles through saved presets; active preset name shown in the HUD
- **Real-time settings pane** — `Tab` opens a right-side overlay; `↑`/`↓` navigate three sliders (effect gain, background alpha, crossfade frames); `←`/`→` adjust the selected slider while visuals keep playing; values persist on quit
- **Span mode** (`Shift+M`) — stretches the window across all connected monitors using the full virtual desktop dimensions; `Shift+M` again restores single-display mode
- **HUD detail levels** — `Shift+H` cycles full / minimal / off; full shows all rows and bars; minimal shows only mode name and BPM; `H` still toggles on/off as before
- **Multi-band vertical bars** — three 8 px wide bars anchored to the bottom-left corner visualise real-time bass (red), mid (green), and treble (purple) energy whenever the HUD is visible

### Changed
- Background layer alpha is now user-configurable via the settings pane (default 102, ~40 %)
- Crossfade duration is now user-configurable via the settings pane (default 45 frames)
- `settings.py` gains `load_presets()`, `save_preset()`, `delete_preset()` for preset persistence

---

## [2.5.0] — 2026-04-11

### Added
- **Particles** — new `RhythmicParticles` effect: beat bursts from screen centre, continuous trickle driven by treble energy, hue drifts with mid energy; uses numpy batch rendering with pre-rendered blit cache for performance
- **BPM detection** — onset timestamps tracked in the audio callback; median inter-beat interval gives a live BPM estimate (60–200) exposed as `config.BPM` and shown in the HUD
- **Multi-band energy** — `config.MID_ENERGY` (bins 20–100, ~860 Hz–4.3 kHz) and `config.TREBLE_ENERGY` (bins 100–256, ~4.3–11 kHz) computed and normalised each frame; effects can read these directly
- **Shared palette** (`effects/palette.py`) — module-level singleton whose base hue drifts with mid energy and whose saturation/lightness track beat/treble; effects opt in via `palette.get(offset)`
- **Crossfade on mode switch** — 45-frame dissolve overlay when switching effects
- **Background layer** — `B` toggles a second effect rendered at 40 % alpha beneath the foreground; `Shift+B` cycles the background effect through modes 1–9
- **Auto-gain** (`A`) — rolling RMS of the waveform auto-scales beat intensity to stay reactive at any playback volume
- **Multi-screen support** — `--display N` CLI flag launches on a specific display; `M` key cycles to the next display at runtime; graceful fallback if RANDR is unavailable
- **Settings persistence** (`settings.py`) — device, mode, intensity, HUD, auto-gain, background state, and display index saved to `~/.config/psysuals/settings.json` and restored on next launch
- **Enhanced HUD** — second row with live BPM, colour-coded energy bars (beat / mid / treble), particle count when Particles effect is active

### Changed
- **Blackman window** replaces Hann window for better spectral leakage suppression
- **Spectral flux beat detection** replaces simple energy averaging — beat signal now tracks the positive rate of change in the bass spectrum, giving sharper and more accurate kick response
- `config.py` now exports `MID_ENERGY`, `TREBLE_ENERGY`, `BPM` as shared mutable globals

---

## [2.4.0] — 2026-04-05

### Fixed
- **Butterflies — edge sticking**: avoidance margin was `110 × scale` (792 px at scale 7.2, larger than half the screen height), putting butterflies permanently in boundary mode and causing them to fight themselves; margin is now `min(50 × scale, WIDTH/5, HEIGHT/5)`; repulsion is proportional and directly bumps position away from the wall rather than only steering heading
- **Butterflies — Android trails**: `TRAIL_ALPHA` changed from 22 to 0; effect now owns a persistent `_trail` surface faded each frame with `BLEND_RGB_MULT`, so trails survive on Android/OpenGL backends where the display backbuffer is not preserved between frames

---

## [2.3.0] — 2026-04-05

### Changed
- **FlowField** — replaces RxDiffusion: 4 000 particles riding a 3-layer sine/cosine noise field; rainbow trails via direct numpy pixel writes on a slow-fade surface; bass warps field intensity; beat phase-jumps all flow lines
- **Vortex** — rewritten with fireworks: rockets launch from the bottom, arc under gravity, explode into 80–120 embers at apex; embers fall with gravity; feedback wormhole swallows all trails; beat fires extra rockets

---

## [2.2.0] — 2026-04-05

### Added
- **FlowField** — 4 000 particles riding a 3-layer sine/cosine noise field; particles paint rainbow trails via direct numpy pixel writes on a slow-fade surface; bass warps field intensity and speed; beat fires a phase jump reshaping all flow lines instantly
- **Vortex** — pixel feedback wormhole: each frame zoom-rotated (1.0038×, 0.42°/frame) and multiplied dark; firework rockets launch from the bottom edge, arc under gravity, explode into 80–120 embers at apex; embers fall with gravity; beat fires extra rockets and ramps zoom/rotation for 50 frames
- **Bug fix**: `_detect_accum` added to `global` declaration in `_audio_cb` (was raising `UnboundLocalError` during genre detection)

---

## [2.1.0] — 2026-04-03

### Added
- **Butterflies** — three independent pairs: each solo butterfly flutters in first, its partner joins after 10–30 s and orbits lovingly; wing flapping syncs when close; sparkles on the beat; pairs vanish and respawn continuously

---

## [2.0.5] — 2026-04-03

### Added
- **Auto genre detection** — accumulates FFT spectrum over ~300 frames and classifies into Electronic / Rock / Classical / Any; applies genre-specific bass-bin weights to beat energy; HUD shows current detected genre; re-detects every ~300 frames so it adapts as music changes

---

## [2.0.4] — 2026-04-01

### Bug fixes
- **Cube**: restore beat scale bump — cube pulses on kick but scale is capped at 1.25× so it never grows large at high intensity; spring always restores to 1.0 between beats

---

## [2.0.3] — 2026-04-01

### Changes
- **Cube**: scale no longer grows on beat/bass; beat/bass now only drive rotation speed and edge brightness
- **Yantra**: initial rotation speed ~2.5× faster; rings tighter (span 28–90% of max radius); 7th ring added
- **Tunnel**: center polygon size halved (0.52 → 0.24 × ring radius); triangle spawn rate doubled for bass and beats
- **Branches**: trunk stub halved (0.03 → 0.015 × arm length) for a denser ball-like canopy from centre

---

## [2.0.2] — 2026-04-01

### Bug fixes
- **Cube**: inner cube rotation velocity capped at ±0.08 rad/frame (x/y) and ±0.05 (z) to prevent runaway spinning on strong beats
- **Cube**: satellite trail length halved (`_SAT_FADE` 8 → 16)

---

## [2.0.1] — 2026-04-01

### Bug fixes
- **Branches**: trunk stub shortened to 3% of arm length so the first fork appears right at the centre; overall tree size unchanged
- **Branches**: hard cap on trunk length (`sc × 0.27`) so branches never leave the screen
- **TriFlux**: rainbow sweep now always enters from the real screen edge — computes the minimum projection of screen corners onto the sweep direction, never starts mid-screen
- **TriFlux**: grid extended one tile outside all four screen edges so no clipped triangle edges are visible at the borders

---

## [2.0.0] — 2026-04-01

### Three spectacular new effects

This is a landmark release. psysuals 2.0.0 ships three completely new visual effects that push the reactive experience to another level — each one a different flavour of audio-driven madness, each one impossible to look away from.

#### TriFlux (key `3`)
The wall is alive. An equilateral triangle mosaic fills the screen with wireframe tiles, their edges blazing with per-angle rainbow colour. On every bass kick, up to three tiles explode to the foreground — growing up to 8× their size, spinning, bouncing off screen edges — before springing back into perfect grid alignment. Two independent rainbow sweep waves wash across the whole wall at constantly changing angles. Every tile glows. Everything reacts. The grid breathes.

Technical highlights: per-tile spring physics (scale + rotation + centroid position), vertex-level screen-edge bounce with velocity reflection, dual sweep layers at staggered positions and independent angles, interior-only activation with 1.5-tile-width margin, guaranteed 2.5–6 s active lifetime per tile, vertex coordinate clamping for SDL stability.

#### Branches (←/→)
Six neon lightning arms fractal-split from screen centre to depth 6, generating 64+ electric tips per arm. Every branch angle jitters live to the mid frequencies — the whole tree writhes with the music. Bass drives trunk length; strong beats fire extra arms and flood the screen with a brightness burst. The structure rotates slowly, never settling.

Technical highlights: depth-6 recursive branching with Y-fork at trunk level, separate draw length for trunk segment (15% of length) while children receive full extent so the tree fills the screen, mid-driven per-branch angle jitter using overlapping sine functions, beat-flash decay envelope.

#### Corridor (key `6`)
A first-person ride through a neon rainbow tunnel of rounded-rectangle frames rushing toward the camera. The path curves sinusoidally. Beat flares the nearest frames and erupts a shower of sparks that streak toward you on their own independent trail layer — sparks always burn above the geometry, never buried behind it.

Technical highlights: two-surface compositing (corridor layer fade α=28, spark layer fade α=10, blitted with `BLEND_ADD` for additive glow), perspective-correct rounded-rect frames, per-frame FFT bin brightness mapping.

### All changes
- **TriFlux**: activation on bass beat (`beat > 0.2 AND bass > 0.25`), max 3 simultaneous active tiles, random lifetime 2.5–6 s, spring-back grid alignment, bounce physics, dual rainbow sweeps
- **TriFlux**: vertex SDL clamp ±16383, scale cap 12.0, `ACTIVE_LIFE_MIN` raised to 150 frames to guarantee 1 s of fully-expanded big-phase
- **Mode order**: TriFlux on key `3`; Plasma moved to ←/→ only
- **EFFECTS.md**: complete rewrite with correct section order and full TriFlux parameter table
- **File**: `effects/attractor.py` → `effects/triflux.py`

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
