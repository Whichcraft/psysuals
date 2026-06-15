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

## Hardware Acceleration (ModernGL)

The app supports hardware acceleration via the `--gl` flag. When enabled:
- The app uses ModernGL to offload heavy pixel calculations to the GPU.
- Effects like `Plasma` switch to a GLSL shader-based implementation.
- Other effects continue to draw to a transparent surface that is composited over the GL viewport each frame.
- A fallback system ensures that all effects remain functional even if ModernGL is not installed or the GPU path is disabled.

If no audio input stream is available, the app stays up and the effects simply run against silence until a device is selected.

Standardized audio energy parameters used across all effects:

| Signal | Source | Typical role |
|--------|--------|--------------|
| `beat` / `bass` | `beat` parameter | kick, sub, pulse, large-scale motion |
| `mid` | `config.MID_ENERGY` | synth body, geometry drift, colour motion, flight speed |
| `high` / `treble` | `config.TREBLE_ENERGY` | shimmer, edges, sparkles, fine detail, high-frequency jitter |

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
| 13 | `←` / `→` | FlowField | 12 000+ particles surfing a shifting vector field |
| 14 | `←` / `→` | Vortex | Feedback wormhole with fireworks |
| 15 | `←` / `→` | Aurora | Parallel Northern Lights ribbons with additive glow |
| 16 | `←` / `→` | Lattice | Crystal grid with zoom feedback and peak-normalization |
| 17 | `←` / `→` | Spectrum | Log-spaced analyser bars with waveform overlay |
| 18 | `←` / `→` | Waterfall | Scrolling time-frequency spectrogram |

`Spectrum` and `Waterfall` are intentionally the final two registry entries.

---

## 1. Yantra

Concentric polygon rings rotate in alternating directions around a bright central hub, with spokes and ring webs building a mandala-like lattice.

- Audio: beat (bass) drives the center dot expansion and ring spring-physics pulses; MID_ENERGY (mids) alternates ring rotations and drives spoke angular wobble; TREBLE_ENERGY (treble) adds high-frequency spoke/vertex jitters and modulates spoke/ring line thicknesses.
- Visual notes: long-lived geometry, strong symmetry, low camera motion, good for steady psytrance passages.

## 2. Cube

Two nested wireframe cubes rotate in 3-D while a pair of small satellite cubes orbit around them on separate trails.

- Audio: beat drives scale expansion and Y-axis rotation; MID_ENERGY drives X-axis rotation velocity and orbit speed; TREBLE_ENERGY drives Z-axis rotation speed, increases satellite rotation speed, and adds physical 3-D vertex jitter to the wireframe.
- Visual notes: the main app now uses the stable CPU implementation again; satellites keep their own persistent trail fade.

## 3. TriFlux

An equilateral triangle wall fills the screen with rainbow wireframe tiles. Selected tiles erupt into the foreground, spin, bounce, and then spring back into place.

- Audio: beat (bass) drives active-tile activation and basic scale pulsing; MID_ENERGY scales background sweep speeds and adds to active-tile scale/brightness; TREBLE_ENERGY accelerates active-tile spin rates and shimmers outline widths.
- Visual notes: two independent sweep bands cross the wall continuously, and the grid extends past screen edges so no clipped borders show.

## 4. Lissajous

A neon 3-D knot traces a dense trail with threefold rotational symmetry and a glowing head point.

- Audio: beat, MID_ENERGY, and TREBLE_ENERGY modulate the X, Y, and Z shape coefficients with reduced influence for a calmer, more fluid motion; MID_ENERGY gently increases rotation speed; TREBLE_ENERGY expands neon glow halos and shimmers trails and node circles.
- Visual notes: motion also reacts to live BPM, so faster tracks tighten and accelerate the knot. Rotation damping is tighter so the knot settles smoothly after beats.

## 5. Tunnel

A first-person ride through a curving polygon tube, with incoming triangles flying toward the viewer from the far end.

- Audio: beat (bass) increases tunnel travel velocity and ring flares; MID_ENERGY modestly drives obstacle spawn rates and rotation speeds; TREBLE_ENERGY drives camera path curvature wobble amplitude and central star size.
- Visual notes: the tube bends continuously, the nearest rings flare hard on strong kicks, and the triangle count is kept lean (max 30 live) so the mid-tunnel stays uncluttered.

## 6. Corridor

Rounded neon frames form a corridor that breathes toward the camera while sparks streak on a separate persistent layer above the geometry.

