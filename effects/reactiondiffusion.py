"""Reaction-Diffusion — Gray-Scott model.

Two virtual chemicals (A and B) diffuse and react across a grid.
Gray-Scott equations produce coral, worm-maze, and spot patterns that
morph continuously as audio shifts the feed/kill parameters.
Beat injects chemical B at a random point, seeding a new growth front.
"""
import math
import random

import numpy as np
import pygame

import config


_GRID_W = 192
_GRID_H = 108
_STEPS  = 4        # simulation steps per rendered frame
_Da     = 1.0      # diffusion rate of A
_Db     = 0.5      # diffusion rate of B
_DT     = 1.0      # time step


def _laplacian(Z):
    return (np.roll(Z,  1, 0) + np.roll(Z, -1, 0) +
            np.roll(Z,  1, 1) + np.roll(Z, -1, 1) - 4.0 * Z)


def _hsl_array(h, s, l):
    """Vectorised HSL → uint8 R, G, B arrays (same shape as inputs)."""
    C  = (1.0 - np.abs(2.0 * l - 1.0)) * s
    H6 = h * 6.0
    X  = C * (1.0 - np.abs(H6 % 2.0 - 1.0))
    m  = l - C * 0.5
    hi = H6.astype(np.int32) % 6
    r = np.select([hi==0, hi==1, hi==2, hi==3, hi==4],
                  [C, X, np.zeros_like(C), np.zeros_like(C), X], default=C) + m
    g = np.select([hi==0, hi==1, hi==2, hi==3, hi==4],
                  [X, C, C, X, np.zeros_like(C)], default=np.zeros_like(C)) + m
    b = np.select([hi==0, hi==1, hi==2, hi==3, hi==4],
                  [np.zeros_like(C), np.zeros_like(C), X, C, C], default=X) + m
    u = np.uint8
    return ((r * 255).clip(0, 255).astype(u),
            (g * 255).clip(0, 255).astype(u),
            (b * 255).clip(0, 255).astype(u))


class ReactionDiffusion:
    TRAIL_ALPHA = 0   # we paint directly

    # Gray-Scott params: "coral / worm-maze" territory
    _F_BASE = 0.055
    _K_BASE = 0.062

    def __init__(self):
        self._A    = np.ones( (_GRID_H, _GRID_W), dtype=np.float32)
        self._B    = np.zeros((_GRID_H, _GRID_W), dtype=np.float32)
        self._hue  = random.random()
        self._F    = self._F_BASE
        self._K    = self._K_BASE
        self._surf = pygame.Surface((_GRID_W, _GRID_H))
        for _ in range(12):
            self._inject(random.randint(4, _GRID_W - 4),
                         random.randint(4, _GRID_H - 4),
                         r=random.randint(3, 7))

    def _inject(self, cx, cy, r=5):
        y0, y1 = max(0, cy - r), min(_GRID_H, cy + r)
        x0, x1 = max(0, cx - r), min(_GRID_W, cx + r)
        self._B[y0:y1, x0:x1] = 1.0
        self._A[y0:y1, x0:x1] = 0.0

    def _step(self):
        A, B   = self._A, self._B
        AB2    = A * B * B
        self._A = np.clip(A + _DT * (_Da * _laplacian(A) - AB2
                                      + self._F * (1.0 - A)), 0.0, 1.0)
        self._B = np.clip(B + _DT * (_Db * _laplacian(B) + AB2
                                      - (self._F + self._K) * B), 0.0, 1.0)

    def draw(self, surf, waveform, fft, beat, tick):
        bass      = float(np.mean(fft[:6]))
        self._hue = (self._hue + 0.0015 + bass * 0.003) % 1.0

        # Slowly drift F and K through parameter space
        self._F = self._F_BASE + math.sin(tick * 0.0008) * 0.010 + bass * 0.005
        self._K = self._K_BASE + math.cos(tick * 0.0011) * 0.005

        # Beat: inject a pulse at a random location
        if beat > 0.7:
            cx = random.randint(8, _GRID_W - 8)
            cy = random.randint(8, _GRID_H - 8)
            self._inject(cx, cy, r=random.randint(4, 10))

        # Re-seed if simulation dies out
        if self._B.max() < 0.01:
            for _ in range(8):
                self._inject(random.randint(4, _GRID_W - 4),
                             random.randint(4, _GRID_H - 4),
                             r=random.randint(3, 7))

        for _ in range(_STEPS):
            self._step()

        # Map B concentration → vivid colour (B peaks around 0.25; scale to 0-1)
        b_norm = np.clip(self._B * 4.0, 0.0, 1.0)
        h_arr  = (self._hue + b_norm * 0.45) % 1.0
        s_arr  = np.full_like(b_norm, 0.9)
        l_arr  = b_norm * 0.65 + 0.04        # dark background, bright structures

        r_arr, g_arr, b_arr = _hsl_array(h_arr, s_arr, l_arr)

        # Build (W, H, 3) for surfarray.blit_array
        rgb = np.stack([r_arr, g_arr, b_arr], axis=2)         # (H, W, 3)
        pygame.surfarray.blit_array(self._surf, rgb.transpose(1, 0, 2))
        surf.blit(pygame.transform.scale(self._surf,
                                         (config.WIDTH, config.HEIGHT)), (0, 0))
