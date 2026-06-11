# Bug Report

> Round 1: Analysis across ETH codebot models (`mistral-small:24b-instruct-2501-q8_0`, `qwen3.6:35b-a3b-q8_0`, `llama3.3:70b`).
> Round 2: Manual review of all 33 source files + targeted queries to `mistral-small:24b-instruct-2501-q8_0` and `qwen3.6:27b`.
> Round 3: Manual review of remaining files (vortex.py) + targeted queries to `mistral-small:24b-instruct-2501-q8_0`.
> Round 4: Runtime analysis (benchmark run + edge-case search + targeted queries to `mistral-small:24b-instruct-2501-q8_0`).
> Round 5: Architecture-level review (crossfade, settings I/O, audio callback safety, GL blend modes, benchmarks) + targeted queries to `mistral-small:24b-instruct-2501-q8_0`.

---

## CRITICAL

### BUG-001: `psysualizer.py:334,522` — `list(self.presets.values())` crashes on list

`load_presets()` (`settings.py:42`) returns a `list`, but the preset cycling code treats it as a `dict`:

```python
# settings.py:42-49
def load_presets() -> list:
    ...
    return data if isinstance(data, list) else []

# psysualizer.py:116
self.presets = sett.load_presets()     # ← gets a list
```

```python
# psysualizer.py:334 — Shift+P preset cycle
p = list(self.presets.values())[self.active_preset]   # ← AttributeError: 'list' has no 'values'

# psysualizer.py:522 — HUD preset name display
pname = list(self.presets.keys())[self.active_preset]  # ← AttributeError: 'list' has no 'keys'
```

**Root cause:** `load_presets()` was refactored from dict to list (to match `save_preset` which uses `list.append`), but the consumer code was not updated.

**Impact:** Pressing Shift+P to cycle presets, or having a preset loaded when HUD level > 1, crashes the application.

**Fix:** Either wrap the list in a dict lookup, or change the cycling code to use list indexing:

```python
# Option A: Convert to dict keyed by name
# psysualizer.py:116
self.presets = {p["name"]: p for p in sett.load_presets()}
# psysualizer.py:351
self.presets = {p["name"]: p for p in sett.load_presets()}

# Option B: Use list indexing (smaller diff)
# psysualizer.py:334
p = self.presets[self.active_preset]
# psysualizer.py:522
pname = self.presets[self.active_preset]["name"]
```

---

## HIGH

### BUG-002: `psysualizer.py:434-437` — Span child death shuts down main application

```python
if self.span_mode:
    for child in self.display.span_children.values():
        if child.poll() is not None:
            self._save_settings()
            self._quit()
```

If any span child process exits (crashes, OOM-killed, or user closes it), the main application immediately saves settings and terminates. A single child failure should not bring down the entire multi-monitor setup.

**Fix:** Respawn the dead child or just log the failure and continue:

```python
for child_idx, child in list(self.display.span_children.items()):
    if child.poll() is not None:
        print(f"  ⚠️ Span child {child_idx} died, respawning...")
        self.display.spawn_span_children(self.span_vis2_idx, os.path.abspath(__file__))
```

---

### BUG-003: `effects/lattice.py:26-31` — `RES_DIV` instance override shadows class attribute with inconsistent semantics

```python
class Lattice(Effect):
    RES_DIV = 3  # class default

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if config.WIDTH >= 2560:
            self.RES_DIV = 1
        elif config.WIDTH >= 1600:
            self.RES_DIV = 2
        else:
            self.RES_DIV = 3
```

The dynamic `RES_DIV` assignment happens only once in `__init__`. If the display resolution changes at runtime (fullscreen toggle → `_rebuild_effects()`), a new `Lattice` instance IS created (since `_rebuild_effects` creates `self.vis = self.VisCls(...)`), so `__init__` runs again with updated `config.WIDTH`. This works **for the main effect**, but the **background effect** (`bg_vis`) — which could be Lattice — is only recreated in `_rebuild_effects()` (called on fullscreen toggle), NOT in `_switch_mode()`.