- Audio: beat drives frame speed and brightness; MID_ENERGY scales camera path sways and frame border inflates; TREBLE_ENERGY drives spark spawn rates, spark sizes, and brightness levels.
- Visual notes: the dedicated spark layer keeps the foreground trails readable instead of smearing them into the walls.

## 7. Nova

Waveform data is mirrored into a sevenfold kaleidoscope across four independently rotating layers.

- Audio: layers are driven by beat, MID_ENERGY, and TREBLE_ENERGY; MID_ENERGY scales layer rotation velocities and outer/inner shapes; TREBLE_ENERGY drives outer-ring radial triangle jitters and waveform line thicknesses.
- Visual notes: this mode is more waveform-shaped than FFT-shaped, so it shows snare and melodic contours clearly.

## 8. Spiral

Six luminous arms sweep toward the viewer as a helix, with cross-ring links tying the structure together into a rotating neon vortex.

- Audio: beat (bass) drives helix speed and spring expansions; MID_ENERGY drives camera path sways and helix radius breathing; TREBLE_ENERGY dynamically twists helix arms and sizes the connection rings.
- Visual notes: colour drift is more aggressive than most modes, which keeps long sessions from feeling static.

## 9. Bubbles

Hundreds of glowing translucent bubbles drift upward with layered halos, reflective highlights, and beat-synchronised global swelling.

- Audio: beat (bass) drives basic bubble scale pulsing, sizes, and mega-bubbles; MID_ENERGY speeds up ascent rates; TREBLE_ENERGY triggers additional bubble spawns and adds horizontal coordinate jitter (wobbles).
- Visual notes: strong beats can trigger exaggerated bloom and larger bubble events, making kicks feel like pressure waves.

## 10. Plasma

Four sine-wave fields interfere into a full-screen psychedelic texture. When running with `--gl`, this effect uses a GLSL fragment shader for per-pixel hardware acceleration.

- Audio: beat (bass) shifts hue and speeds up flow time; MID_ENERGY modulates interference wave density; TREBLE_ENERGY shifts brightness and speeds up cycles.
- Visual notes: this is the primary effect that takes advantage of the ModernGL path, providing high-performance fluid motion. A CPU fallback is automatically used if GL is not available.

## 11. Branches

A recursive lightning tree radiates from the screen centre with multiple branching levels and short trunk stubs, so the structure explodes outward immediately.

- Audio: beat (bass) drives trunk scale and extra arm counts; MID_ENERGY subtly drives branch sway angles and spreads; TREBLE_ENERGY adds modest high-frequency lightning jitter and small branch length decay ratios.
- Visual notes: the tree rotates slowly as a whole. Mid and treble reactivity is deliberately moderate so the structure stays readable even at high energy levels.

## 12. Butterflies

Up to three butterfly pairs move through the screen. A solo butterfly appears first, then a partner joins and the two chase each other in a tightening mutual orbit before occasionally breaking away to wander freely. Pairs come in two sizes: large (default) and small (roughly half the size), mixed in a large/small/large rotation.

- Audio: beat (bass) drives wing flapping speed and sparkle triggers; MID_ENERGY increases flight velocities and mutual orbit chase rates; TREBLE_ENERGY speeds up wing flaps and triggers dense close-proximity sparkle bursts.
- Visual notes: trails are managed on an internal surface so the effect survives backends that do not preserve the display backbuffer between frames. Wing-phase sync distance scales with each pair's butterfly size.

## 13. FlowField

Twelve thousand+ particles surf a continuously changing multi-layer vector field (scaling dynamically up to 50,000 on high-res displays) and paint the path they take directly into a persistent trail surface.

- Audio: beat (bass) drives particle speeds and field angle scales; MID_ENERGY accelerates field evolution; TREBLE_ENERGY triggers a vectorized center-outward push on particle positions during transients.
- Visual notes: particles that drift to within 8% of any screen edge are recycled back into a random position within the central 60% of the screen, keeping the flow concentrated and avoiding edge clustering.

## 14. Vortex

The previous frame is zoomed, rotated, and darkened into a wormhole while fireworks launch upward and explode into glowing embers.

- Audio: beat (bass) launches rockets and drives rotozoom scaling; MID_ENERGY accelerates feedback rotation rates; TREBLE_ENERGY dramatically increases rocket explosion ember counts, launch trail widths, and velocities.
- Visual notes: auto-launch timing is also tied to `config.EFFECT_GAIN`, so quieter gain settings create more background rockets between beats.

