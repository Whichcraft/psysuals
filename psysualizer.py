#!/usr/bin/env python3
"""
Music Visualizer — Real-time audio → visuals.

Controls:
  SPACE / click   Switch to next mode
  1-9             Jump to modes 1-9
  ←/→             Cycle modes  (or adjust pane slider when pane open)
  ↑/↓             Intensity    (or navigate pane sliders when pane open)
  Tab             Toggle settings pane
  P               Save preset  |  Shift+P: cycle presets
  F               Toggle fullscreen
  H               Toggle HUD   |  Shift+H: cycle full/minimal/off
  M               Tap tempo    |  Shift+M: toggle span mode (all monitors)
  Q / ESC         Quit
"""

__version__ = "2.11.0"

import argparse
import os
import subprocess
import sys
import threading
import time as _time
from collections import deque

import numpy as np
import pygame
import sounddevice as sd

import config
import settings as sett
from effects import MODES
from effects.palette import palette
from effects.utils import hsl

# ── Audio ────────────────────────────────────────────────────────────────────
_lock            = threading.Lock()
_waveform        = np.zeros(config.BLOCK_SIZE)
_smooth_fft      = np.zeros(config.BLOCK_SIZE // 2)
_beat_energy     = 0.0
_mid_energy      = 0.0
_treble_energy   = 0.0
_blackman_window = np.blackman(config.BLOCK_SIZE)

# Spectral flux beat detection
_prev_spectrum    = np.zeros(config.BLOCK_SIZE // 2)
_flux_avg         = 1e-6
_mid_avg          = 1e-6
_treble_avg       = 1e-6
_prev_beat_energy = 0.0

# BPM detection
_beat_times      = deque(maxlen=8)   # recent onset timestamps (seconds)
_last_onset_time = 0.0               # for debounce
_bpm             = 0.0

# Genre detection — accumulate raw spectrum for ~300 frames then classify
_genre_weights  = np.ones(20)          # applied to bass bins for beat energy
_detect_accum   = np.zeros(config.BLOCK_SIZE // 2)
_detect_frames  = 0
_DETECT_MIN     = 300                  # frames before first detection (~5 s at 60 fps)


def _apply_genre_weights(genre):
    w = np.ones(20)
    if genre == "electronic":
        w[:5]  = 1.5;  w[10:] = 0.7
    elif genre == "rock":
        w[2:9] = 1.3
    elif genre == "classical":
        w[:10] = 0.6;  w[10:] = 1.4
    with _lock:
        _genre_weights[:] = w


def detect_genre():
    """Return detected genre string once enough frames are collected, else None."""
    global _detect_frames
    with _lock:
        if _detect_frames < _DETECT_MIN:
            return None
        avg = _detect_accum / _detect_frames
        _detect_accum[:] = 0
        _detect_frames = 0
    sub_bass   = float(avg[:5].mean())
    bass       = float(avg[:15].mean())
    mids       = float(avg[15:100].mean())
    sub_ratio  = sub_bass / (bass + 1e-6)
    bass_ratio = bass / (bass + mids + 1e-6)
    if sub_ratio > 0.55 and bass_ratio > 0.50:
        return "electronic"
    if bass_ratio > 0.50 and sub_ratio < 0.45:
        return "rock"
    if bass_ratio < 0.35:
        return "classical"
    return "any"


def _audio_cb(indata, frames, time, status):
    global _waveform, _smooth_fft, _beat_energy, _mid_energy, _treble_energy
    global _detect_frames, _detect_accum, _prev_spectrum, _flux_avg, _mid_avg, _treble_avg
    global _prev_beat_energy, _beat_times, _last_onset_time, _bpm
    mono     = indata[:, 0]
    spectrum = np.abs(np.fft.rfft(mono * _blackman_window))[: config.BLOCK_SIZE // 2]
    np.log1p(spectrum, out=spectrum)
    spectrum /= 10.0
    with _lock:
        _waveform      = mono.copy()
        _smooth_fft   *= 0.50
        _smooth_fft   += spectrum * 0.50
        _detect_accum += spectrum
        _detect_frames += 1

        # Spectral flux beat detection (bass bins 0-20)
        flux      = float(np.mean(np.maximum(0.0, spectrum[:20] - _prev_spectrum[:20])))
        _flux_avg = _flux_avg * 0.95 + flux * 0.05
        _beat_energy = flux / (_flux_avg + 1e-6)

        # BPM: detect onset on rising edge above threshold, debounced 300 ms
        t_now = time.currentTime
        if (_beat_energy > 2.0 and _prev_beat_energy <= 2.0
                and t_now - _last_onset_time > 0.30):
            _beat_times.append(t_now)
            _last_onset_time = t_now
            if len(_beat_times) >= 2:
                intervals = np.diff(list(_beat_times))
                med = float(np.median(intervals))
                if med > 0:
                    _bpm = max(60.0, min(200.0, 60.0 / med))
        _prev_beat_energy = _beat_energy

        # Mid band (bins 20-100, ~860 Hz – 4.3 kHz)
        mid       = float(_smooth_fft[20:100].mean())
        _mid_avg  = _mid_avg * 0.95 + mid * 0.05
        _mid_energy = mid / (_mid_avg + 1e-6)

        # Treble band (bins 100-256, ~4.3 kHz – 11 kHz)
        treble        = float(_smooth_fft[100:256].mean())
        _treble_avg   = _treble_avg * 0.95 + treble * 0.05
        _treble_energy = treble / (_treble_avg + 1e-6)

        _prev_spectrum[:] = spectrum


def get_audio():
    with _lock:
        return (_waveform.copy(), _smooth_fft.copy(),
                _beat_energy, _mid_energy, _treble_energy, _bpm)



# ── Device picker ─────────────────────────────────────────────────────────────

def _input_devices():
    """Return list of (index, name) for all input-capable devices."""
    devs = []
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            devs.append((i, d["name"]))
    return devs


def _draw_device_picker(screen, font, devices, selected, active_idx):
    """Render the device-picker overlay."""
    overlay = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 210))
    screen.blit(overlay, (0, 0))

    title = font.render("SELECT INPUT DEVICE   ↑↓ navigate   Enter confirm   Esc cancel",
                         True, (200, 200, 200))
    screen.blit(title, (40, 30))

    row_h  = 28
    y0     = 80
    visn   = min(len(devices), (config.HEIGHT - y0 - 20) // row_h)
    start  = max(0, min(selected - visn // 2, len(devices) - visn))

    for i, (dev_idx, name) in enumerate(devices[start:start + visn]):
        row   = start + i
        y     = y0 + i * row_h
        is_sel   = row == selected
        is_live  = dev_idx == active_idx
        bg_col   = (40, 80, 140) if is_sel else (0, 0, 0, 0)
        if is_sel:
            pygame.draw.rect(screen, bg_col, (30, y - 2, config.WIDTH - 60, row_h - 2))
        marker = "► " if is_live else "  "
        label  = f"{marker}{dev_idx:3d}  {name}"
        color  = (255, 255, 100) if is_sel else (140, 140, 140)
        screen.blit(font.render(label, True, color), (40, y))


# ── Main loop ─────────────────────────────────────────────────────────────────

_CROSSFADE_FRAMES = 45
_BG_MODES         = 9    # indices 0..8 available as background layers

def main():
    # ── CLI args ──────────────────────────────────────────────────────────────
    ap = argparse.ArgumentParser(description="psysuals music visualizer")
    ap.add_argument("--display", type=int, default=0,
                    help="Display index to launch on (default: 0)")
    ap.add_argument("--mode", type=int, default=None,
                    help="Start on this mode index (overrides saved setting)")
    args = ap.parse_args()

    pygame.init()
    try:
        num_displays = pygame.display.get_num_displays()
    except Exception:
        num_displays = 1
    display_idx = max(0, min(args.display, num_displays - 1))

    def _open_display(idx, fullscreen):
        flags = pygame.FULLSCREEN if fullscreen else 0
        # display= kwarg requires working RANDR; fall back silently if unavailable
        if num_displays > 1:
            try:
                return pygame.display.set_mode(
                    (config.WIDTH, config.HEIGHT), flags, display=idx)
            except Exception:
                pass
        return pygame.display.set_mode((config.WIDTH, config.HEIGHT), flags)

    screen     = _open_display(display_idx, True)
    fullscreen = True
    pygame.display.set_caption(f"psysuals v{__version__}")
    config.WIDTH, config.HEIGHT = screen.get_size()
    clock  = pygame.time.Clock()
    font   = pygame.font.SysFont("monospace", 16)
    font_s = pygame.font.SysFont("monospace", 14)

    # ── Settings ─────────────────────────────────────────────────────────────
    _s = sett.load()

    devices    = _input_devices()
    active_dev = _s["active_dev"]
    if active_dev is not None and active_dev not in [d[0] for d in devices]:
        active_dev = None
    stream = sd.InputStream(
        samplerate=config.SAMPLE_RATE, blocksize=config.BLOCK_SIZE,
        channels=config.CHANNELS, device=active_dev, callback=_audio_cb)
    stream.start()

    mode_idx      = min(_s["mode_idx"], len(MODES) - 1)
    if args.mode is not None:
        mode_idx = args.mode % len(MODES)
    name, VisCls  = MODES[mode_idx]
    vis           = VisCls()
    tick          = 0
    energy_hist   = deque(maxlen=15)
    energy_sum    = 0.0
    dev_name_cache = {None: "default"}
    picking       = False
    pick_sel      = 0
    effect_gain   = _s.get("effect_gain", 1.0)
    current_genre = "detecting…"

    # Task 15: HUD detail level — 2=full, 1=minimal, 0=off
    hud_level  = _s.get("hud_level", 2)
    show_hud   = hud_level > 0

    # Task 3: adaptive intensity
    auto_gain  = _s.get("auto_gain", False)
    rms_buf    = deque(maxlen=30)
    target_rms = 0.05    # typical speech/music RMS in float PCM

    # Tap tempo (M key)
    tap_times      = deque(maxlen=4)
    tap_bpm        = 0.0
    tap_bpm_expiry = 0.0
    _TAP_EXPIRE    = 8.0   # seconds before tap BPM falls back to auto
    tap_flash_end  = 0.0   # monotonic time when tap flash overlay expires

    # Task 2: crossfade
    prev_surf       = None   # snapshot taken at mode switch
    crossfade_frame = 0

    # Task 5: background layer at configurable alpha
    bg_on      = _s.get("bg_on", False)
    bg_mode_i  = _s.get("bg_mode_i", 0) % _BG_MODES
    bg_name, bg_cls = MODES[bg_mode_i]
    bg_vis     = bg_cls()
    bg_surf    = pygame.Surface((config.WIDTH, config.HEIGHT))

    # Task 12: presets
    presets       = sett.load_presets()
    active_preset = -1   # index into presets list, -1 = none loaded

    # Task 13: settings pane
    pane_open = False
    pane_sel  = 0          # 0=effect_gain, 1=bg_alpha, 2=crossfade_frames
    bg_alpha  = _s.get("bg_alpha", 102)          # 102 ≈ 40 % of 255
    cf_frames = _s.get("cf_frames", _CROSSFADE_FRAMES)

    # Task 14: span mode — subprocess approach
    span_mode     = False
    span_vis2_idx = (mode_idx + 1) % len(MODES)
    span_child    = None   # subprocess.Popen for second-display process

    def _quit():
        """Exit fullscreen before destroying the display so SDL restores all monitors."""
        nonlocal span_child
        if span_child and span_child.poll() is None:
            span_child.terminate()
        span_child = None
        try:
            pygame.display.set_mode((1, 1))  # drop fullscreen first
        except Exception:
            pass
        stream.stop(); stream.close()
        pygame.quit()

    def _save_settings():
        sett.save({
            "active_dev": active_dev, "mode_idx": mode_idx,
            "effect_gain": effect_gain, "show_hud": show_hud,
            "auto_gain": auto_gain, "bg_on": bg_on,
            "bg_mode_i": bg_mode_i, "display_idx": display_idx,
            "bg_alpha": bg_alpha, "cf_frames": cf_frames,
            "hud_level": hud_level,
        })

    def make_fade(alpha=28):
        s = pygame.Surface((config.WIDTH, config.HEIGHT))
        s.set_alpha(alpha)
        s.fill((0, 0, 0))
        return s

    fade_alpha = 28
    fade       = make_fade()

    def _switch_mode(new_idx):
        nonlocal mode_idx, name, VisCls, vis, prev_surf, crossfade_frame
        prev_surf       = screen.copy()
        crossfade_frame = 0
        mode_idx        = new_idx % len(MODES)
        name, VisCls    = MODES[mode_idx]
        vis             = VisCls()

    # Task 13: pane slider adjustment
    def _pane_adjust(delta):
        nonlocal effect_gain, bg_alpha, cf_frames
        if pane_sel == 0:
            effect_gain = min(2.0, max(0.0, round(effect_gain + delta * 0.1, 1)))
        elif pane_sel == 1:
            bg_alpha = min(255, max(0, bg_alpha + delta * 5))
        elif pane_sel == 2:
            cf_frames = min(90, max(0, cf_frames + delta * 5))

    # Task 13: draw the settings pane on the right side
    def _draw_pane():
        PW, PH = 240, 160
        px = config.WIDTH - PW - 12
        py = 50
        panel = pygame.Surface((PW, PH), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 185))
        screen.blit(panel, (px, py))
        pygame.draw.rect(screen, (80, 80, 80), (px, py, PW, PH), 1)
        title_surf = font_s.render("Settings  (Tab: close)", True, (120, 120, 120))
        screen.blit(title_surf, (px + 8, py + 6))
        items = [
            ("effect_gain", effect_gain, 2.0,  f"{effect_gain:.1f}"),
            ("bg_alpha",    bg_alpha,    255,   f"{bg_alpha}"),
            ("crossfade",   cf_frames,   90,    f"{int(cf_frames)} fr"),
        ]
        for i, (lbl, val, max_val, vstr) in enumerate(items):
            y   = py + 30 + i * 42
            sel = i == pane_sel
            col = (255, 255, 100) if sel else (150, 150, 150)
            marker = "▶ " if sel else "  "
            screen.blit(font_s.render(f"{marker}{lbl}: {vstr}", True, col), (px + 10, y))
            bw    = PW - 24
            bar_w = int(bw * max(0.0, min(val / max_val, 1.0)))
            pygame.draw.rect(screen, (50, 50, 50), (px + 10, y + 16, bw, 6))
            if bar_w > 0:
                pygame.draw.rect(screen, col, (px + 10, y + 16, bar_w, 6))

    # Task 16: draw 3 vertical energy bars at left edge (bass/mid/treble)
    def _draw_multiband_bars(beat_val, mid_val, treble_val):
        BAR_W   = 8
        BAR_MAX = 120
        GAP     = 3
        total_w = 3 * BAR_W + 2 * GAP
        bar_surf = pygame.Surface((total_w, BAR_MAX), pygame.SRCALPHA)
        defs = [
            (beat_val,   (180, 50,  50,  150)),   # bass — red
            (mid_val,    (50,  180, 50,  150)),   # mid  — green
            (treble_val, (130, 60,  200, 150)),   # treble — purple
        ]
        for i, (val, col) in enumerate(defs):
            h = int(BAR_MAX * max(0.0, min(val / 3.0, 1.0)))
            x = i * (BAR_W + GAP)
            if h > 0:
                pygame.draw.rect(bar_surf, col, (x, BAR_MAX - h, BAR_W, h))
        screen.blit(bar_surf, (6, config.HEIGHT - BAR_MAX - 6))

    hint = ("  ←/→: mode  |  ↑/↓: intensity  |  A: auto-gain"
            "  |  B: bg  |  Shift+B: bg-cycle  |  M: tap  |  Shift+M: span"
            "  |  Tab: pane  |  P: preset  |  Shift+P: load"
            "  |  1-{n}: jump  |  D: device  |  F: fullscreen"
            "  |  H: HUD  |  Shift+H: detail  |  Q: quit"
            ).format(n=len(MODES))

    # ── Event loop ───────────────────────────────────────────────────────────
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                _save_settings(); _quit(); return

            elif event.type == pygame.KEYDOWN:

                if picking:
                    if event.key == pygame.K_ESCAPE:
                        picking = False
                    elif event.key == pygame.K_UP:
                        pick_sel = max(0, pick_sel - 1)
                    elif event.key == pygame.K_DOWN:
                        pick_sel = min(len(devices) - 1, pick_sel + 1)
                    elif event.key == pygame.K_RETURN:
                        new_idx = devices[pick_sel][0]
                        if new_idx != active_dev:
                            stream.stop(); stream.close()
                            active_dev = new_idx
                            stream = sd.InputStream(
                                samplerate=config.SAMPLE_RATE,
                                blocksize=config.BLOCK_SIZE,
                                channels=config.CHANNELS, device=active_dev,
                                callback=_audio_cb)
                            stream.start()
                        picking = False

                else:
                    shift = event.mod & pygame.KMOD_SHIFT

                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        _save_settings(); _quit(); return

                    # Task 13: Tab toggles settings pane
                    elif event.key == pygame.K_TAB:
                        pane_open = not pane_open

                    # ←/→ / Space: cycle mode or adjust pane slider
                    elif event.key in (pygame.K_SPACE, pygame.K_RIGHT):
                        if pane_open:
                            _pane_adjust(+1)
                        else:
                            _switch_mode(mode_idx + 1)
                    elif event.key == pygame.K_LEFT:
                        if pane_open:
                            _pane_adjust(-1)
                        else:
                            _switch_mode(mode_idx - 1)

                    # ↑/↓: intensity or navigate pane
                    elif event.key == pygame.K_UP:
                        if pane_open:
                            pane_sel = max(0, pane_sel - 1)
                        else:
                            effect_gain = min(2.0, round(effect_gain + 0.1, 1))
                    elif event.key == pygame.K_DOWN:
                        if pane_open:
                            pane_sel = min(2, pane_sel + 1)
                        else:
                            effect_gain = max(0.0, round(effect_gain - 0.1, 1))

                    elif event.key == pygame.K_f:
                        if span_mode:
                            span_mode = False
                            if span_child and span_child.poll() is None:
                                span_child.terminate()
                            span_child = None
                        else:
                            fullscreen = not fullscreen
                        screen = _open_display(display_idx, fullscreen)
                        config.WIDTH, config.HEIGHT = screen.get_size()
                        prev_surf = None; crossfade_frame = 0
                        fade = make_fade(); vis = VisCls()
                        bg_surf = pygame.Surface((config.WIDTH, config.HEIGHT))

                    # Task 15: H = toggle HUD on/off; Shift+H = cycle detail level
                    elif event.key == pygame.K_h:
                        if shift:
                            hud_level = (hud_level - 1) % 3   # 2 → 1 → 0 → 2
                            show_hud  = hud_level > 0
                        else:
                            show_hud  = not show_hud
                            hud_level = 2 if show_hud else 0

                    elif event.key == pygame.K_d:
                        if span_mode:
                            span_vis2_idx = (span_vis2_idx + 1) % len(MODES)
                            if span_child and span_child.poll() is None:
                                span_child.terminate()
                            span_child = subprocess.Popen([
                                sys.executable, os.path.abspath(__file__),
                                '--display', str(1 - display_idx),
                                '--mode',    str(span_vis2_idx),
                            ])
                        else:
                            devices = _input_devices(); picking = True
                            active_indices = [d[0] for d in devices]
                            pick_sel = (active_indices.index(active_dev)
                                        if active_dev in active_indices else 0)

                    elif event.key == pygame.K_a:
                        if span_mode:
                            span_vis2_idx = (span_vis2_idx - 1) % len(MODES)
                            if span_child and span_child.poll() is None:
                                span_child.terminate()
                            span_child = subprocess.Popen([
                                sys.executable, os.path.abspath(__file__),
                                '--display', str(1 - display_idx),
                                '--mode',    str(span_vis2_idx),
                            ])
                        else:
                            auto_gain = not auto_gain

                    elif event.key == pygame.K_b:
                        if shift:
                            # Shift+B: cycle background effect and ensure bg is on
                            bg_mode_i = (bg_mode_i + 1) % _BG_MODES
                            bg_name, bg_cls = MODES[bg_mode_i]
                            bg_vis = bg_cls()
                            bg_on = True
                        else:
                            bg_on = not bg_on

                    # M: tap tempo; Shift+M: toggle span mode (Task 14)
                    elif event.key == pygame.K_m:
                        if shift:
                            span_mode = not span_mode
                            if span_mode:
                                if num_displays >= 2:
                                    span_child = subprocess.Popen([
                                        sys.executable, os.path.abspath(__file__),
                                        '--display', str(1 - display_idx),
                                        '--mode',    str(span_vis2_idx),
                                    ])
                                else:
                                    # Only one display — no second process to spawn
                                    span_mode = False
                            else:
                                if span_child and span_child.poll() is None:
                                    span_child.terminate()
                                span_child = None
                            prev_surf = None; crossfade_frame = 0
                        else:
                            now = _time.monotonic()
                            tap_times.append(now)
                            tap_bpm_expiry = now + _TAP_EXPIRE
                            tap_flash_end  = now + 2.0
                            if len(tap_times) >= 2:
                                intervals = [tap_times[i] - tap_times[i-1]
                                             for i in range(1, len(tap_times))]
                                med = sorted(intervals)[len(intervals) // 2]
                                if med > 0:
                                    tap_bpm = max(60.0, min(200.0, 60.0 / med))

                    # Task 12: P = save preset; Shift+P = cycle presets
                    elif event.key == pygame.K_p:
                        if shift:
                            if presets:
                                active_preset = (active_preset + 1) % len(presets)
                                p = presets[active_preset]
                                _switch_mode(p["mode_idx"])
                                effect_gain = p.get("effect_gain", effect_gain)
                                bg_on       = p.get("bg_on", bg_on)
                                bg_mode_i   = p.get("bg_mode_i", bg_mode_i)
                                bg_name, bg_cls = MODES[bg_mode_i]
                                bg_vis = bg_cls()
                        else:
                            n     = len(presets) + 1
                            pname = f"Preset {n}"
                            sett.save_preset(pname, {
                                "mode_idx":   mode_idx,
                                "effect_gain": effect_gain,
                                "bg_on":      bg_on,
                                "bg_mode_i":  bg_mode_i,
                            })
                            presets       = sett.load_presets()
                            active_preset = len(presets) - 1

                    else:
                        idx = event.key - pygame.K_1
                        if 0 <= idx < len(MODES):
                            _switch_mode(idx)

            elif event.type == pygame.MOUSEBUTTONDOWN and not picking:
                _switch_mode(mode_idx + 1)

        # ── Audio ─────────────────────────────────────────────────────────────
        detected = detect_genre()
        if detected is not None:
            current_genre = detected
            _apply_genre_weights(detected)
            palette.set_genre(detected)

        waveform, fft, raw_beat, mid_e, treble_e, bpm = get_audio()
        config.MID_ENERGY    = mid_e
        config.TREBLE_ENERGY = treble_e
        config.EFFECT_GAIN   = effect_gain
        # Tap tempo overrides auto-detected BPM for _TAP_EXPIRE seconds
        if tap_bpm > 0 and _time.monotonic() < tap_bpm_expiry:
            config.BPM = tap_bpm
            bpm        = tap_bpm
            _using_tap = True
        else:
            config.BPM = bpm
            _using_tap = False

        if len(energy_hist) == energy_hist.maxlen:
            energy_sum -= energy_hist[0]
        energy_hist.append(raw_beat)
        energy_sum += raw_beat
        avg  = energy_sum / len(energy_hist) if energy_hist else 1e-6
        beat = max(0.0, min(raw_beat / (avg + 1e-6) - 1.0, 3.0))

        # Task 3: adaptive intensity
        rms_buf.append(float(np.sqrt(np.mean(waveform ** 2))))
        if auto_gain and rms_buf:
            cur_rms    = float(np.mean(rms_buf)) + 1e-9
            auto_scale = max(0.5, min(target_rms / cur_rms, 2.0))
            draw_beat  = beat * auto_scale
        else:
            draw_beat  = beat * effect_gain

        # Update shared palette
        palette.update(beat, mid_e, treble_e, tick)

        # ── Draw ──────────────────────────────────────────────────────────────
        # Genre trail_alpha takes precedence when genre is known
        genre_alpha = palette.trail_alpha if current_genre not in ("detecting…",) else None
        new_alpha = genre_alpha if genre_alpha is not None else getattr(vis, 'TRAIL_ALPHA', 28)
        if new_alpha != fade_alpha:
            fade_alpha = new_alpha
            fade = make_fade(fade_alpha)
        screen.blit(fade, (0, 0))

        # Task 5: background layer at configurable alpha
        if bg_on:
            bg_surf.fill((0, 0, 0))
            bg_vis.draw(bg_surf, waveform, fft, draw_beat, tick)
            bg_surf.set_alpha(bg_alpha)
            screen.blit(bg_surf, (0, 0))

        # Foreground effect
        vis.draw(screen, waveform, fft, draw_beat, tick)

        # Crossfade overlay — ease-in-out cubic dissolve
        if prev_surf is not None:
            frames = max(1, int(cf_frames))
            t      = crossfade_frame / frames
            ease   = t * t * (3.0 - 2.0 * t)    # smoothstep
            prev_surf.set_alpha(int(255 * (1.0 - ease)))
            screen.blit(prev_surf, (0, 0))
            crossfade_frame += 1
            if crossfade_frame >= frames:
                prev_surf = None

        # ── Tap tempo flash ───────────────────────────────────────────────────
        now = _time.monotonic()
        if tap_bpm > 0 and now < tap_flash_end:
            t_left  = tap_flash_end - now          # 0..2
            alpha   = int(180 * min(t_left, 1.0))  # fade in 1 s, hold, then out
            W, H    = config.WIDTH, config.HEIGHT
            flash   = pygame.Surface((W, H), pygame.SRCALPHA)
            flash.fill((255, 255, 255, alpha // 6)) # subtle white pulse
            screen.blit(flash, (0, 0))
            font_big = pygame.font.SysFont("monospace", 72, bold=True)
            lbl = font_big.render(f"{tap_bpm:.0f} BPM", True,
                                  (255, 255, 255, alpha))
            screen.blit(lbl, (W // 2 - lbl.get_width() // 2,
                               H // 2 - lbl.get_height() // 2))

        # ── HUD ───────────────────────────────────────────────────────────────
        if show_hud:
            # Task 16: multi-band vertical bars at left edge
            _draw_multiband_bars(beat, mid_e, treble_e)

            if active_dev not in dev_name_cache:
                dev_name_cache[active_dev] = sd.query_devices(active_dev)["name"]
            dev_name    = dev_name_cache[active_dev]
            gain_str    = "auto" if auto_gain else f"{effect_gain:.1f}"
            bg_str      = f"  bg:{bg_name}" if bg_on else ""
            disp_str    = f"  disp:{display_idx}/{num_displays-1}"
            preset_str  = (f"  preset:{presets[active_preset]['name']}"
                           if 0 <= active_preset < len(presets) else "")

            if hud_level >= 2:
                # Full HUD
                row1 = font.render(
                    f"  [{mode_idx+1}/{len(MODES)}] {name}{bg_str}  |  intensity:{gain_str}"
                    f"  |  genre:{current_genre}{disp_str}{preset_str}  |  🎤 {dev_name}{hint}",
                    True, (90, 90, 90))
                screen.blit(row1, (6, 6))

                # Row 2 — BPM + energy bars
                y2      = row1.get_height() + 8
                bpm_tag = " tap" if _using_tap else ""
                bpm_lbl = font_s.render(
                    f"  BPM:{bpm:5.1f}{bpm_tag}" if bpm > 0 else "  BPM: --.-",
                    True, (70, 70, 70))
                screen.blit(bpm_lbl, (6, y2))
                bx = bpm_lbl.get_width() + 16

                def _bar(label, val, max_val, colour, x):
                    lbl = font_s.render(label, True, (70, 70, 70))
                    screen.blit(lbl, (x, y2))
                    bx2 = x + lbl.get_width() + 4
                    w   = int(80 * max(0.0, min(val / max_val, 1.0)))
                    if w > 0:
                        pygame.draw.rect(screen, colour, (bx2, y2 + 2, w, 13))
                    return bx2 + 88

                bx = _bar("beat", beat,     3.0, (180, 50,  50),  bx)
                bx = _bar(" mid", mid_e,    2.0, (50,  180, 50),  bx)
                bx = _bar(" tri", treble_e, 2.0, (130, 60, 200),  bx)

                # Row 3 — particle count (when applicable)
                if hasattr(vis, "_n"):
                    screen.blit(
                        font_s.render(f"  particles: {vis._n}", True, (60, 60, 60)),
                        (6, y2 + 20))

            elif hud_level == 1:
                # Minimal HUD: mode + BPM only
                bpm_tag = " tap" if _using_tap else ""
                bpm_str = f"{bpm:5.1f}{bpm_tag}" if bpm > 0 else "--.-"
                screen.blit(
                    font_s.render(
                        f"  [{mode_idx+1}/{len(MODES)}] {name}  |  BPM:{bpm_str}",
                        True, (70, 70, 70)),
                    (6, 6))

        # Task 13: settings pane overlay
        if pane_open:
            _draw_pane()

        if picking:
            _draw_device_picker(screen, font, devices, pick_sel, active_dev)

        pygame.display.flip()
        clock.tick(config.FPS)
        tick += 1


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Ctrl+C: restore monitors before exiting
        try:
            pygame.display.set_mode((1, 1))
        except Exception:
            pass
        pygame.quit()