If resolution changes while Lattice is the background effect, the bg instance keeps the stale `RES_DIV` until the next fullscreen toggle or explicit rebuild.

**Severity:** Low at runtime (resolution changes are rare), but architecturally fragile.

---

## MEDIUM

### BUG-004: `effects/flowfield.py:107-109` — Surface lock not exception-safe

```python
pixels = surfarray.pixels2d(self._trail)
pixels[ix, iy] = colors
del pixels
```

`surfarray.pixels2d()` locks the surface for pixel access. The `del pixels` call releases the lock. If any exception occurs between the lock and the `del`, the surface remains locked (`pygame.error: Surfaces must not be locked during blit`).

**Fix:** Use a try/finally block:

```python
pixels = surfarray.pixels2d(self._trail)
try:
    pixels[ix, iy] = colors
finally:
    del pixels
```

Or use a context manager (pygame-ce):

```python
with surfarray.pixels2d(self._trail) as pixels:
    pixels[ix, iy] = colors
```

---

### BUG-005: `beat_tracking.py:112,134` — Dead return values in `_analyze_blocks`

```python
# Line 112 (inside _analyze_blocks, called from a daemon thread)
if onset_env.size < 8:
    return self._bpm or fallback_bpm

# Line 134
from _analyze_blocks:
    bpm = _scalar(tempo)
    if bpm:
        bpm = max(60.0, min(200.0, bpm))
```

`_analyze_blocks()` is called by `_run_analysis()` which discards the return value:

```python
def _run_analysis(self, blocks, block_end_time, fallback_bpm):
    try:
        self._analyze_blocks(blocks, block_end_time, fallback_bpm)  # return ignored
    finally:
        with self._lock:
            self._analysis_running = False
```

Values are stored to instance attributes under lock at the end of `_analyze_blocks` (line 162-172), so the early returns are harmless dead code. However, this is misleading and the early returns bypass the locking at line 162, meaning the `self._bpm` and `self._beat_interval` state may not be updated after an early return, which could leave stale state.

---

### BUG-006: `gl_renderer.py:145-153` — `release()` iterates cache while releasing programs

```python
def release(self):
    if self._blit_tex:
        self._blit_tex.release()
    self._vbo.release()
    for prog, vao in self._program_cache.values():
        prog.release()
        vao.release()
```

If a program in `_program_cache` shares resources with another cached program (e.g., compiled from the same vertex/fragment source), releasing the first program may invalidate the second before it is released. ModernGL can raise `moderngl.Error` on double-free. This is unlikely in the current usage (separate vert/frag pairs), but is a latent use-after-free pattern.

**Fix:** Collect programs first, then release:

```python
for prog, vao in list(self._program_cache.values()):
    vao.release()
    prog.release()
```

---

### BUG-007: `core/audio_engine.py:68-77` — `detect_genre()` resets accumulator (verified race-free)

```python
def detect_genre(self) -> str | None:
    with self._lock:
        if self._detect_frames < self._DETECT_MIN:
            return None
        avg = self._detect_accum / self._detect_frames
        self._detect_accum[:] = 0
        self._detect_frames = 0          # reset under lock — OK
    # ... genre classification ...
```

The reset of `_detect_frames` is under the lock, so the callback (`_audio_cb`) won't race on it. However, after releasing the lock, the classification uses `avg` which was computed from a snapshot. This is correct.

No actual race — correct behavior, but worth documenting that the lock scope is correct.

---

### BUG-009: `settings.py:47` — Silent preset data loss on upgrade from dict format

```python
return data if isinstance(data, list) else []
```

If `presets.json` was saved by an older version (which used a dict keyed by name), `isinstance(data, list)` returns `False` and all presets are silently discarded. The user's saved data is replaced with an empty list on the next `save_preset()` call.

**Root cause:** No migration path. The format changed from `dict` to `list` without version detection.

**Fix:** Support both formats on load:

