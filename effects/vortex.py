"""Pixel Feedback Vortex — infinite zoom-rotate tunnel with decaying colour trails.

Each frame the previous frame is slightly zoomed and rotated, then multiplied
dark so it never saturates.  Neon sparks spawn at the centre, drift outward,
and burn through the decaying trail — creating a falling psychedelic wormhole.
Beat fires a ring of sparks and doubles zoom / rotation speed.
"""
import math
import random

import numpy as np
import pygame

import config
from .utils import hsl


class Vortex:
    TRAIL_ALPHA = 0   # we manage the surface ourselves

    _BASE_ZOOM   = 1.003
    _BASE_ROT    = 0.35    # degrees/frame
    _BEAT_ZOOM   = 1.012
    _BEAT_ROT    = 1.8
    _BEAT_FRAMES = 45

    def __init__(self):
        W, H = config.WIDTH, config.HEIGHT
        self._trail  = pygame.Surface((W, H))
        self._trail.fill((0, 0, 0))
        self._hue    = random.random()
        self._beat_t = 0
        self._sparks = []   # [x, y, vx, vy, hue, radius, life]

    def draw(self, surf, waveform, fft, beat, tick):
        W, H = config.WIDTH, config.HEIGHT
        bass      = float(np.mean(fft[:6]))
        self._hue = (self._hue + 0.0015 + bass * 0.002) % 1.0

        # Beat burst: ring of sparks + speed boost
        if beat > 0.65:
            self._beat_t = self._BEAT_FRAMES
            n = 14 + int(beat * 10)
            for i in range(n):
                ang = i * math.tau / n + random.uniform(-0.3, 0.3)
                spd = random.uniform(3.0, 6.0 + beat * 4)
                self._sparks.append([
                    W / 2, H / 2,
                    math.cos(ang) * spd, math.sin(ang) * spd,
                    (self._hue + random.uniform(-0.12, 0.12)) % 1.0,
                    random.randint(3, 7),
                    random.randint(35, 65),
                ])

        # Interpolate zoom/rotation toward beat values
        t = self._beat_t / self._BEAT_FRAMES if self._beat_t > 0 else 0.0
        self._beat_t = max(0, self._beat_t - 1)
        zoom    = self._BASE_ZOOM + t * (self._BEAT_ZOOM - self._BASE_ZOOM) + bass * 0.004
        rot_deg = self._BASE_ROT  + t * (self._BEAT_ROT  - self._BASE_ROT)

        # Feedback: zoom + rotate the trail surface, centred
        rotated = pygame.transform.rotozoom(self._trail, rot_deg, zoom)
        rw, rh  = rotated.get_size()
        self._trail.fill((0, 0, 0))
        self._trail.blit(rotated, (-((rw - W) // 2), -((rh - H) // 2)))

        # Decay: multiply RGB by ~0.94 each frame to prevent saturation
        self._trail.fill((240, 240, 240), special_flags=pygame.BLEND_RGB_MULT)

        # Continuous bass-driven sparks from centre
        n_spawn = max(1, int(bass * 5))
        for _ in range(n_spawn):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(0.4, 1.8 + bass * 2.5)
            self._sparks.append([
                W / 2 + random.gauss(0, 6),
                H / 2 + random.gauss(0, 6),
                math.cos(ang) * spd, math.sin(ang) * spd,
                (self._hue + random.uniform(-0.18, 0.18)) % 1.0,
                random.randint(2, 4),
                random.randint(20, 50),
            ])

        # Update sparks and paint onto trail
        live = []
        for s in self._sparks:
            s[0] += s[2]; s[1] += s[3]; s[6] -= 1
            x, y = int(s[0]), int(s[1])
            if s[6] > 0 and 0 <= x < W and 0 <= y < H:
                brightness = 0.50 + (s[6] / 65) * 0.40
                pygame.draw.circle(self._trail, hsl(s[4], l=brightness), (x, y), s[5])
                live.append(s)
        self._sparks = live

        surf.blit(self._trail, (0, 0))
