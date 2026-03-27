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
| 3 | `3` | Plasma | Full-screen sine-interference psychedelic texture |
| 4 | `4` | Tunnel | First-person ride through a curving tube |
| 5 | `5` | Lissajous | 3-D Lissajous knot with 3-fold symmetry |
| 6 | `6` | Nova | Waveform kaleidoscope with 7-fold mirror symmetry |
| 7 | `7` | Spiral | Neon helix vortex with 6 arms flying toward viewer |
| 8 | `8` | Bubbles | Translucent rising bubbles, size driven by bass |
| 9 | `9` | Spectrum | Classic spectrum bars with peak markers and waveform overlay |
| 10 | `0` | Waterfall | Scrolling spectrogram (time-frequency display) |

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

Dual rotating wireframe cubes (main + inner at 45% scale) with orbiting satellite cubes. Satellite count scales with beat intensity (2–6 cubes). Two-pass neon glow on edges.

### Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `TRAIL_ALPHA` | `18` | Fade speed; lower = longer trails |
| Satellite count | `2 + int(min(beat, 2.0) * 2)` | Range 2–6 |
| Orbital radius | `2.6` 3-D units | — |
| Satellite scale | `main_scale * 0.28` | — |
| Inner cube scale | `main_scale * 0.45` | — |
| FOV | `680` units | — |
| Rotation damping | `0.94` | Per axis |
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
- **Beat** → all axes, satellite count, scale burst

---

## 3. Plasma

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

## 4. Tunnel

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
| Inner polygon sides | `3 + (ring_index % 4)` | 3–6 sides, alternating |
| Inner polygon rotation | `time * 0.45 * direction` | Alternating per ring |

### Audio Reactions
- **Bass** → time speed, triangle size, spawn rate
- **Beat** → time speed burst, spawn burst, ring brightness
- **Per-ring FFT** → individual ring brightness

---

## 5. Lissajous

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

## 6. Nova

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

## 7. Spiral

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

## 8. Bubbles

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

## 9. Spectrum

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

## 10. Waterfall

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
| `1` – `0` | Switch effect |
| `←` / `→` | Previous / next effect |
| `↑` / `↓` | Increase / decrease effect intensity (gain 0.0–2.0) |
| `Q` / `Esc` | Quit |