```python
def load_presets() -> list:
    try:
        with open(_PRESETS_FILE) as f:
            data = json.load(f)
        if isinstance(data, dict):  # old format — migrate
            return [{"name": k, **v} for k, v in data.items()]
        return data if isinstance(data, list) else []
```

---

## LOW

### BUG-008: `effects/corridor.py:54-55` — Internal surfaces created without `SRCALPHA`

```python
self.corridor_surf = pygame.Surface((W, H))
self.spark_surf    = pygame.Surface((W, H))
```

These surfaces are blitted to the main target with `BLEND_ADD` (spark_surf) or directly (corridor_surf). Since they lack `SRCALPHA`, pygame uses the per-surface alpha via `set_alpha()` on the fade surfaces (`_cfade`, `_sfade`). The `spark_surf` is blitted with `BLEND_ADD` at line 143:

```python
surf.blit(self.spark_surf, (0, 0), special_flags=pygame.BLEND_ADD)
```

On an `SRCALPHA` target, `BLEND_ADD` with a non-alpha source performs additive blending on RGB channels with no alpha contribution — the source alpha is treated as 0 for blending purposes. This means the spark additive glow may not composite correctly over alpha content (e.g. in GL mode where the target might have transparency). The visual effect may differ between CPU and GL paths.

---

<!-- BUG-009 was a false positive — butterflies trail decay is mathematically correct -->

### BUG-010: `effects/vortex.py:104-107` — Feedback rotozoom at `RES_DIV=3` creates visual artifacts

```python
rotated = pygame.transform.rotozoom(self._trail, rot_deg, zoom)
```

At `RES_DIV = 3`, the internal surface is 1/3 resolution. `rotozoom` with a fractional zoom factor on low-resolution input interpolates pixels, creating visible blocky artifacts in the feedback tunnel. This is a known design tradeoff for performance, but at higher zoom levels the pixel grid becomes noticeable.

---

### BUG-011: `effects/triflux.py:229` — Off-screen tile check may skip tiles that are partially on-screen

```python
pts = self._screen_verts(tile)
if all(p[0] < 0 or p[0] >= W or p[1] < 0 or p[1] >= H for p in pts):
    continue
```

This only skips tiles where ALL vertices are off-screen. A tile with most vertices off-screen but one just on the edge will be drawn. This is correct culling behavior for the mosaic wall effect. However, it also means the sweep glow (drawn at line 242) is applied even for off-screen tiles, wasting fill rate. The check should only skip the edge+fill drawing, not the sweep.

---

## HIGH

### BUG-012: `core/display_manager.py:109-111` — `SDL_VIDEO_WINDOW_POS` env var leaked on `set_mode` exception

```python
os.environ["SDL_VIDEO_WINDOW_POS"] = f"{mx},{my}"
self.screen = pygame.display.set_mode((mw, mh), flags | pygame.NOFRAME)
os.environ.pop("SDL_VIDEO_WINDOW_POS", None)
```

If `pygame.display.set_mode()` raises an exception (e.g. invalid geometry, GL initialization failure), the env var `SDL_VIDEO_WINDOW_POS` is never popped from `os.environ`. This poisons all subsequent `set_mode()` calls in the same process — any window opened later will be positioned at the stale monitor coordinates.

**Fix:** Wrap `set_mode` in a `try/finally` to guarantee cleanup:

```python
os.environ["SDL_VIDEO_WINDOW_POS"] = f"{mx},{my}"
try:
    self.screen = pygame.display.set_mode((mw, mh), flags | pygame.NOFRAME)
finally:
    os.environ.pop("SDL_VIDEO_WINDOW_POS", None)
```

---

## MEDIUM

### BUG-013: `core/display_manager.py:157-176` + `psysualizer.py:433-437` — Span child respawn kills all healthy children

The BUG-002 fix originally called `self.display.spawn_span_children(...)` when a single child died:

```python
for child_idx, child in list(self.display.span_children.items()):
    if child.poll() is not None:
        print(f"  Span child {child_idx} died, respawning...")
        self.display.spawn_span_children(self.span_vis2_idx, os.path.abspath(__file__))
```

