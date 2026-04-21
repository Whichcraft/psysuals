# psysuals — Effects Reference

All effects consume the same shared audio signals. They differ only in how they interpret those signals visually.

---

## Global audio signals

| Signal | Meaning | Source |
|--------|---------|--------|
| `waveform` | Latest raw mono PCM block (`1024` samples) | `sounddevice` callback |
| `fft` | Smoothed, log-scaled spectrum (`512` bins) | Blackman-windowed FFT + EMA |
| `beat` | Normalised beat impulse (`0.0 .. 3.0`) | Spectral flux, optional tracker refinement, main-loop decay |
| `config.MID_ENERGY` | Normalised mid-band energy | Smoothed bins `20..99` |
| `config.TREBLE_ENERGY` | Normalised treble energy | Smoothed bins `100..255` |
| `config.BPM` | Live BPM estimate or tap-tempo override | Callback onset timing + optional `librosa` refinement |

`effect_gain` scales only the foreground beat response. Current default is `0.7`, and changing modes resets it back to that default.

If no audio input stream is available, the app stays up and the effects simply run against silence until a device is selected.

Common band splits used in most effects:

| Band | Bins | Typical role |
|------|------|--------------|
| bass | `fft[:6]` | kick, sub, pulse, large-scale motion |
| mid | `fft[6:30]` | synth body, geometry drift, colour motion |
| high | `fft[30:]` | shimmer, edges, sparks, fine detail |

---

## Mode list

| # | Key | Mode | Summary |
|---|-----|------|---------|
| 1 | `1` | Yantra | Sacred-geometry mandala with springy concentric rings |
| 2 | `2` | Cube | Dual wireframe cubes with orbiting satellites |
| 3 | `3` | TriFlux | Triangle mosaic wall with popping foreground tiles |
| 4 | `4` | Lissajous | 3-D knot with neon trail and BPM-sensitive motion |
| 5 | `5` | Tunnel | Curving polygon tube rushing toward the camera |
| 6 | `6` | Corridor | Neon rounded-rectangle corridor with sparks |
| 7 | `7` | Nova | Waveform kaleidoscope with layered symmetry |
| 8 | `8` | Spiral | Multi-arm helix vortex with cross-ring links |
| 9 | `9` | Bubbles | Rising translucent bubbles with global pulse swells |
| 10 | `←` / `→` | Plasma | Full-screen sine-interference plasma |
| 11 | `←` / `→` | Branches | Fractal lightning tree with audio-jittered angles |
| 12 | `←` / `→` | Butterflies | Dancing butterfly pairs with orbit breaks |
| 13 | `←` / `→` | FlowField | 4 000 particles surfing a shifting vector field |
| 14 | `←` / `→` | Vortex | Feedback wormhole with fireworks |
| 15 | `←` / `→` | Aurora | Northern Lights ribbons with additive glow |
| 16 | `←` / `→` | Lattice | Crystal grid mapped across the spectrum |
| 17 | `←` / `→` | Spectrum | Log-spaced analyser bars with waveform overlay |
| 18 | `←` / `→` | Waterfall | Scrolling time-frequency spectrogram |

`Spectrum` and `Waterfall` are intentionally the final two registry entries.

---

## 1. Yantra

Concentric polygon rings rotate in alternating directions around a bright central hub, with spokes and ring webs building a mandala-like lattice.

- Audio: bass enlarges the centre dot, mid makes the spokes wobble, beat kicks all rings outward through a spring system.
- Visual notes: long-lived geometry, strong symmetry, low camera motion, good for steady psytrance passages.

## 2. Cube

Two nested wireframe cubes rotate in 3-D while a pair of small satellite cubes orbit around them on separate trails.

- Audio: bass, mid, and high drive different rotation axes; beat adds a capped scale burst and brighter edges.
- Visual notes: the main app now uses the stable CPU implementation again; satellites keep their own persistent trail fade.

## 3. TriFlux

An equilateral triangle wall fills the screen with rainbow wireframe tiles. Selected tiles erupt into the foreground, spin, bounce, and then spring back into place.

- Audio: bass raises the active-tile scale target, while bass+beat activates tiles or extends their life.
- Visual notes: two independent sweep bands cross the wall continuously, and the grid extends past screen edges so no clipped borders show.

## 4. Lissajous

A neon 3-D knot traces a dense trail with threefold rotational symmetry and a glowing head point.

- Audio: bass, mid, and high drive the X/Y/Z frequencies; beat kicks scale, hue drift, and extra glow.
- Visual notes: motion also reacts to live BPM, so faster tracks tighten and accelerate the knot.

## 5. Tunnel

A first-person ride through a curving polygon tube, with incoming triangles flying toward the viewer from the far end.

- Audio: bass and beat increase travel speed and triangle spawn pressure; per-ring FFT energy modulates ring brightness.
- Visual notes: the tube bends continuously, and the nearest rings flare hard on strong kicks.

## 6. Corridor

Rounded neon frames form a corridor that breathes toward the camera while sparks streak on a separate persistent layer above the geometry.

- Audio: bass and beat increase corridor speed and spark emission; FFT energy brightens individual frames.
- Visual notes: the dedicated spark layer keeps the foreground trails readable instead of smearing them into the walls.

