# Psysualizer — Effects Reference

All effects share a common audio pipeline. Each effect responds to the same audio signals but visualizes them differently.

---

## Global Audio Signals

| Signal | Description | Source |
|--------|-------------|--------|
| `bass` | Average energy of FFT bins 0–5 (~0–259 Hz) | Normalized by 15-frame moving average |
| `mid` | Average energy of FFT bins 6–29 (~259–1.3 kHz) | — |
| `high` | Average energy of FFT bins 30+ (~1.3 kHz+) | — |
| `beat` | Detected beat intensity [0.0+] | Bass energy spike detection |
| `fft[]` | Full smoothed spectrum (512 bins) | Exponential moving avg, factor 0.50 |
| `waveform` | Raw audio samples (1024 points) | Mono, 44100 Hz |

**Effect Gain** — user-adjustable multiplier [0.0–2.0] applied to beat response (arrow keys ↑↓ in-app).

---

## Effect List

| # | Key | Name | Description |
|---|-----|------|-------------|
| 1 | `1` | Yantra | Sacred geometry mandala with concentric polygon rings |
| 2 | `2` | Cube | Rotating wireframe cubes with orbiting satellites |
| 3 | `3` | TriFlux | Equilateral triangle mosaic — rainbow wireframe wall with bass-reactive tiles that pop forward, bounce, and sweep with colour |
| 4 | `4` | Lissajous | 3-D Lissajous knot with 3-fold symmetry |
| 5 | `5` | Tunnel | First-person ride through a curving tube |
| 6 | `6` | Corridor | Neon rainbow corridor — rounded-rectangle frames flying toward camera |
| 7 | `7` | Nova | Waveform kaleidoscope with 7-fold mirror symmetry |
| 8 | `8` | Spiral | Neon helix vortex with 6 arms flying toward viewer |
| 9 | `9` | Bubbles | Translucent rising bubbles, size driven by bass |
| — | ←/→ only | Plasma | Full-screen sine-interference psychedelic texture |
| — | ←/→ only | Branches | Recursive fractal lightning tree — 6 arms, depth 6, audio-jittered angles |
| — | ←/→ only | Spectrum | Classic spectrum bars with peak markers and waveform overlay |
| — | ←/→ only | Waterfall | Scrolling spectrogram (time-frequency display) |

---

## 1. Yantra

Psychedelic sacred-geometry mandala. Six concentric polygon rings (triangle through octagon) rotate in alternating directions with audio-driven spring perturbations. Neon spokes radiate from center; web lines connect adjacent ring vertices.

### Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `N_RINGS` | `6` | Number of concentric polygon rings |
| `N_SPOKES` | `24` | Radial lines from center |
| Ring sizes | `max_r * (0.13 + i/(N_RINGS-1) * 0.83)` | Linearly spaced |
| Rotation velocity (per ring) | `±(0.004 + i * 0.0018)` rad/frame | Alternating direction |
| Spring restore force | `–poff[i] * 0.22` | Per ring |
| Spring damping | `0.65` | — |
| Beat spring kick | `0.36 + energy * 0.18` | Energy-dependent |
| Hue drift | `0.005` per frame | Continuous cycling |
| Spoke wiggle amplitude | `0.05 + mid * 0.10` | Mid-band driven |
| Central dot radius | `4 + bass * 12 + beat * 10` px | — |
| Spoke width | `beat * 3.75` | Beat driven |

### Audio Reactions
- **Bass** → central dot size
- **Mid** → spoke wiggle amplitude
- **Beat** → spring kick on all rings, spoke width, dot size

---

## 2. Cube

Dual rotating wireframe cubes (main + inner at 45% scale) with 2 orbiting satellite cubes. Satellite count is fixed; satellites have their own slow independent rotation. Two-pass neon glow on edges.

### Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `TRAIL_ALPHA` | `18` | Main cube fade speed; lower = longer trails |
| `_SAT_FADE` | `16` | Satellite trail fade speed; lower = longer trails |
| Satellite count | `2` (fixed) | Independent slow rotation |
| Orbital radius | `2.6` 3-D units | — |
| Satellite scale | `min(main_scale * 0.28, 0.55)` | Capped to prevent overflow |
| Inner cube scale | `main_scale * 0.45` | — |
| FOV | `680` units | — |
| Rotation damping | `0.94` | Per axis |
| Rotation velocity cap | `±0.08` rad/frame (x/y), `±0.05` (z) | Prevents runaway spin |
| X-axis angular accel | `0.00165 + mid * 0.012 + beat * 0.10` | — |
| Y-axis angular accel | `0.00248 + bass * 0.015 + beat * 0.12` | — |
| Z-axis angular accel | `0.00083 + high * 0.008 + beat * 0.05` | — |
| Scale spring kick | `beat * 0.32 + bass * 0.20` | — |
| Scale restore | `(1.0 – scale) * 0.18` | — |
| Scale damping | `0.68` | — |
| Minimum scale | `0.5` | — |
| Edge width | `max(1, int(2 + svel * 4))` px | Scale-velocity driven |

### Audio Reactions
- **Bass** → Y-axis spin, scale kick
- **Mid** → X-axis spin
- **High** → Z-axis spin
- **Beat** → all axes, scale burst

---

## 3. TriFlux

Equilateral triangle mosaic wall. All triangles are wireframe with per-edge rainbow colours. A subset of 4–6 tiles are filled. On bass beats, an interior tile pops to the foreground at up to 8× size, spins, pulses to bass, and bounces off screen edges — then springs back into grid alignment. Two independent rainbow sweep waves cross the wall at random angles continuously. The grid extends one tile past all screen edges so no clipped triangle borders are visible. Each sweep always enters from the real screen edge (projection of screen corners onto sweep direction).

### Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `N_COLS` | `14` | Grid columns |
| `GAP` | `0.88` | Inter-tile gap (scale factor applied to all geometry) |
| `N_FILLED` | `5` | Permanently filled background tiles |
| `N_ACTIVE_MAX` | `3` | Max tiles simultaneously enlarged in foreground |
| `ACTIVE_LIFE_MIN` | `150` frames | Minimum active lifetime (~2.5 s at 60 fps) |
| `ACTIVE_LIFE_MAX` | `360` frames | Maximum active lifetime (~6 s at 60 fps) |
| `MIN_LIFE` | `150` frames | Minimum remaining life when extended by a beat pulse |
| Active scale target | `4.5 + bass * 4.0` | Up to ~8.5× on strong bass — capped at 12.0 |
| Scale spring stiffness | `0.22` | — |
| Scale spring damping | `0.70` | — |
| Fallback scale spring | stiffness `0.12`, damping `0.78` | Springs back to 1.0 |
| Rotation spring (fallback) | stiffness `0.06`, damping `0.85` | Springs rot → 0° |
| Centroid bounce friction | `0.97` per frame | `cvx`/`cvy` velocity decay |
| Bounce reflection | `abs(v) * 0.8 + 1.5` | Velocity magnitude on edge hit |
| Interior margin | `1.5 × tile_width` from each edge | Only interior tiles activate |
| Filled-set swap | every `70–120` frames | One filled tile replaced randomly |
| Auto-activate | every `180–320` frames | 1–2 interior tiles activate without a beat |
| Sweep 1 velocity | `3.2` px/frame | — |
| Sweep 2 velocity | `4.1` px/frame | Staggered start so one is always on screen |
| Sweep band half-width | `90` px | — |
| Sweep start position | `min_proj(corners) − 90` px | Always enters from real screen edge |
| Sweep brightness at centre | `0.20 + 0.55 = 0.75` | Falloff to 0.20 at edge |
| Vertex coordinate clamp | `±16383` | SDL/pygame safe range |
| Grid bleed | `1 tile` past each edge | No clipped triangles at screen border |

### Activation Trigger
A tile is activated when `beat > 0.2 AND bass > 0.25` (bass-beat detection) and fewer than `N_ACTIVE_MAX` tiles are already active. If all slots are full the existing tiles' remaining life is extended to at least `MIN_LIFE` frames instead.

### Rainbow Edge Hue
Each edge hue is computed from the edge's screen angle: `h = (global_hue * 2 + atan2(dy, dx) / τ + 0.5) % 1.0`, so the wireframe colours shift continuously with the edge direction and global hue drift.

### Audio Reactions
- **Bass** → active tile scale target (pulses up to 8×), spin reinforcement
- **Beat + bass** → new tile activation or life extension
- **Bass level** → background filled-tile brightness

---

## 4. Lissajous