## 15. Aurora

Five translucent ribbon curtains sweep across the screen as thick parallel bands with additive overlap, bright edge lines, and a cyan-to-violet bias.

- Audio: beat (bass) controls ribbon amplitude and flash triggers; MID_ENERGY drives ribbon thickness and hue shifts; TREBLE_ENERGY drives curtain shimmer phase velocities.
- Visual notes: the effect uses harmonic ribbon stacks rather than particles, so it feels broad and atmospheric.

## 16. Lattice

A dynamic crystal grid of nodes and beams uses a center-out frequency mapping: center columns glow on bass, edge columns glow on treble, creating a symmetric bloom on beats. Grid density scales with display size (14×9 on 1080p, 18×12 on 1440p, 22×14 on 4K+). Features a zoom feedback tunnel and dynamic peak-normalization for balanced column activity.

- Audio: column activity is peak-normalized; beat drives shockwave expansion; MID_ENERGY drives grid feedback rotozoom scales; TREBLE_ENERGY shimmers node base radius and core brightness.
- Visual notes: node hue has a radial offset, so the centre stays cooler while the corners drift more violet. Bass hits now bloom symmetrically outward from both sides of centre.

## 17. Spectrum

Classic analyser bars are spaced logarithmically, with peak markers and a waveform line layered over the centre of the screen.

- Audio: per-bin FFT controls bar height; beat drives bar smoothing decay; MID_ENERGY shifts base hue; TREBLE_ENERGY modulates waveform overlay line thickness and vertical amplitude.
- Visual notes: this is the plainest diagnostic mode and is useful for checking input levels quickly.

## 18. Waterfall

A scrolling spectrogram stores recent history as rows, with hue encoding frequency and brightness encoding energy.

- Audio: FFT energy fills scrolling rows; beat/mids add row brightness boosts; TREBLE_ENERGY adds a heat-shimmer jitter/offset to newly scrolled rows.
- Visual notes: because it accumulates history, this is the best mode for spotting rhythmic patterns and sustained tonal bands.

## 17. Mycelium

A spreading fungal hyphal network: active tips grow outward leaving decaying filament segments behind. Beat triggers an explosive central bloom that spawns new tip clusters simultaneously.

- Audio: bass controls growth speed and reach; mid controls branching probability and angle spread; treble controls tip respawn rate; beat fires the central bloom burst.
- Visual notes: tips bias away from the screen centre, filling the periphery over time. Filaments fade individually as they age.

## 18. Magnetar

~6 000 particles ride the field lines of an analytically computed rotating magnetic dipole. Particles accumulate near the poles and trace luminous flux lines. Beat fires a shockwave that scatters particles outward from the magnetic equator.

- Audio: bass drives field rotation speed and particle velocity; mid shifts the dipole tilt angle; treble shifts particle colour saturation; beat triggers the equatorial shockwave.
- Visual notes: rendered at half resolution for performance. Particles are coloured by their angular position relative to the dipole axis, producing a continuous spectrum sweep.

## 19. SlimeMold

A Physarum-inspired multi-agent simulation: thousands of agents deposit chemical trail, sense three directions, and steer toward the strongest signal. The self-organising vein network pulses and reforms in real time.

- Audio: bass controls agent speed and trail deposit strength; mid sharpens gradient sensitivity; treble widens the sensor angle; beat teleports a fraction of agents back toward centre.
- Visual notes: runs at 1/4 resolution with approximate diffusion. Trail hue cycles slowly for a bioluminescent effect.

## 20. Droste

An Escher-style infinite recursive zoom portal: each frame the previous image is zoom-rotated inward, then spiralling geometric shapes are drawn on top and sucked into the vortex.

- Audio: bass drives zoom depth; mid drives rotation speed and shape complexity; treble brightens the overlay; beat triggers a zoom/rotation spike.
- Visual notes: runs at 1/3 resolution. The feedback loop is self-sustaining — shapes drawn each frame continually feed the tunnel.

## 21. Clifford

40 000 parallel walkers are iterated through the Clifford strange attractor each frame. Parameters (a, b, c, d) drift slowly at rest and snap to new values on strong beats, morphing the attractor shape in real time.

- Audio: beat jumps to new attractor parameters; mid accelerates parameter morphing; bass brightens points; treble cycles hue.
- Visual notes: rendered at half resolution with a long trail decay. On beat, the attractor dissolves and rebuilds in a new form.