But `spawn_span_children()` calls `kill_children()` first, which sends SIGTERM to every running child. A single child crash would terminate all healthy siblings.

**Fix:** Spawn only the dead child directly via `_spawn_child()` rather than the full reset:

```python
for child_idx, child in list(self.display.span_children.items()):
    if child.poll() is not None:
        print(f"  Span child {child_idx} died, respawning...")
        self.display._spawn_child(child_idx, self.span_vis2_idx, os.path.abspath(__file__))
```

---

## LOW

### BUG-014: `effects/butterflies.py:294` — One-way wing sync applies delta asymmetrically

```python
diff = self.love.wing_phase - self.solo.wing_phase
self.love.wing_phase -= diff * sync * 0.12
```

When butterflies are close, their wing phases sync. But only `love.wing_phase` is pulled toward `solo.wing_phase` — the solo's phase is never adjusted. If both phases are equally valid (neither is the "reference"), the correction should be symmetric.

**Fix:** Apply half the diff to each:

```python
self.love.wing_phase -= diff * sync * 0.12
self.solo.wing_phase += diff * sync * 0.12
```

---

### BUG-022: `benchmarks.py:18,53,71` — Tick counter shared across all CPU/GL tests

```python
tick = 0  # initialized once at module level

for name, VisCls in MODES:
    # CPU test: tick increments by ~2800 for fast effects
    while time.perf_counter() < end_time:
        vis_cpu.draw(cpu_surf, waveform, fft, beat, tick)
        tick += 1
    # GL test: continues from CPU's final tick
    vis_gl = VisCls(renderer=renderer)
    while time.perf_counter() < end_time:
        vis_gl.draw(gl_target, waveform, fft, beat, tick)
        tick += 1
```

`tick` is never reset between effects or between CPU/GL test pairs. Effects using `tick % N` (e.g., `vortex.py:120`) appear at completely different animation phases between CPU and GL runs. This introduces non-deterministic measurement noise for tick-dependent effects.

**Fix:** Reset `tick = 0` at the start of each CPU test and each GL test.

---

### BUG-021: `effects/vortex.py:155`, `flowfield.py:114`, `lattice.py:220`, `butterflies.py:380`, `cube.py:147` — `BLEND_RGBA_MAX` corrupts alpha on SRCALPHA targets (GL path)

```python
surf.blit(self._trail, (0, 0), special_flags=pygame.BLEND_RGBA_MAX)
```

All five effects that use trail fading create 24-bit (no alpha) surfaces. When blitted with `BLEND_RGBA_MAX`, pygame treats the missing alpha as 255, so `max(255, dst_alpha) = 255`. On SRCALPHA targets (used in GL mode at `psysualizer.py:181`), this unconditionally raises destination alpha to 255 wherever the trail has content, destroying any semi-transparency for composited elements.

This also affects `Aurora` using `BLEND_ADD` on SRCALPHA (`aurora.py:131`), which adds alpha channels and clamps at 255.

**Fix:** Replace `BLEND_RGBA_MAX` with `BLEND_RGB_MAX` (which only blends R/G/B channels) on all trail compositing operations. For Aurora, use `BLEND_RGB_ADD` instead of `BLEND_ADD`.

---

### BUG-020: `core/audio_engine.py:79-147` — Audio callback unhandled exceptions silently kill the stream

```python
def _audio_cb(self, indata, frames, time_info, status) -> None:
    mono = np.asarray(indata[:, 0], dtype=np.float32)
    self.beat_tracker.push_audio(mono, time_info.currentTime)
    windowed = mono * self._blackman_window
    spectrum = np.abs(np.fft.rfft(windowed))
    ...  # no try/except around any of this
    with self._lock:
        self._waveform = mono.copy()
        ...
```

If any line in the callback raises (e.g., `np.fft.rfft` on corrupted data, shape mismatch), sounddevice catches the exception, logs it, and **stops the audio stream** without notifying the main thread. The visualizer continues running with stale/frozen audio data, and the user sees the visuals stop reacting to music.