3-D Lissajous parametric curve forming a trefoil knot with 3-fold rotational symmetry. Trail of up to 1400 points rendered with two-pass neon glow. Scale and rotation spring on beats.

### Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `TRAIL` | `1400` | Maximum trail history length |
| `N_SYM` | `3` | Rotational symmetry copies |
| FOV | `min(W, H) * 0.40` | — |
| X frequency | `3.0 + bass * 1.3` | Bass-driven |
| Y frequency | `2.0 + mid * 1.3` | Mid-driven |
| Z frequency | `5.0 + high * 1.3` | High-driven |
| Phase dx per frame | `0.0006 + bass * 0.002` | — |
| Phase dz per frame | `0.0005 + high * 0.0013` | — |
| Time speed | `0.016 + beat * 0.04` per frame | — |
| Scale spring kick | `beat * 0.30` | — |
| Scale restore | `(1.0 – scale) * 0.16` | — |
| Scale damping | `0.72` | — |
| Minimum scale | `0.35` | — |
| 3-D rotation X damping | `0.985` | — |
| 3-D rotation Y damping | `0.985` | — |
| Hue drift on beat | `beat * 0.06` per frame | — |
| Head dot radius | `max(3, int(7 + beat * 22))` px | — |
| Halo render: lw multiplier | `4×` | Neon glow pass |
| Core render: head lightness | `0.90 + beat * 0.08` (max 0.98) | — |

### Audio Reactions
- **Bass** → X-axis frequency, phase speed
- **Mid** → Y-axis frequency
- **High** → Z-axis frequency, phase speed
- **Beat** → scale burst, rotation kick, head dot size, hue shift, extra glow (beat > 0.5)

---

## 5. Tunnel

First-person ride through a sinusoidal curving tube. 30 rings of 20-sided polygons recede into the distance. Beat spawns incoming triangles that rotate as they fly toward the camera. Inner polygons rotate within each ring.

### Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `N_RINGS` | `30` | Depth rings |
| `N_SIDES` | `20` | Polygon segments per ring |
| `TUBE_R` | `2.8` 3-D units | Tube radius |
| `Z_FAR` | `10.0` | Far clipping depth |
| `Z_NEAR` | `0.18` | Near clipping depth |
| FOV | `min(W, H) * 0.75` | — |
| Tube sway X | `sin(t * 0.21) * 0.8` | — |
| Tube sway Y | `cos(t * 0.16) * 0.6` | — |
| Time speed | `0.03 + bass * 0.09 + beat * 0.18` per frame | — |
| Triangle spawn rate | `int(bass * 1.5 + beat * 3.0)` per frame | Beat threshold 0.3 |
| Triangle size | `uniform(0.45, 1.1) * (1.0 + bass * 1.5)` | — |
| Triangle rotation velocity | `±uniform(0.04, 0.12)` rad/frame | Random direction |
| Triangle pool limit | `120` | — |
| Ring brightness | `0.06 + near_t * 0.70 + fft[fi] * 0.20 + beat * near_t * 0.50` | — |
| Ring width | `max(1, int(1 + beat * 3 * near_t))` | — |
| Inner polygon sides | `3 + (ring_index % 4)` | 3–6 sides, alternating |
| Inner polygon rotation | `time * 0.45 * direction` | Alternating per ring |

### Audio Reactions
- **Bass** → time speed, triangle size & spawn rate
- **Beat** → time speed burst, spawn burst, ring brightness & width
- **Per-ring FFT** → individual ring brightness

---

## 6. Corridor

First-person neon rainbow corridor. Concentric rounded-rectangle frames recede into a vanishing point and fly toward the camera. The path curves sinusoidally over time. Beat flares the nearest frames and spawns glowing sparks scattered within the corridor that streak toward the camera. Sparks are composited above frame geometry via an independent persistent surface.

### Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `N_FRAMES` | `28` | Depth frames |
| `WORLD_H` | `2.0` | Half-height in world units |
| `ASPECT` | `1.65` | Width / height ratio |
| `Z_FAR` | `12.0` | Far clipping depth |
| `Z_NEAR` | `0.28` | Near clipping depth |
| `_CORRIDOR_FADE` | `28` | Frame layer fade alpha |
| `_SPARK_FADE` | `10` | Spark layer fade alpha — slower = longer trails |
| FOV | `min(W, H) * 0.72` | — |
| Path sway X | `sin(t * 0.19) * 0.5` | — |
| Path sway Y | `cos(t * 0.14) * 0.35` | — |
| Time speed | `0.028 + bass * 0.08 + beat * 0.16` per frame | — |
| Spark spawn rate | `int(bass * 1.2 + beat * 4.0)` per frame | Beat threshold 0.25 |
| Spark pool limit | `100` | — |
| Frame corner radius | `min(half_w, half_h) // 3` | Rounded rectangle |
| Frame brightness | `0.06 + near_t * 0.70 + fft[fi] * 0.20 + beat * near_t * 0.50` | — |
| Glow halo inflate | `lw * 5 + 4` px | Neon glow pass |
| Hue drift | `0.005` per frame | — |

### Audio Reactions
- **Bass** → time speed, spark spawn rate
- **Beat** → time speed burst, frame brightness, spark spawn burst, frame line width
- **Per-frame FFT** → individual frame brightness

---

## 7. Nova

Waveform kaleidoscope with prime 7-fold mirror symmetry across 4 concentric spinning layers. Each layer is assigned a different frequency band. Beat explodes all layers outward simultaneously.

### Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `N_SYM` | `7` | Symmetry sectors (prime fold) |
| `N_LAYERS` | `4` | Concentric spinning rings |
| `N_WAVE` | `120` | Waveform samples per sector |
| Layer radii fractions | `0.22 + i/(N_LAYERS–1) * 0.72` | Of `max_r` |
| Rotation base velocity | `±(0.005 + i * 0.0022)` rad/frame | Alternating direction |
| Rotation audio modulation | `rvel * (1.0 + energy * 2.8 + bass * 1.2)` | — |
| Spring kick | `0.32 + energy * 0.14` | Energy-dependent |
| Spring restore | `–poff[i] * 0.24` | Per layer |
| Spring damping | `0.63` | — |
| Waveform amplitude | `base_r * (0.14 + energy * 0.20 + beat * 0.10)` | — |
| Line width | `max(1, int(1 + energy * 2.5 + beat * 2))` px | — |

### Layer Band Assignment
| Layer | Band |
|-------|------|
| 0 | Bass (fft[:6]) |
| 1 | Mid (fft[6:30]) |
| 2 | High (fft[30:]) |
| 3 | Average of all three |

### Decorative Triangle Rings
| Ring | Speed | Radius fraction | Hue offset |
|------|-------|-----------------|------------|
| Outer sector ring 1 | `+0.012` | `0.58` | `0.25` |
| Outer sector ring 2 | `–0.008` | `0.82` | `0.55` |
| Central ring 1 | `+0.025` | `0.12` | `0.00` |
| Central ring 2 | `–0.017` | `0.18` | `0.45` |

### Audio Reactions
- **Per-layer band** → waveform amplitude, rotation speed, spring kick
- **Bass** → global rotation speed modulation
- **Beat** → spring kick on all layers, waveform amplitude burst, line width

---

## 8. Spiral

Neon helix vortex. Six spiral arms fly toward the viewer with cross-ring connections between arms. Two-pass neon glow on all points. Beat springs the entire structure outward.

### Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `N_ARMS` | `6` | Spiral arms |
| `N_PTS` | `80` | Points per arm |
| `Z_FAR` | `10.0` | Far clipping depth |
| `Z_NEAR` | `0.12` | Near clipping depth |
| `RADIUS` | `1.0` | Base arm radius (3-D units) |
| `SPIN` | `1.6` | Angular velocity multiplier |
| `N_SYM` | `3` | 3-fold rotational symmetry copies |
| `RING_STEP` | `8` | Cross-ring connection interval (depth points) |
| FOV | `min(W, H) * 0.72` | — |
| Time speed | `0.038 + bass * 0.10 + beat * 0.18` per frame | — |
| Scale spring kick | `beat * 0.48` | — |
| Scale restore | `(1.0 – scale) * 0.25` | — |
| Scale damping | `0.81` | — |
| Minimum scale | `0.4` | — |
| Hue drift | `0.007 + beat * 0.04` per frame | — |
| Radius modulation per point | `fft[band] * 1.5` | Band varies with depth |
| Brightness exponent | `near_t ** 1.15` | Emphasizes closest points |
| Halo radius | `r_dot * 3 + 1` px | Neon glow pass |
| Beat flash threshold | `beat > 0.35 and near_t > 0.80` | Extra ring at near points |