## 22. Möbius

A 3-D Möbius strip rendered as a wireframe with perspective projection. Latitude and longitude lines sweep across the single face of the band as it rotates in 3-D. Beat fires a shiver that temporarily increases twist amplitude.

- Audio: bass controls rotation speed; mid controls roll/tilt speed; treble increases longitude line density; beat triggers the shiver.
- Visual notes: hue varies continuously along the strip width, highlighting the non-orientable topology.

## 23. Chromatic

Concentric ring waves expand from beat origins, splitting red, green, and blue channels outward by a treble-controlled pixel offset. Rings overlap additively, generating prismatic rainbow halos at intersection zones.

- Audio: bass controls expansion speed and ring intensity; mid drives hue drift; treble increases the RGB aberration split; beat spawns new rings.
- Visual notes: rendered at half resolution using BLEND_RGB_ADD for additive colour mixing. Multiple simultaneous rings create complex interference colours.

## 24. Persistence of Vision

Multiple nested polygons (triangle through decagon) rotate at slightly different speeds. With the long trail persistence (TRAIL_ALPHA = 5), ghost images accumulate and interfere, building wagon-wheel moiré illusions and mandala kaleidoscope patterns.

- Audio: bass drives rotation speed bursts; mid scales the number of active shapes; treble fires a radial flash ring; beat triggers a speed spike.
- Visual notes: the slower the music, the more complex the accumulated pattern. Let it run for 10+ seconds to see full moiré effects.

## 25. OilSlick

Two families of sine waves interfere across a full pixel grid, simulating the rainbow shimmer of an oil film. The interference value maps continuously to hue, producing flowing prismatic colour fields that shift with the music.

- Audio: bass adds a radial ripple from centre; mid scales spatial frequency; treble speeds up temporal shimmer; beat phase-jumps the pattern.
- Visual notes: runs at 1/4 resolution. The entire screen is re-rendered each frame as a vectorised NumPy operation.

## 26. Synapse

~55 nodes wired to their nearest neighbours form a neural graph. Signals travel visibly along edges as glowing pulses; arriving signals fire destination nodes which cascade further. Beat triggers multi-node cascades.

- Audio: bass drives signal propagation speed and node glow intensity; mid controls the baseline auto-fire rate; treble increases signal colour saturation; beat fires 1–4 random cascades.
- Visual notes: the baseline firing rate produces a gentle idle glow; strong beats produce branching light storms across the entire graph.

## 27. Coral

Iterative branch-tip growth produces upward-sweeping fractal coral structures from the bottom edge. Branch thickness tapers with depth; hue shifts along the colony. Beat fires a bioluminescent pulse that lights the whole structure at once.

- Audio: bass controls growth speed and stem length; mid controls branching angle spread; treble drives tip respawn rate; beat fires the bioluminescent bloom.
- Visual notes: distinct from Branches — Coral grows from the ground up with gravitropic bias, tapers naturally, and uses a much longer trail for accumulated colony density.

## 28. Heartbeat

Rhythmic pressure waves expand from the screen centre. Each beat spawns concentric rings whose outline morphs between a circle (gentle bass) and a polygon (heavy bass). Multiple overlapping rings create moiré interference patterns.

- Audio: bass drives wave speed and polygon morphing (low bass = circle, high bass = triangle); mid modulates propagation speed; treble adds shimmer; beat spawns new ring(s).
- Visual notes: strong beats at high bass produce stark polygonal shockwaves; gentle beats produce soft circular ripples. Rings are drawn with polygon outlines for smooth morphing.

---

## Navigation

| Key | Action |
|-----|--------|
| `1` – `9` | Jump directly to modes 1–9 |
| `←` / `→` | Previous / next mode across all 30 modes |
| `Space` or mouse click | Next mode |
| `↑` / `↓` | Adjust intensity for the current mode (`0.0 .. 2.0`) |
| `Tab` | Open the settings pane |
| `P` / `Shift+P` | Save / load presets |
| `D` | Open the device picker, or cycle the shared secondary-display mode while span mode is active |
| `F` | Toggle fullscreen |
| `H` / `Shift+H` | Toggle HUD / change HUD detail |
| `Q` / `Esc` | Quit |

Mode changes reset intensity to the default `0.7`. Loading a preset can restore a saved custom intensity on purpose.