If the exception occurs inside `with self._lock:`, Python's context manager guarantees lock release (no deadlock), but shared state may be partially updated — `get_audio()` on the main thread reads a mix of old and new values.

**Fix:** Wrap the entire callback body in `try/except` that logs the error and signals the main thread to restart the stream. At minimum, catch and re-raise after cleanup.

---

### BUG-019: `settings.py:34-37` — Non-atomic writes silently wipe settings on crash

```python
def save(d):
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    with open(_SETTINGS_FILE, "w") as f:
        json.dump(d, f, indent=2)
```

Same for `save_preset()` (line 65) and `delete_preset()` (line 73). If the process crashes or is killed mid-write, the JSON file is truncated or contains partial data. On next load, `json.JSONDecodeError` is caught and defaults silently replace the user's configuration:

```python
def load():
    try:
        with open(_SETTINGS_FILE) as f:
            data = json.load(f)
        return {**_DEFAULTS, **data}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_DEFAULTS)  # ← user's settings silently lost
```

**Fix:** Use write-to-temp + `os.replace()` (atomic rename on POSIX):

```python
tmp = _SETTINGS_FILE + ".tmp"
with open(tmp, "w") as f:
    json.dump(d, f, indent=2)
os.replace(tmp, _SETTINGS_FILE)
```

---

### BUG-018: `psysualizer.py:463-468` — Crossfade off-by-one prevents full transparency

```python
frames = max(1, int(self.cf_frames))   # default: 45
t = self.crossfade_frame / frames       # 0/45, 1/45, ..., 44/45
ease = t * t * (3.0 - 2.0 * t)         # smoothstep
scaled_prev.set_alpha(int(255 * (1.0 - ease)))
self.crossfade_frame += 1
if self.crossfade_frame >= frames:      # stops at 45
    self.prev_surf = None
```

`crossfade_frame` iterates 0..44 (45 steps), so the last `t = 44/45 ≈ 0.978`. Smoothstep(0.978) ≈ 0.998, giving `alpha = 255 × (1 − 0.998) ≈ 0.5`. The previous frame is cleared while still at alpha ≈ 0.5 — it never reaches full transparency.

- **At default `cf_frames=45`:** α ≈ 0.5 / 255 — imperceptible.
- **At `cf_frames=2`:** α ≈ 127 / 255 — **50% remnant visible**. The pane slider allows values as low as 0 (`psysualizer.py:385`), so users can easily configure this.

**Fix:** Change the condition so `t` reaches 1.0 on the last frame, e.g.:

```python
if self.crossfade_frame >= frames:
    scaled_prev.set_alpha(0)
    self.prev_surf = None
...
```

Or add one extra animation step to let smoothstep reach 1.0.

---

### BUG-017: `psysualizer.py:421-424` — Auto-gain spikes to max on silence before audio arrives

```python
self.rms_buf.append(float(np.sqrt(np.mean(self.waveform ** 2))))
if self.auto_gain and self.rms_buf:
    cur_rms = float(np.mean(self.rms_buf)) + 1e-9
    auto_scale = max(0.5, min(self.target_rms / cur_rms, 2.0))
```

Before the first audio callback fires, `self.waveform` (from `AudioEngine._waveform`) is still the initial `np.zeros(config.BLOCK_SIZE, dtype=np.float32)`. This means:
1. RMS of zeros = 0.0
2. `cur_rms = 0.0 + 1e-9 = 1e-9`
3. `auto_scale = min(2.0, 0.05 / 1e-9) = 2.0`

The auto-gain stays at 2.0× until enough real audio RMS values (from `rms_buf`, maxlen=30) raise the average — about 0.5s at 60fps.

**Fix:** Initialize `rms_buf` with a small non-zero value, or check `audio.is_active()` before enabling auto-gain.

---

### BUG-016: `effects/vortex.py:139-148` — Ember life decrement after boundary check causes off-by-one

```python
em[0], em[1], em[2], em[3], em[6] = x, y, vx, vy, life - 1
if life > 0 and ... :
    brightness = 0.4 + (life / max_life) * 0.5 + high * 0.15
```

