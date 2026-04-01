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

__version__ = "1.6.2"

import threading
from collections import deque

import numpy as np
import pygame
import sounddevice as sd

import config
from effects import MODES
from effects.utils import hsl

# ── Audio ────────────────────────────────────────────────────────────────────
_lock           = threading.Lock()
_waveform       = np.zeros(config.BLOCK_SIZE)
_smooth_fft     = np.zeros(config.BLOCK_SIZE // 2)
_beat_energy    = 0.0
_hanning_window = np.hanning(config.BLOCK_SIZE)


def _audio_cb(indata, frames, time, status):
    global _waveform, _smooth_fft, _beat_energy
    mono     = indata[:, 0]
    spectrum = np.abs(np.fft.rfft(mono * _hanning_window))[: config.BLOCK_SIZE // 2]
    np.log1p(spectrum, out=spectrum)
    spectrum /= 10.0
    with _lock:
        _waveform    = mono.copy()
        _smooth_fft *= 0.50
        _smooth_fft += spectrum * 0.50
        _beat_energy = float(_smooth_fft[:20].mean())


def get_audio():
    with _lock:
        return _waveform.copy(), _smooth_fft.copy(), _beat_energy


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

def main():
    pygame.init()
    screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT), pygame.FULLSCREEN)
    pygame.display.set_caption(f"psysuals v{__version__}")
    config.WIDTH, config.HEIGHT = screen.get_size()
    clock  = pygame.time.Clock()
    font   = pygame.font.SysFont("monospace", 16)

    devices    = _input_devices()
    active_dev = None
    stream     = sd.InputStream(
        samplerate=config.SAMPLE_RATE, blocksize=config.BLOCK_SIZE,
        channels=config.CHANNELS, device=active_dev, callback=_audio_cb)
    stream.start()

    mode_idx       = 0
    name, VisCls   = MODES[mode_idx]
    vis            = VisCls()
    fullscreen     = True
    tick           = 0
    energy_hist    = deque(maxlen=15)
    energy_sum     = 0.0
    dev_name_cache = {None: "default"}
    picking        = False
    pick_sel       = 0
    show_hud       = True
    effect_gain    = 1.0

    def make_fade(alpha=28):
        s = pygame.Surface((config.WIDTH, config.HEIGHT))
        s.set_alpha(alpha)
        s.fill((0, 0, 0))
        return s

    fade      = make_fade()
    fade_alpha = 28

    hint = ("  ←/→: prev/next mode  |  ↑/↓: effect intensity  |  1-{n}: pick mode  "
            "|  D: device  |  F: fullscreen  |  H: hide HUD  |  Q: quit").format(n=len(MODES))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stream.stop(); stream.close()
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
                        new_idx  = devices[pick_sel][0]
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
                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        stream.stop(); stream.close()
                        pygame.quit(); return
                    elif event.key in (pygame.K_SPACE, pygame.K_RIGHT):
                        mode_idx = (mode_idx + 1) % len(MODES)
                        name, VisCls = MODES[mode_idx]; vis = VisCls()
                        fade_alpha = -1
                    elif event.key == pygame.K_LEFT:
                        mode_idx = (mode_idx - 1) % len(MODES)
                        name, VisCls = MODES[mode_idx]; vis = VisCls()
                        fade_alpha = -1
                    elif event.key == pygame.K_UP:
                        effect_gain = min(2.0, round(effect_gain + 0.1, 1))
                    elif event.key == pygame.K_DOWN:
                        effect_gain = max(0.0, round(effect_gain - 0.1, 1))
                    elif event.key == pygame.K_f:
                        fullscreen = not fullscreen
                        flags  = pygame.FULLSCREEN if fullscreen else 0
                        screen = pygame.display.set_mode(
                            (config.WIDTH, config.HEIGHT), flags)
                        config.WIDTH, config.HEIGHT = screen.get_size()
                        fade = make_fade()
                        fade_alpha = -1
                        vis  = VisCls()
                    elif event.key == pygame.K_h:
                        show_hud = not show_hud
                    elif event.key == pygame.K_d:
                        devices  = _input_devices()
                        picking  = True
                        active_indices = [d[0] for d in devices]
                        pick_sel = (active_indices.index(active_dev)
                                    if active_dev in active_indices else 0)
                    else:
                        idx = event.key - pygame.K_1
                        if 0 <= idx < len(MODES):
                            mode_idx = idx
                            name, VisCls = MODES[mode_idx]; vis = VisCls()
                            fade_alpha = -1

            elif event.type == pygame.MOUSEBUTTONDOWN and not picking:
                mode_idx = (mode_idx + 1) % len(MODES)
                name, VisCls = MODES[mode_idx]; vis = VisCls()
                fade_alpha = -1

        waveform, fft, raw_beat = get_audio()
        if len(energy_hist) == energy_hist.maxlen:
            energy_sum -= energy_hist[0]
        energy_hist.append(raw_beat)
        energy_sum += raw_beat
        avg  = energy_sum / len(energy_hist) if energy_hist else 1e-6
        beat = max(0.0, min(raw_beat / (avg + 1e-6) - 1.0, 3.0))

        new_alpha = getattr(vis, 'TRAIL_ALPHA', 28)
        if new_alpha != fade_alpha:
            fade_alpha = new_alpha
            fade = make_fade(fade_alpha)
        screen.blit(fade, (0, 0))
        vis.draw(screen, waveform, fft, beat * effect_gain, tick)

        if show_hud:
            if active_dev not in dev_name_cache:
                dev_name_cache[active_dev] = sd.query_devices(active_dev)["name"]
            dev_name = dev_name_cache[active_dev]
            label = font.render(
                f"  [{mode_idx+1}/{len(MODES)}] {name}  |  intensity: {effect_gain:.1f}  |  🎤 {dev_name}{hint}",
                True, (90, 90, 90))
            screen.blit(label, (6, 6))

        if picking:
            _draw_device_picker(screen, font, devices, pick_sel, active_dev)

        pygame.display.flip()
        clock.tick(config.FPS)
        tick += 1


if __name__ == "__main__":
    main()
