"""Clifford — 3D-shaded density-accumulated strange attractor."""
import math
import random

import numpy as np
import pygame
import pygame.surfarray as surfarray

import config
from .base import Effect


class Clifford(Effect):
    TRAIL_ALPHA = 0
    RES_DIV     = 2
    _FADE_ALPHA = 18

    _N = 60_000
    _PRESETS = [
        (-1.40, 1.60, 1.00, 0.70),
        (-1.70, 1.80, -1.90, -0.40),
        (1.30, -1.70, 1.80, 1.30),
        (-1.20, 1.90, -0.90, 1.70),
        (1.60, 1.10, -1.50, 0.90),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._trail = pygame.Surface((1, 1))
        self._frame_surf = pygame.Surface((1, 1))
        self._scaled = pygame.Surface((1, 1))
        self._fade = pygame.Surface((1, 1), pygame.SRCALPHA)
        self._hue = random.random()
        self._a, self._b = np.float32(-1.4), np.float32(1.6)
        self._c, self._d = np.float32(1.0),  np.float32(0.7)
        self._ta = self._a; self._tb = self._b
        self._tc = self._c; self._td = self._d
        self._xmin = -2.0
        self._xmax = 2.0
        self._ymin = -2.0
        self._ymax = 2.0
        self._beat_prev = 0.0
        self._reset_state()

    def _reset_state(self):
        W, H, RD = self._render_size()
        self._W, self._H = W, H
        self._trail = pygame.Surface((W, H))
        self._trail.fill((0, 0, 0))
        self._frame_surf = pygame.Surface((W, H))
        self._frame_surf.fill((0, 0, 0))
        self._fade = pygame.Surface((W, H), pygame.SRCALPHA)
        self._fade.fill((0, 0, 0, self._FADE_ALPHA))
        self._scaled = pygame.Surface((config.WIDTH, config.HEIGHT))
        
        self._n = self._N
        if getattr(config, "LOW_SPEC", False):
            self._n //= 2
            
        self._xs = np.random.uniform(-1.6, 1.6, self._n).astype(np.float32)
        self._ys = np.random.uniform(-1.6, 1.6, self._n).astype(np.float32)
        self._xmin, self._xmax = -2.0, 2.0
        self._ymin, self._ymax = -2.0, 2.0
        self._new_params(force=True)

    def _new_params(self, force=False):
        base = random.choice(self._PRESETS)
        jitter = 0.0 if force else 0.18
        self._ta = np.float32(base[0] + random.uniform(-jitter, jitter))
        self._tb = np.float32(base[1] + random.uniform(-jitter, jitter))
        self._tc = np.float32(base[2] + random.uniform(-jitter, jitter))
        self._td = np.float32(base[3] + random.uniform(-jitter, jitter))

    def draw(self, surf, waveform, fft, beat, tick):
        W, H, RD = self._render_size()
        bass = beat
        mid  = config.MID_ENERGY
        high = config.TREBLE_ENERGY

        if self._trail.get_width() != W or self._trail.get_height() != H:
            self._reset_state()
            W, H = self._W, self._H
        if self._scaled.get_width() != config.WIDTH or self._scaled.get_height() != config.HEIGHT:
            self._scaled = pygame.Surface((config.WIDTH, config.HEIGHT))

        self._hue = (self._hue + 0.0025 + high * 0.003) % 1.0

        if bass > 0.8 and self._beat_prev <= 0.8:
            self._new_params()
        self._beat_prev = bass

        # Smooth parameter interpolation
        spd  = 0.008 + mid * 0.012 + bass * 0.006
        self._a = np.float32(self._a + (self._ta - self._a) * spd)
        self._b = np.float32(self._b + (self._tb - self._b) * spd)
        self._c = np.float32(self._c + (self._tc - self._c) * spd)
        self._d = np.float32(self._d + (self._td - self._d) * spd)

        xs, ys = self._xs, self._ys
        all_x = []
        all_y = []
        # Multi-pass iteration to generate high point density
        for _ in range(4):
            nx = np.sin(self._a * ys) - np.cos(self._b * xs)
            ny = np.sin(self._c * xs) - np.cos(self._d * ys)
            xs = nx.astype(np.float32)
            ys = ny.astype(np.float32)
            all_x.append(xs)
            all_y.append(ys)
        self._xs, self._ys = xs, ys

        if not np.isfinite(xs).all() or not np.isfinite(ys).all():
            self._reset_state()
            return

        draw_x = np.concatenate(all_x)
        draw_y = np.concatenate(all_y)

        # Dynamic bounding frame interpolation
        x_lo, x_hi = np.percentile(draw_x, (1.0, 99.0))
        y_lo, y_hi = np.percentile(draw_y, (1.0, 99.0))
        if x_hi - x_lo < 0.10 or y_hi - y_lo < 0.10:
            self._reset_state()
            return

        self._xmin += (x_lo - self._xmin) * 0.12
        self._xmax += (x_hi - self._xmax) * 0.12
        self._ymin += (y_lo - self._ymin) * 0.12
        self._ymax += (y_hi - self._ymax) * 0.12

        x_span = max(0.01, self._xmax - self._xmin)
        y_span = max(0.01, self._ymax - self._ymin)

        # Map to pixel indexes
        ix = np.clip(((draw_x - self._xmin) / x_span * (W - 1)).astype(np.int32), 0, W - 1)
        iy = np.clip(((draw_y - self._ymin) / y_span * (H - 1)).astype(np.int32), 0, H - 1)

        # Calculate density counts using fast np.bincount
        indices = ix * H + iy
        counts = np.bincount(indices, minlength=W * H)
        density = counts.reshape((W, H)).astype(np.float32)

        # Logarithmic normalization for a gorgeous smooth nebulous look
        if density.max() > 0:
            log_density = np.log1p(density)
            norm_density = log_density / log_density.max()
        else:
            norm_density = np.zeros_like(density)

        # 3D relief shading computation
        if norm_density.max() > 0:
            dy, dx = np.gradient(norm_density)
            # Light source orbits over time
            l_ang = tick * 0.035
            lx = math.cos(l_ang)
            ly = math.sin(l_ang)
            lz = 0.58
            l_len = math.hypot(lx, ly, lz)
            lx /= l_len; ly /= l_len; lz /= l_len

            # Normal vector components in bump-map relief space
            nz = 0.09
            n_len = np.sqrt(dx*dx + dy*dy + nz*nz)
            
            # Diffuse component (N . L)
            diffuse = ((-dx) * lx + (-dy) * ly + nz * lz) / n_len
            diffuse = np.clip(diffuse, 0.0, 1.0)
            
            # Brightness scaled by density, audio transients, and 3D shading
            bright = norm_density * (0.24 + bass * 0.40 + high * 0.30) * (0.35 + 0.65 * diffuse)
        else:
            bright = np.zeros_like(norm_density)

        # Map color values across grid coordinates using cosine palette
        x_g = np.linspace(-1.0, 1.0, W, dtype=np.float32)
        y_g = np.linspace(-1.0, 1.0, H, dtype=np.float32)
        xx, yy = np.meshgrid(x_g, y_g, indexing='ij')
        
        r = np.hypot(xx, yy)
        ang = np.arctan2(yy, xx) / math.tau + 0.5
        h_arr = (self._hue + ang * 0.45 + r * 0.20) % 1.0

        r_arr = np.clip((np.sin(h_arr * math.tau) * 127 + 128) * bright * 2, 0, 255).astype(np.uint32)
        g_arr = np.clip((np.sin((h_arr + 0.333) * math.tau) * 127 + 128) * bright * 2, 0, 255).astype(np.uint32)
        b_arr = np.clip((np.sin((h_arr + 0.667) * math.tau) * 127 + 128) * bright * 2, 0, 255).astype(np.uint32)
        colors = (r_arr << 16) | (g_arr << 8) | b_arr

        # Write frame buffer
        pix = surfarray.pixels2d(self._frame_surf)
        try:
            pix[:, :] = colors
        finally:
            del pix

        # Fade and accumulate trails
        self._trail.blit(self._fade, (0, 0))
        self._trail.blit(self._frame_surf, (0, 0), special_flags=pygame.BLEND_RGB_MAX)

        pygame.transform.scale(self._trail, (config.WIDTH, config.HEIGHT), self._scaled)
        surf.blit(self._scaled, (0, 0), special_flags=pygame.BLEND_RGB_MAX)