The local variable `life` is decremented in the list assignment (`em[6] = life - 1`), but the condition on the next line reads the **old** `life` value from the local scope, which hasn't been updated. This means:
1. Embers live one frame longer than `max_life`
2. The brightness calculation on the last visual frame uses the wrong `life` ratio

**Fix:** Decrement the local variable before the check:

```python
life -= 1
em[0], em[1], em[2], em[3], em[6] = x, y, vx, vy, life
if life > 0 and ... :
```

---

### BUG-015: `effects/waterfall.py:47` — `import random` inside `draw()` called every frame

```python
# waterfall.py:47, inside draw() — called 60×/second
import random
```

Python caches imports after the first load, so this doesn't cause a crash or meaningful performance cost, but it's a style violation and makes the import-order logic harder to follow. The import should be at the module level.

**Fix:** Move `import random` to the top of the file.

---

## Summary

| ID | File | Line | Severity | Description |
|----|------|------|----------|-------------|
| BUG-001 | `psysualizer.py` | 334, 522 | **CRITICAL** | `self.presets.values()` crashes — presets is a `list`, not `dict` |
| BUG-002 | `psysualizer.py` | 434-437 | **HIGH** | Span child death terminates main app |
| BUG-003 | `effects/lattice.py` | 26-31 | **HIGH** | Dynamic RES_DIV not refreshed on resolution change for bg effect |
| BUG-004 | `effects/flowfield.py` | 107-109 | **MEDIUM** | Surface lock not exception-safe |
| BUG-005 | `beat_tracking.py` | 112, 134 | **MEDIUM** | Dead return values + skipped state update on early return |
| BUG-006 | `gl_renderer.py` | 145-153 | **MEDIUM** | Potential use-after-free during cache release |
| BUG-007 | `core/audio_engine.py` | 68-77 | **LOW** | Correct under review (no actual race, documented for completeness) |
| BUG-008 | `effects/corridor.py` | 54-55 | **LOW** | Non-alpha spark surface composited with BLEND_ADD |
| BUG-009 | `settings.py` | 47 | **LOW** | Silent preset data loss on upgrade from legacy dict format |
| BUG-010 | `effects/vortex.py` | 104-107 | **LOW** | Low-res rotozoom feedback artifacts |
| BUG-011 | `effects/triflux.py` | 229 | **LOW** | Sweep glow drawn even for off-screen tiles |
| BUG-012 | `core/display_manager.py` | 109-111 | **HIGH** | `SDL_VIDEO_WINDOW_POS` leaked on `set_mode` exception |
| BUG-013 | `core/display_manager.py` + `psysualizer.py` | 433-437 | **MEDIUM** | Span child respawn kills all healthy children |
| BUG-014 | `effects/butterflies.py` | 294 | **LOW** | One-way wing sync applies delta asymmetrically |
| BUG-015 | `effects/waterfall.py` | 47 | **LOW** | `import random` inside `draw()` called every frame |
| BUG-016 | `effects/vortex.py` | 139-148 | **LOW** | Ember life decrement after boundary check — off-by-one |
| BUG-017 | `psysualizer.py` | 421-424 | **LOW** | Auto-gain spikes to 2.0× on silence before audio data arrives |
| BUG-018 | `psysualizer.py` | 463-468 | **LOW** | Crossfade off-by-one — never reaches full transparency |
| BUG-019 | `settings.py` | 34-37, 65, 73 | **MEDIUM** | Non-atomic writes silently wipe settings on crash |
| BUG-020 | `core/audio_engine.py` | 79-147 | **MEDIUM** | Unhandled callback exceptions silently kill audio stream |
| BUG-021 | `vortex/flowfield/lattice/butterflies/cube/aurora` | trail blits | **MEDIUM** | `BLEND_RGBA_MAX`/`BLEND_ADD` corrupts alpha on SRCALPHA (GL path) |
| BUG-022 | `benchmarks.py` | 18, 53, 71 | **LOW** | Tick counter shared across CPU/GL tests introduces phase noise |
