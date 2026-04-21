#!/usr/bin/env python3
"""
Music Visualizer — real-time audio -> visuals.

Controls:
  SPACE / click   Switch to next mode
  1-9             Jump to modes 1-9
  Left/Right      Cycle modes (or adjust pane slider when pane is open)
  Up/Down         Intensity (or navigate pane sliders when pane is open)
  Tab             Toggle settings pane
  P               Save preset  |  Shift+P: cycle presets
  F               Toggle fullscreen
  H               Toggle HUD   |  Shift+H: cycle full/minimal/off
  M               Tap tempo    |  Shift+M: toggle span mode (all monitors)
  Q / ESC         Quit
"""

from __future__ import annotations

__version__ = "2.15.0"

import argparse
import atexit
import os
import re as _re
import subprocess
import sys
import threading
import time as _time
from collections import deque

import numpy as np
import pygame
import sounddevice as sd

from beat_tracking import LibrosaBeatTracker
import config
import settings as sett
from effects import MODES
from effects.palette import palette


# ── Audio ────────────────────────────────────────────────────────────────────

_lock = threading.Lock()
_waveform = np.zeros(config.BLOCK_SIZE, dtype=np.float32)
_smooth_fft = np.zeros(config.BLOCK_SIZE // 2, dtype=np.float32)
_raw_beat_energy = 0.0
_mid_energy = 0.0
_treble_energy = 0.0
_audio_time = 0.0
_blackman_window = np.blackman(config.BLOCK_SIZE).astype(np.float32)

_prev_spectrum = np.zeros(config.BLOCK_SIZE // 2, dtype=np.float32)
_flux_avg = 1e-6
_mid_avg = 1e-6
_treble_avg = 1e-6
_prev_beat_energy = 0.0

_beat_times = deque(maxlen=8)
_last_onset_time = 0.0
_bpm = 0.0

_genre_weights = np.ones(20, dtype=np.float32)
_detect_accum = np.zeros(config.BLOCK_SIZE // 2, dtype=np.float32)
_detect_frames = 0
_DETECT_MIN = 300

_beat_tracker = LibrosaBeatTracker(
    sample_rate=config.SAMPLE_RATE,
    block_size=config.BLOCK_SIZE,
)


def _apply_genre_weights(genre: str) -> None:
    weights = np.ones(20, dtype=np.float32)
    if genre == "electronic":
        weights[:5] = 1.5
        weights[10:] = 0.7
    elif genre == "rock":
        weights[2:9] = 1.3
    elif genre == "classical":
        weights[:10] = 0.6
        weights[10:] = 1.4
    with _lock:
        _genre_weights[:] = weights


def detect_genre() -> str | None:
    """Return detected genre string once enough frames are collected."""
    global _detect_frames
    with _lock:
        if _detect_frames < _DETECT_MIN:
            return None
        avg = _detect_accum / _detect_frames
        _detect_accum[:] = 0
        _detect_frames = 0

    sub_bass = float(avg[:5].mean())
    bass = float(avg[:15].mean())
    mids = float(avg[15:100].mean())
    sub_ratio = sub_bass / (bass + 1e-6)
    bass_ratio = bass / (bass + mids + 1e-6)

    if sub_ratio > 0.55 and bass_ratio > 0.50:
        return "electronic"
    if bass_ratio > 0.50 and sub_ratio < 0.45:
        return "rock"
    if bass_ratio < 0.35:
        return "classical"
    return "any"


def _audio_cb(indata, frames, time_info, status) -> None:
    global _waveform, _smooth_fft, _raw_beat_energy, _mid_energy, _treble_energy
    global _audio_time, _detect_frames, _prev_spectrum, _flux_avg, _mid_avg
    global _treble_avg, _prev_beat_energy, _last_onset_time, _bpm

    mono = np.asarray(indata[:, 0], dtype=np.float32)
    _beat_tracker.push_audio(mono, time_info.currentTime)

    spectrum = np.abs(np.fft.rfft(mono * _blackman_window))[: config.BLOCK_SIZE // 2]
    spectrum = spectrum.astype(np.float32, copy=False)
    np.log1p(spectrum, out=spectrum)
    spectrum /= 10.0

    with _lock:
        _audio_time = float(time_info.currentTime)
        _waveform = mono.copy()
        _smooth_fft *= 0.50
        _smooth_fft += spectrum * 0.50
        _detect_accum[:] += spectrum
        _detect_frames += 1

        weights = _genre_weights
        flux = float(
            np.mean(
                np.maximum(
                    0.0,
                    spectrum[:20] * weights - _prev_spectrum[:20] * weights,
                )
            )
        )
        _flux_avg = _flux_avg * 0.95 + flux * 0.05
        _raw_beat_energy = flux / (_flux_avg + 1e-6)

        t_now = float(time_info.currentTime)
        if (
            _raw_beat_energy > 2.0
            and _prev_beat_energy <= 2.0
            and t_now - _last_onset_time > 0.30
        ):
            _beat_times.append(t_now)
            _last_onset_time = t_now
            if len(_beat_times) >= 2:
                intervals = np.diff(list(_beat_times))
                median_interval = float(np.median(intervals))
                if median_interval > 0:
                    _bpm = max(60.0, min(200.0, 60.0 / median_interval))
        _prev_beat_energy = _raw_beat_energy

        mid = float(_smooth_fft[20:100].mean())
        _mid_avg = _mid_avg * 0.95 + mid * 0.05
        _mid_energy = mid / (_mid_avg + 1e-6)

        treble = float(_smooth_fft[100:256].mean())
        _treble_avg = _treble_avg * 0.95 + treble * 0.05
        _treble_energy = treble / (_treble_avg + 1e-6)

        _prev_spectrum[:] = spectrum


def get_audio():
    with _lock:
        return (
            _waveform.copy(),
            _smooth_fft.copy(),
            _raw_beat_energy,
            _mid_energy,
            _treble_energy,
            _bpm,
            _audio_time,
        )


# ── Device picker ────────────────────────────────────────────────────────────

def _input_devices() -> list[tuple[int, str]]:
    """Return list of (index, name) for all input-capable devices."""
    devices = []
    for idx, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] > 0:
            devices.append((idx, device["name"]))
    return devices


def _draw_device_picker(screen, font, devices, selected, active_idx) -> None:
    overlay = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 210))
    screen.blit(overlay, (0, 0))

    title = font.render(
        "SELECT INPUT DEVICE   Up/Down navigate   Enter confirm   Esc cancel",
        True,
        (200, 200, 200),
    )
    screen.blit(title, (40, 30))

    row_h = 28
    y0 = 80
    visible = min(len(devices), (config.HEIGHT - y0 - 20) // row_h)
    start = max(0, min(selected - visible // 2, len(devices) - visible))

    for i, (dev_idx, name) in enumerate(devices[start : start + visible]):
        row = start + i
        y = y0 + i * row_h
        is_selected = row == selected
        is_active = dev_idx == active_idx
        if is_selected:
            pygame.draw.rect(screen, (40, 80, 140), (30, y - 2, config.WIDTH - 60, row_h - 2))
        marker = ">> " if is_active else "   "
        label = f"{marker}{dev_idx:3d}  {name}"
        color = (255, 255, 100) if is_selected else (140, 140, 140)
        screen.blit(font.render(label, True, color), (40, y))


# ── Main loop ────────────────────────────────────────────────────────────────

_CROSSFADE_FRAMES = 45
_BG_MODES = 9

_x11_err_handler_ref = None
_libX11 = None


def _install_x11_error_handler() -> None:
    """Suppress X11 RandR errors on some multi-monitor X11 setups."""
    global _x11_err_handler_ref, _libX11
    try:
        import ctypes

        class _XErrorEvent(ctypes.Structure):
            _fields_ = [
                ("type", ctypes.c_int),
                ("display", ctypes.c_void_p),
                ("resourceid", ctypes.c_ulong),
                ("serial", ctypes.c_ulong),
                ("error_code", ctypes.c_ubyte),
                ("request_code", ctypes.c_ubyte),
                ("minor_code", ctypes.c_ubyte),
            ]

        handler_type = ctypes.CFUNCTYPE(
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.POINTER(_XErrorEvent),
        )

        def _handler(display, event):
            return 0

        _x11_err_handler_ref = handler_type(_handler)
        lib = ctypes.CDLL("libX11.so.6")
        lib.XSetErrorHandler(_x11_err_handler_ref)
        lib.XMoveWindow.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_int,
        ]
        lib.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
        _libX11 = lib
    except Exception:
        pass


def _xrandr_monitors() -> list[tuple[int, int, int, int]]:
    """Return list of (x, y, w, h) for each physical monitor."""
    try:
        out = subprocess.check_output(
            ["xrandr", "--listmonitors"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        monitors = []
        for line in out.splitlines():
            match = _re.search(r"(\d+)/\d+x(\d+)/\d+\+(\d+)\+(\d+)", line)
            if match:
                w, h, x, y = (int(match.group(i)) for i in range(1, 5))
                monitors.append((x, y, w, h))
        monitors.sort(key=lambda mon: mon[0])
        return monitors
    except Exception:
        return []


def main() -> None:
    parser = argparse.ArgumentParser(description="psysuals music visualizer")
    parser.add_argument(
        "--display",
        type=int,
        default=0,
        help="Display index to open on (default: 0)",
    )
    parser.add_argument(
        "--mode",
        type=int,
        default=None,
        help="Start on this mode index (overrides saved setting)",
    )
    args = parser.parse_args()

    xmonitors = _xrandr_monitors()
    num_displays = max(len(xmonitors), 1)
    display_idx = max(0, min(args.display, num_displays - 1))

    _install_x11_error_handler()
    pygame.init()

    _xmove_target = None

    def _open_display(idx: int, fullscreen: bool):
        nonlocal _xmove_target
        _xmove_target = None
        if fullscreen and idx < len(xmonitors):
            mx, my, mw, mh = xmonitors[idx]
            os.environ["SDL_VIDEO_WINDOW_POS"] = f"{mx},{my}"
            screen = pygame.display.set_mode((mw, mh), pygame.NOFRAME)
            os.environ.pop("SDL_VIDEO_WINDOW_POS", None)
            if _libX11:
                wm = pygame.display.get_wm_info()
                dpy = wm.get("display")
                win = wm.get("window")
                if isinstance(dpy, int) and dpy and win:
                    _libX11.XMoveWindow(dpy, win, mx, my)
                    _libX11.XSync(dpy, 0)
                    _xmove_target = (dpy, win, mx, my)
            config.WIDTH = mw
            config.HEIGHT = mh
            return screen
        if fullscreen:
            screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            config.WIDTH, config.HEIGHT = screen.get_size()
            return screen
        return pygame.display.set_mode((config.WIDTH, config.HEIGHT), 0)

    screen = _open_display(display_idx, True)
    fullscreen = True

    pygame.display.set_caption(f"psysuals v{__version__}")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 16)
    font_s = pygame.font.SysFont("monospace", 14)

    settings = sett.load()
    devices = _input_devices()
    active_dev = settings["active_dev"]
    if active_dev is not None and active_dev not in [d[0] for d in devices]:
        active_dev = None

    stream = sd.InputStream(
        samplerate=config.SAMPLE_RATE,
        blocksize=config.BLOCK_SIZE,
        channels=config.CHANNELS,
        device=active_dev,
        callback=_audio_cb,
    )
    stream.start()

    mode_idx = min(settings["mode_idx"], len(MODES) - 1)
    if args.mode is not None:
        mode_idx = args.mode % len(MODES)
    name, VisCls = MODES[mode_idx]
    vis = VisCls()

    tick = 0
    energy_hist = deque(maxlen=40)
    energy_sum = 0.0
    beat_decay = 0.0
    dev_name_cache = {None: "default"}
    picking = False
    pick_sel = 0
    effect_gain = config.DEFAULT_EFFECT_GAIN
    current_genre = "detecting..."

    hud_level = settings.get("hud_level", 2)
    show_hud = hud_level > 0

    auto_gain = settings.get("auto_gain", False)
    rms_buf = deque(maxlen=30)
    target_rms = 0.05

    tap_times = deque(maxlen=4)
    tap_bpm = 0.0
    tap_bpm_expiry = 0.0
    tap_flash_end = 0.0
    tap_expire = 8.0

    prev_surf = None
    crossfade_frame = 0

    bg_on = settings.get("bg_on", False)
    bg_mode_i = settings.get("bg_mode_i", 0) % _BG_MODES
    bg_name, bg_cls = MODES[bg_mode_i]
    bg_vis = bg_cls()
    bg_surf = pygame.Surface((config.WIDTH, config.HEIGHT))

    presets = sett.load_presets()
    active_preset = -1

    pane_open = False
    pane_sel = 0
    bg_alpha = settings.get("bg_alpha", 102)
    cf_frames = settings.get("cf_frames", _CROSSFADE_FRAMES)

    span_vis2_idx = (mode_idx + 1) % len(MODES)
    span_child = None

    def _spawn_span_child(mode_i: int):
        child_idx = 1 - display_idx
        return subprocess.Popen(
            [
                sys.executable,
                os.path.abspath(__file__),
                "--display",
                str(child_idx),
                "--mode",
                str(mode_i),
            ]
        )

    span_mode = len(xmonitors) >= 2 and display_idx == 0
    if span_mode:
        span_child = _spawn_span_child(span_vis2_idx)

    def _kill_child() -> None:
        nonlocal span_child
        if span_child and span_child.poll() is None:
            span_child.terminate()
        span_child = None

    atexit.register(_kill_child)

    def _quit() -> None:
        _kill_child()
        try:
            pygame.display.set_mode((1, 1))
        except Exception:
            pass
        try:
            stream.stop()
        finally:
            stream.close()
        pygame.quit()

    def _save_settings() -> None:
        sett.save(
            {
                "active_dev": active_dev,
                "mode_idx": mode_idx,
                "show_hud": show_hud,
                "auto_gain": auto_gain,
                "bg_on": bg_on,
                "bg_mode_i": bg_mode_i,
                "display_idx": display_idx,
                "bg_alpha": bg_alpha,
                "cf_frames": cf_frames,
                "hud_level": hud_level,
            }
        )

    def make_fade(alpha: int = 28):
        surf = pygame.Surface((config.WIDTH, config.HEIGHT))
        surf.set_alpha(alpha)
        surf.fill((0, 0, 0))
        return surf

    fade_alpha = 28
    fade = make_fade()

    def _switch_mode(new_idx: int) -> None:
        nonlocal mode_idx, name, VisCls, vis, prev_surf, crossfade_frame, effect_gain
        if hasattr(vis, "release") and callable(vis.release):
            vis.release()
        prev_surf = screen.copy()
        crossfade_frame = 0
        mode_idx = new_idx % len(MODES)
        name, VisCls = MODES[mode_idx]
        vis = VisCls()
        effect_gain = config.DEFAULT_EFFECT_GAIN

    def _pane_adjust(delta: int) -> None:
        nonlocal effect_gain, bg_alpha, cf_frames
        if pane_sel == 0:
            effect_gain = min(2.0, max(0.0, round(effect_gain + delta * 0.1, 1)))
        elif pane_sel == 1:
            bg_alpha = min(255, max(0, bg_alpha + delta * 5))
        elif pane_sel == 2:
            cf_frames = min(90, max(0, cf_frames + delta * 5))

    def _draw_pane() -> None:
        panel_w, panel_h = 240, 160
        px = config.WIDTH - panel_w - 12
        py = 50
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 185))
        screen.blit(panel, (px, py))
        pygame.draw.rect(screen, (80, 80, 80), (px, py, panel_w, panel_h), 1)
        title = font_s.render("Settings  (Tab: close)", True, (120, 120, 120))
        screen.blit(title, (px + 8, py + 6))
        items = [
            ("effect_gain", effect_gain, 2.0, f"{effect_gain:.1f}"),
            ("bg_alpha", bg_alpha, 255, f"{bg_alpha}"),
            ("crossfade", cf_frames, 90, f"{int(cf_frames)} fr"),
        ]
        for i, (label, value, max_value, value_str) in enumerate(items):
            y = py + 30 + i * 42
            selected = i == pane_sel
            color = (255, 255, 100) if selected else (150, 150, 150)
            marker = ">> " if selected else "   "
            screen.blit(
                font_s.render(f"{marker}{label}: {value_str}", True, color),
                (px + 10, y),
            )
            bar_total = panel_w - 24
            bar_w = int(bar_total * max(0.0, min(value / max_value, 1.0)))
            pygame.draw.rect(screen, (50, 50, 50), (px + 10, y + 16, bar_total, 6))
            if bar_w > 0:
                pygame.draw.rect(screen, color, (px + 10, y + 16, bar_w, 6))

    def _draw_multiband_bars(beat_val: float, mid_val: float, treble_val: float) -> None:
        bar_w = 8
        bar_max = 120
        gap = 3
        total_w = 3 * bar_w + 2 * gap
        bar_surf = pygame.Surface((total_w, bar_max), pygame.SRCALPHA)
        defs = [
            (beat_val, (180, 50, 50, 150)),
            (mid_val, (50, 180, 50, 150)),
            (treble_val, (130, 60, 200, 150)),
        ]
        for i, (value, color) in enumerate(defs):
            h = int(bar_max * max(0.0, min(value / 3.0, 1.0)))
            x = i * (bar_w + gap)
            if h > 0:
                pygame.draw.rect(bar_surf, color, (x, bar_max - h, bar_w, h))
        screen.blit(bar_surf, (6, config.HEIGHT - bar_max - 6))

    hint = (
        "  Left/Right: mode  |  Up/Down: intensity  |  A: auto-gain"
        "  |  B: bg  |  Shift+B: bg-cycle  |  M: tap  |  Shift+M: span"
        "  |  Tab: pane  |  P: preset  |  Shift+P: load"
        "  |  1-{n}: jump  |  D: device  |  F: fullscreen"
        "  |  H: HUD  |  Shift+H: detail  |  Q: quit"
    ).format(n=len(MODES))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                _save_settings()
                _quit()
                return

            if event.type == pygame.KEYDOWN:
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
                            stream.stop()
                            stream.close()
                            active_dev = new_idx
                            stream = sd.InputStream(
                                samplerate=config.SAMPLE_RATE,
                                blocksize=config.BLOCK_SIZE,
                                channels=config.CHANNELS,
                                device=active_dev,
                                callback=_audio_cb,
                            )
                            stream.start()
                        picking = False
                    continue

                shift = bool(event.mod & pygame.KMOD_SHIFT)

                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    _save_settings()
                    _quit()
                    return
                if event.key == pygame.K_TAB:
                    pane_open = not pane_open
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
                        _kill_child()
                    else:
                        fullscreen = not fullscreen
                    screen = _open_display(display_idx, fullscreen)
                    config.WIDTH, config.HEIGHT = screen.get_size()
                    prev_surf = None
                    crossfade_frame = 0
                    fade = make_fade(fade_alpha)
                    vis = VisCls()
                    bg_surf = pygame.Surface((config.WIDTH, config.HEIGHT))
                elif event.key == pygame.K_h:
                    if shift:
                        hud_level = (hud_level - 1) % 3
                        show_hud = hud_level > 0
                    else:
                        show_hud = not show_hud
                        hud_level = 2 if show_hud else 0
                elif event.key == pygame.K_d:
                    if span_mode:
                        span_vis2_idx = (span_vis2_idx + 1) % len(MODES)
                        _kill_child()
                        span_child = _spawn_span_child(span_vis2_idx)
                    else:
                        devices = _input_devices()
                        picking = True
                        active_indices = [d[0] for d in devices]
                        pick_sel = active_indices.index(active_dev) if active_dev in active_indices else 0
                elif event.key == pygame.K_a:
                    if span_mode:
                        span_vis2_idx = (span_vis2_idx - 1) % len(MODES)
                        _kill_child()
                        span_child = _spawn_span_child(span_vis2_idx)
                    else:
                        auto_gain = not auto_gain
                elif event.key == pygame.K_b:
                    if shift:
                        bg_mode_i = (bg_mode_i + 1) % _BG_MODES
                        bg_name, bg_cls = MODES[bg_mode_i]
                        bg_vis = bg_cls()
                        bg_on = True
                    else:
                        bg_on = not bg_on
                elif event.key == pygame.K_m:
                    if shift:
                        span_mode = not span_mode
                        if span_mode:
                            if num_displays >= 2:
                                span_child = _spawn_span_child(span_vis2_idx)
                            else:
                                span_mode = False
                        else:
                            _kill_child()
                        prev_surf = None
                        crossfade_frame = 0
                    else:
                        now = _time.monotonic()
                        tap_times.append(now)
                        tap_bpm_expiry = now + tap_expire
                        tap_flash_end = now + 2.0
                        if len(tap_times) >= 2:
                            intervals = [
                                tap_times[i] - tap_times[i - 1]
                                for i in range(1, len(tap_times))
                            ]
                            median_interval = sorted(intervals)[len(intervals) // 2]
                            if median_interval > 0:
                                tap_bpm = max(60.0, min(200.0, 60.0 / median_interval))
                elif event.key == pygame.K_p:
                    if shift:
                        if presets:
                            active_preset = (active_preset + 1) % len(presets)
                            preset = presets[active_preset]
                            _switch_mode(preset["mode_idx"])
                            effect_gain = preset.get(
                                "effect_gain", config.DEFAULT_EFFECT_GAIN
                            )
                            bg_on = preset.get("bg_on", bg_on)
                            bg_mode_i = preset.get("bg_mode_i", bg_mode_i)
                            bg_name, bg_cls = MODES[bg_mode_i]
                            bg_vis = bg_cls()
                    else:
                        preset_name = f"Preset {len(presets) + 1}"
                        sett.save_preset(
                            preset_name,
                            {
                                "mode_idx": mode_idx,
                                "effect_gain": effect_gain,
                                "bg_on": bg_on,
                                "bg_mode_i": bg_mode_i,
                            },
                        )
                        presets = sett.load_presets()
                        active_preset = len(presets) - 1
                else:
                    idx = event.key - pygame.K_1
                    if 0 <= idx < len(MODES):
                        _switch_mode(idx)

            elif event.type == pygame.MOUSEBUTTONDOWN and not picking:
                _switch_mode(mode_idx + 1)

        detected = detect_genre()
        if detected is not None:
            current_genre = detected
            _apply_genre_weights(detected)
            palette.set_genre(detected)

        waveform, fft, raw_beat, mid_e, treble_e, bpm, audio_time = get_audio()
        if _beat_tracker.enabled:
            bpm = _beat_tracker.analyze(fallback_bpm=bpm)
            raw_beat = _beat_tracker.refine_beat(raw_beat, audio_time)

        config.MID_ENERGY = mid_e
        config.TREBLE_ENERGY = treble_e
        config.EFFECT_GAIN = effect_gain

        if tap_bpm > 0 and _time.monotonic() < tap_bpm_expiry:
            config.BPM = tap_bpm
            bpm = tap_bpm
            using_tap = True
        else:
            config.BPM = bpm
            using_tap = False

        if len(energy_hist) == energy_hist.maxlen:
            energy_sum -= energy_hist[0]
        energy_hist.append(raw_beat)
        energy_sum += raw_beat
        avg = energy_sum / len(energy_hist) if energy_hist else 1e-6

        impulse = max(0.0, min(raw_beat / (avg + 1e-6) - 1.0, 3.0))
        beat_decay = max(impulse, beat_decay * 0.90)
        beat = beat_decay

        rms_buf.append(float(np.sqrt(np.mean(waveform ** 2))))
        if auto_gain and rms_buf:
            cur_rms = float(np.mean(rms_buf)) + 1e-9
            auto_scale = max(0.5, min(target_rms / cur_rms, 2.0))
            draw_beat = beat * auto_scale
        else:
            draw_beat = beat * effect_gain

        palette.update(beat, mid_e, treble_e, tick)

        genre_alpha = palette.trail_alpha if current_genre not in ("detecting...",) else None
        new_alpha = genre_alpha if genre_alpha is not None else getattr(vis, "TRAIL_ALPHA", 28)
        if new_alpha != fade_alpha:
            fade_alpha = new_alpha
            fade = make_fade(fade_alpha)
        screen.blit(fade, (0, 0))

        if bg_on:
            bg_surf.fill((0, 0, 0))
            bg_vis.draw(bg_surf, waveform, fft, draw_beat, tick)
            bg_surf.set_alpha(bg_alpha)
            screen.blit(bg_surf, (0, 0))

        vis.draw(screen, waveform, fft, draw_beat, tick)

        if prev_surf is not None:
            frames = max(1, int(cf_frames))
            t = crossfade_frame / frames
            ease = t * t * (3.0 - 2.0 * t)
            prev_surf.set_alpha(int(255 * (1.0 - ease)))
            screen.blit(prev_surf, (0, 0))
            crossfade_frame += 1
            if crossfade_frame >= frames:
                prev_surf = None

        now = _time.monotonic()
        if tap_bpm > 0 and now < tap_flash_end:
            t_left = tap_flash_end - now
            alpha = int(180 * min(t_left, 1.0))
            flash = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
            flash.fill((255, 255, 255, alpha // 6))
            screen.blit(flash, (0, 0))
            font_big = pygame.font.SysFont("monospace", 72, bold=True)
            label = font_big.render(f"{tap_bpm:.0f} BPM", True, (255, 255, 255, alpha))
            screen.blit(
                label,
                (
                    config.WIDTH // 2 - label.get_width() // 2,
                    config.HEIGHT // 2 - label.get_height() // 2,
                ),
            )

        if show_hud:
            _draw_multiband_bars(beat, mid_e, treble_e)
            if active_dev not in dev_name_cache:
                dev_name_cache[active_dev] = sd.query_devices(active_dev)["name"]
            dev_name = dev_name_cache[active_dev]
            gain_str = "auto" if auto_gain else f"{effect_gain:.1f}"
            bg_str = f"  bg:{bg_name}" if bg_on else ""
            disp_str = f"  disp:{display_idx}/{num_displays - 1}"
            preset_str = (
                f"  preset:{presets[active_preset]['name']}"
                if 0 <= active_preset < len(presets)
                else ""
            )

            if hud_level >= 2:
                row1 = font.render(
                    f"  [{mode_idx + 1}/{len(MODES)}] {name}{bg_str}  |  intensity:{gain_str}"
                    f"  |  genre:{current_genre}{disp_str}{preset_str}  |  mic {dev_name}{hint}",
                    True,
                    (90, 90, 90),
                )
                screen.blit(row1, (6, 6))

                y2 = row1.get_height() + 8
                bpm_tag = " tap" if using_tap else ""
                bpm_label = font_s.render(
                    f"  BPM:{bpm:5.1f}{bpm_tag}" if bpm > 0 else "  BPM: --.-",
                    True,
                    (70, 70, 70),
                )
                screen.blit(bpm_label, (6, y2))
                bx = bpm_label.get_width() + 16

                def _bar(label: str, value: float, max_value: float, color, x: int) -> int:
                    lbl = font_s.render(label, True, (70, 70, 70))
                    screen.blit(lbl, (x, y2))
                    x2 = x + lbl.get_width() + 4
                    width = int(80 * max(0.0, min(value / max_value, 1.0)))
                    if width > 0:
                        pygame.draw.rect(screen, color, (x2, y2 + 2, width, 13))
                    return x2 + 88

                bx = _bar("beat", beat, 3.0, (180, 50, 50), bx)
                bx = _bar(" mid", mid_e, 2.0, (50, 180, 50), bx)
                bx = _bar(" tri", treble_e, 2.0, (130, 60, 200), bx)

                if hasattr(vis, "_n"):
                    screen.blit(
                        font_s.render(f"  particles: {vis._n}", True, (60, 60, 60)),
                        (6, y2 + 20),
                    )
            elif hud_level == 1:
                bpm_tag = " tap" if using_tap else ""
                bpm_str = f"{bpm:5.1f}{bpm_tag}" if bpm > 0 else "--.-"
                screen.blit(
                    font_s.render(
                        f"  [{mode_idx + 1}/{len(MODES)}] {name}  |  BPM:{bpm_str}",
                        True,
                        (70, 70, 70),
                    ),
                    (6, 6),
                )

        if pane_open:
            _draw_pane()

        if picking:
            _draw_device_picker(screen, font, devices, pick_sel, active_dev)

        if _xmove_target and tick < 60:
            dpy, win, mx, my = _xmove_target
            _libX11.XMoveWindow(dpy, win, mx, my)
            _libX11.XSync(dpy, 0)

        pygame.display.flip()
        clock.tick(config.FPS)
        tick += 1


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        try:
            pygame.display.set_mode((1, 1))
        except Exception:
            pass
        pygame.quit()
