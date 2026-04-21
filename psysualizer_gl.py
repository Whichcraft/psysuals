#!/usr/bin/env python3
"""
psysualizer_gl.py — moderngl proof-of-concept entry point.

Runs the Plasma effect as a GLSL fragment shader via a pygame OpenGL window.
Same audio pipeline as psysualizer.py; same config.py for dimensions/FPS.

Usage:
    python psysualizer_gl.py

Controls:
    Q / ESC     Quit
    F           Toggle fullscreen

Dependencies (beyond the normal requirements.txt):
    pip install -r requirements-gl.txt
"""

__version__ = "0.1.0-gl"

import threading
from collections import deque

import numpy as np

try:
    import pygame
    import moderngl          # noqa: F401 — import check before we go further
    import sounddevice as sd
except ImportError as e:
    raise SystemExit(f"Missing dependency: {e}\n  pip install -r requirements-gl.txt")

import config
from gl_renderer import GLRenderer
from effects.plasma_gl import PlasmaGL

# ── Audio pipeline ────────────────────────────────────────────────────────────
# Mirrors psysualizer.py's _audio_cb / get_audio() without the BPM/genre work.

_lock      = threading.Lock()
_waveform  = np.zeros(config.BLOCK_SIZE)
_fft       = np.zeros(config.BLOCK_SIZE // 2)
_beat      = 0.0
_window    = np.blackman(config.BLOCK_SIZE)
_prev_spec = np.zeros(config.BLOCK_SIZE // 2)
_flux_avg  = 1e-6


def _audio_cb(indata, frames, time, status):
    global _waveform, _fft, _beat, _prev_spec, _flux_avg
    mono = indata[:, 0]
    spec = np.abs(np.fft.rfft(mono * _window))[: config.BLOCK_SIZE // 2]
    np.log1p(spec, out=spec)
    spec /= 10.0
    with _lock:
        _waveform    = mono.copy()
        _fft        *= 0.5
        _fft        += spec * 0.5
        flux         = float(np.mean(np.maximum(0.0, spec[:20] - _prev_spec[:20])))
        _flux_avg    = _flux_avg * 0.95 + flux * 0.05
        _beat        = flux / (_flux_avg + 1e-6)
        _prev_spec[:] = spec


def _get_audio() -> tuple:
    with _lock:
        return _waveform.copy(), _fft.copy(), _beat


# ── Window helpers ────────────────────────────────────────────────────────────

def _open_window(fullscreen: bool) -> pygame.Surface:
    flags = pygame.OPENGL | pygame.DOUBLEBUF
    if fullscreen:
        flags |= pygame.FULLSCREEN
    return pygame.display.set_mode((config.WIDTH, config.HEIGHT), flags)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    pygame.init()

    fullscreen = True
    screen     = _open_window(fullscreen)
    config.WIDTH, config.HEIGHT = screen.get_size()
    pygame.display.set_caption(f"psysuals GL v{__version__}")

    # Create moderngl context bound to pygame's OpenGL window
    renderer = GLRenderer(config.WIDTH, config.HEIGHT)
    effect   = PlasmaGL(renderer)
    clock    = pygame.time.Clock()
    tick     = 0

    stream = sd.InputStream(
        samplerate=config.SAMPLE_RATE,
        blocksize=config.BLOCK_SIZE,
        channels=config.CHANNELS,
        callback=_audio_cb,
    )
    stream.start()

    try:
        while True:
            # ── Events ───────────────────────────────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        return
                    elif event.key == pygame.K_f:
                        fullscreen = not fullscreen
                        screen = _open_window(fullscreen)
                        config.WIDTH, config.HEIGHT = screen.get_size()
                        # Recreate GL context and effect after window change
                        renderer = GLRenderer(config.WIDTH, config.HEIGHT)
                        effect   = PlasmaGL(renderer)

            # ── Render ───────────────────────────────────────────────────────
            waveform, fft, beat = _get_audio()
            config.EFFECT_GAIN  = config.DEFAULT_EFFECT_GAIN

            effect.draw(None, waveform, fft, beat, tick)

            pygame.display.flip()
            clock.tick(config.FPS)
            tick += 1

            if tick % 60 == 0:
                pygame.display.set_caption(
                    f"psysuals GL v{__version__}  "
                    f"[{clock.get_fps():.0f} fps  |  GL]"
                )

    finally:
        stream.stop()
        stream.close()
        pygame.quit()


if __name__ == "__main__":
    main()
