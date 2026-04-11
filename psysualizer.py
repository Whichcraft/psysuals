#!/usr/bin/env python3
"""
Music Visualizer — Real-time audio → visuals.

Controls:
  SPACE / click   Switch to next mode
  1-9             Jump to modes 1-9
  1-9             Jump to modes 1-9 (use ←/→ for modes 10+)
  F               Toggle fullscreen
  H               Toggle HUD / legend
  Q / ESC         Quit
"""

__version__ = "2.1.0"

import argparse
import threading
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
_prev_spectrum   = np.zeros(config.BLOCK_SIZE // 2)
_flux_avg        = 1e-6
_mid_avg         = 1e-6
_treble_avg      = 1e-6
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
    """Render the device-picker overlay; returns nothing."""
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
    # ── CLI args (Task 8: multi-screen) ──────────────────────────────────────
    ap = argparse.ArgumentParser(description="psysuals music visualizer")
    ap.add_argument("--display", type=int, default=0,
                    help="Display index to launch on (default: 0)")
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
    name, VisCls  = MODES[mode_idx]
    vis           = VisCls()
    tick          = 0
    energy_hist   = deque(maxlen=15)
    energy_sum    = 0.0
    dev_name_cache = {None: "default"}
    picking       = False
    pick_sel      = 0
    show_hud      = _s.get("show_hud", True)
    effect_gain   = _s.get("effect_gain", 1.0)
    current_genre = "detecting…"

    # Task 3: adaptive intensity
    auto_gain  = _s.get("auto_gain", False)
    rms_buf    = deque(maxlen=30)
    target_rms = 0.05    # typical speech/music RMS in float PCM

    # Task 2: crossfade
    prev_surf       = None   # snapshot taken at mode switch
    crossfade_frame = 0

    # Task 5: background layer
    bg_on      = _s.get("bg_on", False)
    bg_mode_i  = _s.get("bg_mode_i", 0) % _BG_MODES
    bg_name, bg_cls = MODES[bg_mode_i]
    bg_vis     = bg_cls()
    bg_surf    = pygame.Surface((config.WIDTH, config.HEIGHT))

    def _save_settings():
        sett.save({
            "active_dev": active_dev, "mode_idx": mode_idx,
            "effect_gain": effect_gain, "show_hud": show_hud,
            "auto_gain": auto_gain, "bg_on": bg_on,
            "bg_mode_i": bg_mode_i, "display_idx": display_idx,
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

    hint = ("  ←/→: mode  |  ↑/↓: intensity  |  A: auto-gain  "
            "|  B: bg layer  |  Shift+B: bg cycle  |  M: next display  "
            "|  1-{n}: jump  |  D: device  |  F: fullscreen  |  H: HUD  |  Q: quit"
            ).format(n=len(MODES))

    # ── Event loop ───────────────────────────────────────────────────────────
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                _save_settings(); stream.stop(); stream.close()
                pygame.quit(); return

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
                    mods = pygame.key.get_mods()

                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        _save_settings(); stream.stop(); stream.close()
                        pygame.quit(); return

                    elif event.key in (pygame.K_SPACE, pygame.K_RIGHT):
                        _switch_mode(mode_idx + 1)
                    elif event.key == pygame.K_LEFT:
                        _switch_mode(mode_idx - 1)

                    elif event.key == pygame.K_UP:
                        effect_gain = min(2.0, round(effect_gain + 0.1, 1))
                    elif event.key == pygame.K_DOWN:
                        effect_gain = max(0.0, round(effect_gain - 0.1, 1))

                    elif event.key == pygame.K_f:
                        fullscreen = not fullscreen
                        screen = _open_display(display_idx, fullscreen)
                        config.WIDTH, config.HEIGHT = screen.get_size()
                        fade = make_fade(); vis = VisCls()
                        bg_surf = pygame.Surface((config.WIDTH, config.HEIGHT))

                    elif event.key == pygame.K_h:
                        show_hud = not show_hud

                    elif event.key == pygame.K_d:
                        devices = _input_devices(); picking = True
                        active_indices = [d[0] for d in devices]
                        pick_sel = (active_indices.index(active_dev)
                                    if active_dev in active_indices else 0)

                    # Task 3: auto-gain toggle
                    elif event.key == pygame.K_a:
                        auto_gain = not auto_gain

                    # Task 5: background layer
                    elif event.key == pygame.K_b:
                        if mods & pygame.KMOD_SHIFT:
                            bg_mode_i = (bg_mode_i + 1) % _BG_MODES
                            bg_name, bg_cls = MODES[bg_mode_i]
                            bg_vis = bg_cls()
                        else:
                            bg_on = not bg_on

                    # Task 8: cycle display
                    elif event.key == pygame.K_m:
                        display_idx = (display_idx + 1) % num_displays
                        screen = _open_display(display_idx, fullscreen)
                        config.WIDTH, config.HEIGHT = screen.get_size()
                        fade = make_fade(); vis = VisCls()
                        bg_surf = pygame.Surface((config.WIDTH, config.HEIGHT))

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

        waveform, fft, raw_beat, mid_e, treble_e, bpm = get_audio()
        config.MID_ENERGY    = mid_e
        config.TREBLE_ENERGY = treble_e
        config.BPM           = bpm

        if len(energy_hist) == energy_hist.maxlen:
            energy_sum -= energy_hist[0]
        energy_hist.append(raw_beat)
        energy_sum += raw_beat
        avg  = energy_sum / len(energy_hist) if energy_hist else 1e-6
        beat = max(0.0, min(raw_beat / (avg + 1e-6) - 1.0, 3.0))

        # Task 3: adaptive intensity
        rms_buf.append(float(np.sqrt(np.mean(waveform ** 2))))
        if auto_gain and rms_buf:
            cur_rms     = float(np.mean(rms_buf)) + 1e-9
            auto_scale  = max(0.5, min(target_rms / cur_rms, 2.0))
            draw_beat   = beat * auto_scale
        else:
            draw_beat   = beat * effect_gain

        # Update shared palette
        palette.update(beat, mid_e, treble_e, tick)

        # ── Draw ──────────────────────────────────────────────────────────────
        new_alpha = getattr(vis, 'TRAIL_ALPHA', 28)
        if new_alpha != fade_alpha:
            fade_alpha = new_alpha
            fade = make_fade(fade_alpha)
        screen.blit(fade, (0, 0))

        # Task 5: background layer at 40 % alpha
        if bg_on:
            bg_surf.fill((0, 0, 0))
            bg_vis.draw(bg_surf, waveform, fft, draw_beat, tick)
            bg_surf.set_alpha(102)   # ~40 % of 255
            screen.blit(bg_surf, (0, 0))

        # Foreground effect
        vis.draw(screen, waveform, fft, draw_beat, tick)

        # Task 2: crossfade overlay — dissolve old screenshot out
        if prev_surf is not None:
            alpha = int(255 * (1.0 - crossfade_frame / _CROSSFADE_FRAMES))
            prev_surf.set_alpha(alpha)
            screen.blit(prev_surf, (0, 0))
            crossfade_frame += 1
            if crossfade_frame >= _CROSSFADE_FRAMES:
                prev_surf = None

        # ── HUD (Tasks 7 + 8) ─────────────────────────────────────────────────
        if show_hud:
            if active_dev not in dev_name_cache:
                dev_name_cache[active_dev] = sd.query_devices(active_dev)["name"]
            dev_name    = dev_name_cache[active_dev]
            gain_str    = "auto" if auto_gain else f"{effect_gain:.1f}"
            bg_str      = f"  bg:{bg_name}" if bg_on else ""
            disp_str    = f"  disp:{display_idx}/{num_displays-1}"

            # Row 1 — mode, intensity, genre, device, hint
            row1 = font.render(
                f"  [{mode_idx+1}/{len(MODES)}] {name}{bg_str}  |  intensity:{gain_str}"
                f"  |  genre:{current_genre}{disp_str}  |  🎤 {dev_name}{hint}",
                True, (90, 90, 90))
            screen.blit(row1, (6, 6))

            # Row 2 — BPM + energy bars
            y2      = row1.get_height() + 8
            bpm_lbl = font_s.render(
                f"  BPM:{bpm:5.1f}" if bpm > 0 else "  BPM: --.-", True, (70, 70, 70))
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

            bx = _bar("beat", beat,   3.0, (180, 50,  50),  bx)
            bx = _bar(" mid", mid_e,  2.0, (50,  180, 50),  bx)
            bx = _bar(" tri", treble_e, 2.0, (130, 60, 200), bx)

            # Row 3 — particle count (when applicable)
            if hasattr(vis, "_n"):
                screen.blit(
                    font_s.render(f"  particles: {vis._n}", True, (60, 60, 60)),
                    (6, y2 + 20))

        if picking:
            _draw_device_picker(screen, font, devices, pick_sel, active_dev)

        pygame.display.flip()
        clock.tick(config.FPS)
        tick += 1


if __name__ == "__main__":
    main()