### Audio Reactions
- **Bass** → time speed
- **Per-band FFT** → individual arm point radius
- **Beat** → time burst, scale burst, hue acceleration, near-point flash ring

---

## 9. Bubbles

Translucent rising bubbles with multi-layer glow, neon rim, specular highlight, and complementary-hue filled core. Up to 700 bubbles. Beat swells all bubbles simultaneously.

### Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `MAX` | `700` | Maximum bubble pool size |
| Pre-spawned bubbles | `200` | At startup |
| Radius range | `uniform(8, 45)` px | Base size |
| X velocity | `gauss(0, 0.4)` px/frame | Lateral drift |
| Y velocity | `uniform(–1.0, –3.2)` px/frame | Upward movement |
| Wobble rate | `uniform(0.025, 0.07)` per frame | Horizontal oscillation |
| Spawn rate | `int(2 + beat * 12 + bass * 6)` per frame | — |
| Spawn radius boost | `r *= (1 + bass * 1.2)` | — |
| Spawn velocity boost | `vy *= (1 + beat * 0.8)` | — |
| Global beat spring kick | `beat * 0.75` | All bubbles swell together |
| Global spring restore | `–pulse * 0.35` | — |
| Global spring damping | `0.52` | — |
| Display radius | `max(2, int(r * (1 + pulse * 0.90 + mid * 0.15)))` px | — |
| Hue drift per bubble | `+0.004` per frame | Individual rainbow cycling |
| Alpha (life-based) | `int(life * 160)` | Fades near top of screen |
| Beat flash threshold | `beat > 1.0` | Extra bright ring at `r * 1.4` |

### Glow Layers (outermost → innermost)
| Layer | Size exponent | Lightness | Alpha multiplier |
|-------|--------------|-----------|-----------------|
| Outer halo | `1.55×` | `0.40` | `0.18` |
| Mid halo | `1.28×` | `0.52` | `0.35` |
| Inner halo | `1.10×` | `0.65` | `0.60` |
| Neon rim | `1.00×` | `0.78` | — (solid, width 2) |
| Filled core | `1.00×` | `0.55` | `0.22` (complementary hue) |
| Specular | `r/3` | white | `0.55` (offset –r/3, –r/3) |

### Audio Reactions
- **Bass** → spawn rate, spawned size, spawned velocity
- **Mid** → display radius modulation
- **Beat** → spawn burst, velocity burst, global pulse swell, beat flash ring

---

## 10. Plasma (←/→ only)

Full-screen psychedelic texture from four overlapping sine wave fields. Rendered at ¼ resolution and upscaled for performance. Hue and brightness continuously shift with audio.

### Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `RES_DIV` | `4` | Render resolution divisor (performance) |
| Wave fields | 4 | Perpendicular + diagonal + radial |
| Frequency modulation (`fm`) | `1.0 + mid * 0.7` | Mid-band driven |
| Time speed | `0.018 + bass * 0.09 + beat * 0.14` per frame | — |
| Brightness base | `0.28` | — |
| Brightness wave contribution | `wave * 0.22` | — |
| Beat brightness flash | `beat * 0.22` | — |
| High-freq brightness boost | `high * 0.08` | — |
| Brightness range | `[0.0, 0.95]` | Clipped |
| Hue modulation | `wave * 0.55 + 0.5 + hue_base + bass * 0.35` | — |
| Hue drift | `0.005` per frame | — |

### Wave Fields
1. `sin(X * fm + t)`
2. `sin(Y * fm * 0.8 + t * 1.4)`
3. `sin((X * 0.6 + Y * 0.8) * fm + t * 0.9)`
4. `sin(R * fm * 0.5 – t * 1.2)` (radial)

### Audio Reactions
- **Bass** → time speed, hue shift
- **Mid** → wave frequency density
- **High** → brightness boost
- **Beat** → time speed burst, brightness flash

---

## 11. Branches (←/→ only)

Recursive fractal lightning tree. Nine neon arms radiate from screen centre, each splitting recursively (with an extra central fork at trunk and first-split levels) down to depth 7, yielding dense electric tips per arm. The trunk stub is very short (3% of arm length) so branches burst outward almost immediately from the centre. The whole tree rotates slowly. Mid-band jitter makes every branch angle ripple in real-time. Beat fires additional arms and a brightness burst. Two-pass neon glow (wide dim halo + bright core) on every segment.

### Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `MAX_DEPTH` | `7` | Recursion depth |
| `BASE_ARMS` | `9` | Resting arm count |
| Extra arms on beat | `int(min(beat, 2.5) * 2.2)` | Up to +5 arms |
| Trunk draw length | `length * 0.03` | Very short stub; children get full length |
| Trunk size | `min(sc * 0.22 * (1 + bass*0.70 + beat*0.45), sc * 0.27)` | Capped to keep branches on screen |
| Branch ratio | `0.62 + high * 0.10` | Child / parent length |
| Spread angle | `π/2.6 + mid * 0.55` rad | Split half-angle |
| Angle jitter | `sin(t*2.3 + …) * mid * 0.80` | Mid-driven per-branch jitter (3 overlapping sines) |
| Triple-fork depth | `>= MAX_DEPTH - 1` | Extra centre child at trunk + first split |
| Rotation speed | `time * 0.06` rad | Whole-tree slow rotation |
| `beat_flash` | decay `* 0.72 + beat * 0.28` | Brightness burst on beat |

### Audio Reactions
- **Bass** → trunk length, animation speed
- **Mid** → branch angle jitter (organic branching motion)
- **High** → branch brightness, child/parent length ratio
- **Beat** → extra arms, brightness burst, speed kick

---

## 12. Spectrum (←/→ only)

Classic frequency spectrum bars with peak markers and scrolling waveform overlay. Log-spaced frequency bins give uniform visual weight to all decades.

### Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| Bin spacing | Logarithmic (`geomspace`) | ~40–60 bars depending on FFT |
| FFT coverage | `2 – 85%` of Nyquist | Upper range trimmed to reduce noise |
| Bar width | `WIDTH // n_bars` px | — |
| Bar height smoothing | Lerp speed `0.25 + min(beat, 1.0) * 0.75` | Fast at beats, smooth at quiet |
| Peak decay | `peaks * 0.97` per frame | Slow fall |
| Peak marker height | `3` px | Thin white line |
| Bar lightness | `0.38 + height * 0.42` | Brighter at higher energy |
| Waveform amplitude | `sample * 120` px | Centered at screen middle |
| Waveform line width | `2` px | — |
| Waveform lightness | `0.75` | — |
| Hue drift | `0.003` per frame | — |

### Audio Reactions
- **Beat** → lerp speed spike (bars snap faster to new heights)
- **Per-bin FFT** → individual bar heights
- **Waveform** → overlay line shape

---

## 13. Waterfall (←/→ only)

Scrolling spectrogram. Each frame a new frequency row is added at the top; old rows scroll down. Hue encodes frequency position; brightness encodes energy. Newest rows receive strongest beat flash.

### Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `ROWS` | `100` | Frames of history displayed |
| `COLS` | `80` | Frequency bins (log-spaced) |
| FFT coverage | `2 – 85%` of Nyquist | — |
| Tile width | `max(1, WIDTH // cols)` px | — |
| Tile height | `max(4, HEIGHT // ROWS)` px | — |
| Hue (frequency) | `(base_hue + col / cols * 0.75) % 1.0` | Low → high = hue sweep |
| Lightness base | `0.2 + energy * 0.8` | Energy-driven |
| Age decay | `1 – age * 0.7` | Older rows dimmer |
| Beat flash (newest rows) | `beat * 0.35` | Decays 6× faster with age |
| Minimum lightness | `0.10` | Always-visible floor |
| Hue drift | `0.003 + beat * 0.015` per frame | — |

### Audio Reactions
- **Per-bin FFT** → tile brightness per column
- **Beat** → brightness flash on newest rows, hue acceleration
- **Time** → rows scroll downward, history fades

---

## Navigation

| Key | Action |
|-----|--------|
| `1` – `9` | Switch to effect 1–9 |
| `←` / `→` | Previous / next effect (cycles all 13 modes) |
| `↑` / `↓` | Increase / decrease effect intensity (gain 0.0–2.0) |
| `D` | Open audio device picker |
| `F` | Toggle fullscreen |
| `H` | Toggle HUD / legend |
| `Q` / `Esc` | Quit |
