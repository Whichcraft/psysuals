"""Mycelium — psychedelic hyphae colonies with swirling spores."""
import math
import random

import numpy as np
import pygame

import config
from .base import Effect
from .utils import hsl

_MAX_SEGS = 900
_MAX_TIPS = 240
_CORE_COUNT = 5


class Mycelium(Effect):
    TRAIL_ALPHA = 8

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._hue = random.random()
        self._phase = 0.0
        self._pulse = 0.0
        self._segs: list = []
        self._tips: list = []
        self._cores: list[tuple[float, float, float]] = []
        self._rng = np.random.default_rng(config.RNG_SEED or None)
        self._build_cores()
        self._seed_tips(28)

    def _build_cores(self):
        W, H = config.WIDTH, config.HEIGHT
        cx, cy = W / 2.0, H / 2.0
        rad = min(W, H) * 0.22
        self._cores = []
        base = np.linspace(0.0, math.tau, _CORE_COUNT, endpoint=False, dtype=np.float32)
        angs = base + self._rng.uniform(-0.22, 0.22, _CORE_COUNT)
        dists = rad * self._rng.uniform(0.55, 1.15, _CORE_COUNT)
        for i, (ang, dist) in enumerate(zip(angs, dists)):
            self._cores.append((
                cx + math.cos(ang) * dist,
                cy + math.sin(ang) * dist,
                i / _CORE_COUNT * 0.45,
            ))

    def _seed_tips(self, count, core_idx=None):
        if not self._cores:
            self._build_cores()
        n = min(count, _MAX_TIPS - len(self._tips))
        if n <= 0:
            return
        if core_idx is None:
            idxs = self._rng.integers(0, len(self._cores), size=n)
        else:
            idxs = np.full(n, core_idx, dtype=np.int32)
        angs = self._rng.uniform(0.0, math.tau, n)
        radii = self._rng.uniform(4.0, min(config.WIDTH, config.HEIGHT) * 0.035, n)
        hoffs = self._rng.uniform(0.0, 0.15, n)
        for idx, ang, radius, hoff in zip(idxs, angs, radii, hoffs):
            cx, cy, h_off = self._cores[int(idx)]
            self._tips.append([
                cx + math.cos(ang) * radius,
                cy + math.sin(ang) * radius,
                ang,
                0,
                (h_off + float(hoff)) % 1.0,
                int(idx),
            ])

    def draw(self, surf, waveform, fft, beat, tick):
        W, H = config.WIDTH, config.HEIGHT
        bass = beat
        mid = config.MID_ENERGY
        high = config.TREBLE_ENERGY

        if not self._cores:
            self._build_cores()

        self._hue = (self._hue + 0.003 + mid * 0.002) % 1.0
        self._phase += 0.010 + mid * 0.012 + high * 0.006
        self._pulse = max(0.0, self._pulse - 0.03)

        if bass > 0.65 and len(self._tips) < _MAX_TIPS:
            self._pulse = 1.0
            for _ in range(1 + int(bass * 2.5)):
                self._seed_tips(int(5 + bass * 6), int(self._rng.integers(0, len(self._cores))))

        speed = 6.5 + bass * 18.0 + mid * 5.0
        spread = 0.20 + mid * 0.30 + high * 0.10
        branch_p = 0.07 + mid * 0.10 + high * 0.08
        seg_life = 90 + int(bass * 55 + high * 20)

        next_tips: list = []
        tips = self._tips
        tip_count = len(tips)
        if tip_count:
            gauss = self._rng.normal(0.0, spread * 0.16, tip_count)
            len_mul = self._rng.uniform(0.72, 1.22, tip_count)
            branch_roll = self._rng.random(tip_count)
            branch_sign = self._rng.integers(0, 2, tip_count) * 2 - 1
            branch_angle = self._rng.uniform(0.35, 0.95 + spread, tip_count)
            branch_core = self._rng.integers(0, len(self._cores), tip_count)
            seg_jitter = self._rng.integers(-16, 56, tip_count)
            for idx, (tx, ty, ta, depth, h_off, core_idx) in enumerate(tips):
                if depth >= 18:
                    continue
                cx, cy, _ = self._cores[core_idx]
                swirl = math.atan2(ty - cy, tx - cx) + math.pi * 0.5
                field = (
                    math.sin(tx * 0.013 + self._phase + core_idx * 0.7) * 0.55
                    + math.cos(ty * 0.011 - self._phase * 1.2 + depth * 0.25) * 0.35
                )
                ta2 = ta + (swirl + field - ta) * 0.22 + float(gauss[idx])
                length = max(2.5, speed * (1.0 - depth * 0.030) * float(len_mul[idx]))
                ex = (tx + math.cos(ta2) * length) % W
                ey = (ty + math.sin(ta2) * length) % H
                if len(self._segs) < _MAX_SEGS:
                    self._segs.append([tx, ty, ex, ey, 0, seg_life + int(seg_jitter[idx]), depth, h_off])
                if len(next_tips) < _MAX_TIPS:
                    next_tips.append([ex, ey, ta2, depth + 1, h_off, core_idx])
                if branch_roll[idx] < branch_p and depth < 13 and len(next_tips) < _MAX_TIPS:
                    b_ang = ta2 + float(branch_sign[idx]) * float(branch_angle[idx])
                    b_core = core_idx if self._rng.random() > 0.18 else int(branch_core[idx])
                    next_tips.append([ex, ey, b_ang, depth + 1, (h_off + 0.10) % 1.0, b_core])

        self._tips = next_tips[:_MAX_TIPS]

        if not self._tips:
            self._build_cores()
            self._seed_tips(28)

        self._segs = [s for s in self._segs if s[4] < s[5]]
        for s in self._segs:
            s[4] += 1

        for i, (cx, cy, h_off) in enumerate(self._cores):
            phase = self._phase * (0.7 + i * 0.08)
            wobble = 10.0 + math.sin(phase) * 8.0
            hue = (self._hue + h_off + math.sin(phase * 0.6) * 0.05) % 1.0
            glow = 0.06 + self._pulse * 0.12 + bass * 0.05
            pygame.draw.circle(surf, hsl(hue, l=glow * 0.35), (int(cx), int(cy)), int(22 + wobble))
            pygame.draw.circle(surf, hsl(hue, l=glow), (int(cx), int(cy)), int(7 + bass * 8))

        for x1, y1, x2, y2, age, max_age, depth, h_off in self._segs:
            fade = max(0.0, 1.0 - age / max_age)
            hue = (self._hue + h_off + depth * 0.015) % 1.0
            bright = (0.22 + bass * 0.10 + high * 0.08 + self._pulse * 0.14) * fade
            glow_w = max(1, 5 - depth // 4)
            core_w = max(1, 3 - depth // 6)
            p1 = (int(x1), int(y1))
            p2 = (int(x2), int(y2))
            pygame.draw.line(surf, hsl(hue, l=bright * 0.28), p1, p2, glow_w + 2)
            pygame.draw.line(surf, hsl(hue, l=bright), p1, p2, core_w)
            if depth > 5 and age < max_age * 0.25 and (depth + age) % 5 == 0:
                pygame.draw.circle(surf, hsl(hue, l=bright * 0.85), p2, max(1, 3 - depth // 8))