## 7. Nova

Waveform data is mirrored into a sevenfold kaleidoscope across four independently rotating layers.

- Audio: each layer is assigned a different band mix; beat bursts all layers outward together.
- Visual notes: this mode is more waveform-shaped than FFT-shaped, so it shows snare and melodic contours clearly.

## 8. Spiral

Six luminous arms sweep toward the viewer as a helix, with cross-ring links tying the structure together into a rotating neon vortex.

- Audio: bass raises transport speed, depth-varying FFT energy changes arm radius, beat adds a spring burst and near-field flash.
- Visual notes: colour drift is more aggressive than most modes, which keeps long sessions from feeling static.

## 9. Bubbles

Hundreds of glowing translucent bubbles drift upward with layered halos, reflective highlights, and beat-synchronised global swelling.

- Audio: bass increases spawn rate, spawn size, and ascent speed; mid broadens display radius; beat swells the full pool.
- Visual notes: strong beats can trigger exaggerated bloom and larger bubble events, making kicks feel like pressure waves.

## 10. Plasma

Four sine-wave fields interfere into a full-screen psychedelic texture rendered at reduced resolution and scaled up for speed.

- Audio: bass shifts hue and flow speed, mid changes wave density, high adds brightness, beat flashes the whole frame.
- Visual notes: this is the closest thing to a pure fullscreen shader look in the CPU path.

## 11. Branches

A recursive lightning tree radiates from the screen centre with multiple branching levels and short trunk stubs, so the structure explodes outward immediately.

- Audio: bass changes trunk length and animation speed, mid jitters branch angles, high changes branch ratio and brightness, beat adds extra arms.
- Visual notes: the tree rotates slowly as a whole, but the branch jitter provides most of the motion.

## 12. Butterflies

Up to three butterfly pairs move through the screen. A solo butterfly appears first, then a partner joins and the two chase each other in a tightening orbit before occasionally breaking away.

- Audio: bass raises flight speed, beat adds wing energy and sparkle accents, and the overall hue drifts with the music.
- Visual notes: trails are managed on an internal surface so the effect survives backends that do not preserve the display backbuffer between frames.

## 13. FlowField

Four thousand particles surf a continuously changing multi-layer vector field and paint the path they take directly into a persistent trail surface.

- Audio: bass gently pulls particles toward the screen centre, treble scatters them outward, beat phase-jumps the field and adds a speed boost.
- Visual notes: this mode responds strongly to hats and cymbals because treble physically disperses the particles.

## 14. Vortex

The previous frame is zoomed, rotated, and darkened into a wormhole while fireworks launch upward and explode into glowing embers.

- Audio: beat launches extra rockets and boosts the feedback transform; bass nudges hue and tunnel strength.
- Visual notes: auto-launch timing is also tied to `config.EFFECT_GAIN`, so quieter gain settings create more background rockets between beats.

## 15. Aurora

Five translucent ribbon curtains sweep across the screen with additive overlap, bright edge lines, and a cyan-to-violet bias.

- Audio: bass controls ribbon amplitude, mid changes ribbon thickness, treble drives shimmer speed, beat triggers bloom flashes and hue nudges.
- Visual notes: the effect uses harmonic ribbon stacks rather than particles, so it feels broad and atmospheric.

## 16. Lattice

A `14 × 9` crystal grid of nodes and beams maps low frequencies to the left and higher frequencies to the right, with a shockwave travelling outward from the centre on beats.

- Audio: per-column FFT energy brightens nodes and beams, bass adds a subtle whole-grid scale breath, beat launches the shockwave ring.
- Visual notes: node hue has a radial offset, so the centre stays cooler while the corners drift more violet.

## 17. Spectrum

Classic analyser bars are spaced logarithmically, with peak markers and a waveform line layered over the centre of the screen.

- Audio: per-bin FFT controls bar height, beat temporarily increases the bar smoothing rate so peaks snap harder, waveform draws the overlay line directly.
- Visual notes: this is the plainest diagnostic mode and is useful for checking input levels quickly.

## 18. Waterfall

A scrolling spectrogram stores recent history as rows, with hue encoding frequency and brightness encoding energy.

- Audio: FFT energy fills the newest row, beat adds a brightness flash to the leading edge, and time pushes older rows downward.
- Visual notes: because it accumulates history, this is the best mode for spotting rhythmic patterns and sustained tonal bands.

---

## Navigation

| Key | Action |
|-----|--------|
| `1` – `9` | Jump directly to modes 1–9 |
| `←` / `→` | Previous / next mode across all 18 modes |
| `Space` or mouse click | Next mode |
| `↑` / `↓` | Adjust intensity for the current mode (`0.0 .. 2.0`) |
| `Tab` | Open the settings pane |
| `P` / `Shift+P` | Save / load presets |
| `D` | Open the device picker, or cycle the shared secondary-display mode while span mode is active |
| `F` | Toggle fullscreen |
| `H` / `Shift+H` | Toggle HUD / change HUD detail |
| `Q` / `Esc` | Quit |

Mode changes reset intensity to the default `0.7`. Loading a preset can restore a saved custom intensity on purpose.
