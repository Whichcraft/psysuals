"""Vortex — pixel feedback wormhole tunnel with fireworks.

Each frame the previous frame is zoom-rotated and multiplied dark, building
an infinite falling psychedelic tunnel.  Firework rockets launch from the
bottom, arc upward under gravity, and explode into glowing embers at the
apex.  Beat fires extra rockets and cranks the zoom/rotation speed.
The feedback loop swallows all trails into the wormhole.
"""
import math
import random

import numpy as np
import pygame

import config
from .utils import hsl


_GRAV = 0.13    # pixels/frame² downward
_DRAG = 0.991   # velocity multiplier per frame


from .base import Effect

class Vortex(Effect):
    TRAIL_ALPHA = 0   # we manage the surface

    _BASE_ZOOM       = 1.0038
    _BASE_ROT        = 0.42
    _BEAT_ZOOM       = 1.015
    _BEAT_ROT        = 2.4
    _BEAT_FRAMES     = 50
    # Auto-launch interval at gain=1.0.  Scales linearly with gain so that
    # higher intensity → longer interval (fewer rockets) and lower → shorter.
    # Formula: interval = _BASE_INTERVAL * gain  (clamped 20..200)
    _BASE_INTERVAL   = 40   # frames between auto-launches at gain 1.0

    def __init__(self):
        W, H = config.WIDTH, config.HEIGHT
        self._trail   = pygame.Surface((W, H))
        self._trail.fill((0, 0, 0))
        self._hue     = random.random()
        self._beat_t  = 0
        self._rockets = []   # [x, y, vx, vy, hue, trail_pts]
        self._embers  = []   # [x, y, vx, vy, hue, radius, life, max_life]
        self._auto_t  = random.randint(0, 40)   # stagger first launch

    # ── helpers ───────────────────────────────────────────────────────────────

    def _launch(self):
        W, H = config.WIDTH, config.HEIGHT
        x  = random.uniform(W * 0.10, W * 0.90)
        vy = random.uniform(-15, -10)
        vx = random.uniform(-2.0, 2.0)
        h  = (self._hue + random.uniform(-0.25, 0.25)) % 1.0
        self._rockets.append([float(x), float(H), vx, vy, h, []])

    def _explode(self, x, y, hue):
        n = random.randint(80, 120)
        for _ in range(n):
            ang = random.uniform(0, math.tau)
            spd = random.gauss(4.5, 1.8)
            vx  = math.cos(ang) * spd
            vy  = math.sin(ang) * spd * 0.85 - random.uniform(0, 1.5)
            life = random.randint(50, 100)
            h    = (hue + random.uniform(-0.09, 0.09)) % 1.0
            r    = random.randint(2, 5)
            self._embers.append([x, y, vx, vy, h, r, life, life])

    # ── main draw ─────────────────────────────────────────────────────────────

    def draw(self, surf, waveform, fft, beat, tick):
        W, H  = config.WIDTH, config.HEIGHT
        bass  = float(np.mean(fft[:6]))
        self._hue = (self._hue + 0.0015 + bass * 0.002) % 1.0

        # Beat: launch rockets + boost
        if beat > 0.6:
            self._beat_t = self._BEAT_FRAMES
            for _ in range(1 + int(beat * 2)):
                self._launch()

        # Auto-launch between beats — interval scales with effect gain so that
        # low gain → more rockets, high gain → fewer (beat-triggered already
        # fires more rockets when gain is high via the larger beat value).
        gain     = max(0.1, getattr(config, 'EFFECT_GAIN', 1.0))
        interval = int(max(20, min(200, self._BASE_INTERVAL * gain)))
        self._auto_t += 1
        if self._auto_t >= interval:
            self._auto_t = 0
            self._launch()

        # ── feedback: zoom + rotate trail ─────────────────────────────────────
        t = self._beat_t / self._BEAT_FRAMES if self._beat_t > 0 else 0.0
        self._beat_t = max(0, self._beat_t - 1)
        zoom    = self._BASE_ZOOM + t * (self._BEAT_ZOOM - self._BASE_ZOOM) + bass * 0.003
        rot_deg = self._BASE_ROT  + t * (self._BEAT_ROT  - self._BASE_ROT)

        rotated = pygame.transform.rotozoom(self._trail, rot_deg, zoom)
        rw, rh  = rotated.get_size()
        self._trail.fill((0, 0, 0))
        self._trail.blit(rotated, (-((rw - W) // 2), -((rh - H) // 2)))

        # Decay (~94% per frame so trails persist ~40 frames)
        self._trail.fill((240, 240, 240), special_flags=pygame.BLEND_RGB_MULT)

        # ── rockets ───────────────────────────────────────────────────────────
        live = []
        for rk in self._rockets:
            x, y, vx, vy, hue, trail = rk
            vy += _GRAV
            vx *= _DRAG
            x += vx; y += vy
            trail.append((int(x), int(y)))
            if len(trail) > 14:
                trail.pop(0)
            rk[0], rk[1], rk[2], rk[3] = x, y, vx, vy

            # Draw rocket trail
            for i, pt in enumerate(trail):
                frac = (i + 1) / len(trail)
                pygame.draw.circle(self._trail, hsl(hue, l=0.30 + frac * 0.55),
                                   pt, max(1, round(3 * frac)))

            if vy >= 0 or y < -20:          # apex reached → explode
                self._explode(x, y, hue)
            elif -20 < x < W + 20:
                live.append(rk)
        self._rockets = live

        # ── embers ────────────────────────────────────────────────────────────
        live = []
        for em in self._embers:
            x, y, vx, vy, hue, radius, life, max_life = em
            vy += _GRAV
            vx *= _DRAG
            vy *= _DRAG
            x += vx; y += vy
            em[0], em[1], em[2], em[3], em[6] = x, y, vx, vy, life - 1
            if life > 0 and -60 < x < W + 60 and y < H + 60:
                brightness = 0.32 + (life / max_life) * 0.52
                pygame.draw.circle(self._trail, hsl(hue, l=brightness),
                                   (int(x), int(y)), radius)
                live.append(em)
        self._embers = live

        surf.blit(self._trail, (0, 0))
