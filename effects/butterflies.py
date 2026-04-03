"""Butterflies — up to three pairs dancing to the music.

Each pair: a solo butterfly flutters in first; its partner joins after
10–30 s and orbits it lovingly.  After a random lifetime the pair wanders
off-screen and vanishes.  New pairs can re-enter from the edges.
Wing flapping syncs when partners are close; sparkles on the beat.
"""
import math
import random

import numpy as np
import pygame

import config
from .utils import hsl


# ── Wing geometry ─────────────────────────────────────────────────────────────

def _wing_poly(x, y, heading, side, upper, flap, scale):
    """Four-point polygon for one wing.
    side: +1 / -1  (which perpendicular direction)
    upper: +1 front/larger wing, -1 rear/smaller wing
    flap: 0..1 (0 = closed, 1 = fully spread)
    """
    ca, sa = math.cos(heading), math.sin(heading)
    off  = 5.0 * scale * upper
    ax   = x + ca * off
    ay   = y + sa * off
    ws   = scale * (22 if upper == 1 else 13)
    spread  = (0.22 + flap * 0.68) * math.pi / 2
    w_ang   = heading + side * spread + upper * 0.10
    tip_x   = ax + math.cos(w_ang) * ws
    tip_y   = ay + math.sin(w_ang) * ws
    fe_ang  = w_ang - side * math.pi * 0.28
    fe_x    = ax + math.cos(fe_ang) * ws * 0.58
    fe_y    = ay + math.sin(fe_ang) * ws * 0.58
    re_ang  = w_ang + side * math.pi * 0.32
    re_x    = ax + math.cos(re_ang) * ws * 0.52
    re_y    = ay + math.sin(re_ang) * ws * 0.52
    return [(int(ax), int(ay)), (int(fe_x), int(fe_y)),
            (int(tip_x), int(tip_y)), (int(re_x), int(re_y))]


# ── Single butterfly ──────────────────────────────────────────────────────────

class _Butterfly:
    def __init__(self, x, y, hue, scale=4.0):
        self.x           = float(x)
        self.y           = float(y)
        self.heading     = random.uniform(0, math.tau)
        self.wing_phase  = random.uniform(0, math.tau)
        self.hue         = hue
        self.scale       = scale
        self._wander_des = self.heading
        self._wander_cd  = 0
        # Departure: when set, butterfly flies toward this point then off-screen
        self._depart_ang = None

    @property
    def off_screen(self):
        m = 80 * self.scale
        return (self.x < -m or self.x > config.WIDTH  + m or
                self.y < -m or self.y > config.HEIGHT + m)

    def start_depart(self):
        """Pick an off-screen heading and start leaving."""
        if self._depart_ang is None:
            self._depart_ang = random.uniform(0, math.tau)

    def update(self, bass, beat, t, orbit_pos=None, orbit_angle=0.0, orbit_r=180.0):
        self.wing_phase += 0.09 + bass * 0.16 + beat * 0.06

        if self._depart_ang is not None:
            # Fly off-screen
            self.heading += (self._depart_ang - self.heading + math.pi) % math.tau - math.pi
            spd = (2.5 + bass * 0.5) * self.scale
            self.x += math.cos(self.heading) * spd
            self.y += math.sin(self.heading) * spd
            return

        if orbit_pos is not None:
            gx = orbit_pos[0] + math.cos(orbit_angle) * orbit_r
            gy = orbit_pos[1] + math.sin(orbit_angle) * orbit_r
            desired = math.atan2(gy - self.y, gx - self.x)
        else:
            self._wander_cd -= 1
            if self._wander_cd <= 0:
                self._wander_des = (self.heading
                                    + random.uniform(-math.pi * 0.6, math.pi * 0.6))
                self._wander_cd = random.randint(60, 180)
            desired = self._wander_des

        # Boundary avoidance
        m = int(110 * self.scale)
        if   self.x < m:                      desired = 0.0
        elif self.x > config.WIDTH  - m:      desired = math.pi
        if   self.y < m:                      desired = math.pi * 0.5
        elif self.y > config.HEIGHT - m:      desired = -math.pi * 0.5

        diff = (desired - self.heading + math.pi) % math.tau - math.pi
        self.heading += max(-0.10, min(0.10, diff * 0.14))

        spd = (1.5 + bass * 0.8 + beat * 0.4) * self.scale
        self.x += math.cos(self.heading) * spd
        self.y += math.sin(self.heading) * spd

        cl = int(28 * self.scale)
        self.x = max(float(cl), min(float(config.WIDTH  - cl), self.x))
        self.y = max(float(cl), min(float(config.HEIGHT - cl), self.y))

    def draw(self, surf, outline_col=None):
        flap     = math.sin(self.wing_phase) * 0.5 + 0.5
        body_col = hsl(self.hue, l=0.28)
        wc1      = hsl(self.hue, l=0.58)
        wc2      = hsl((self.hue + 0.10) % 1.0, l=0.46)
        oc       = outline_col or body_col

        for upper in (-1, 1):
            col = wc1 if upper == 1 else wc2
            for side in (-1, 1):
                pts = _wing_poly(self.x, self.y, self.heading,
                                 side, upper, flap, self.scale)
                pygame.draw.polygon(surf, col, pts)
                pygame.draw.polygon(surf, oc,  pts, 1)

        ca, sa = math.cos(self.heading), math.sin(self.heading)
        bl = int(10 * self.scale)
        hx, hy = int(self.x + ca * bl), int(self.y + sa * bl)
        tx, ty = int(self.x - ca * bl), int(self.y - sa * bl)
        lw = max(2, int(3 * self.scale))
        pygame.draw.line(surf, body_col, (hx, hy), (tx, ty), lw)
        pygame.draw.circle(surf, hsl(self.hue, l=0.22), (hx, hy),
                           max(2, int(3 * self.scale)))

        # Antennae
        for s in (-1, 1):
            a_ang = self.heading + s * 0.38
            aex = int(hx + math.cos(a_ang) * 9 * self.scale)
            aey = int(hy + math.sin(a_ang) * 9 * self.scale)
            pygame.draw.line(surf, body_col, (hx, hy), (aex, aey), 1)
            pygame.draw.circle(surf,
                               hsl((self.hue + 0.15) % 1.0, l=0.70),
                               (aex, aey), max(1, int(2 * self.scale)))


# ── Pair ──────────────────────────────────────────────────────────────────────

def _edge_spawn():
    """Return a position just off one screen edge."""
    m = 60
    edge = random.choice("LRTB")
    if edge == "L":  return float(m), random.uniform(m, config.HEIGHT - m)
    if edge == "R":  return float(config.WIDTH - m), random.uniform(m, config.HEIGHT - m)
    if edge == "T":  return random.uniform(m, config.WIDTH - m), float(m)
    return random.uniform(m, config.WIDTH - m), float(config.HEIGHT - m)


class _Pair:
    """One loving pair of butterflies with its own lifecycle."""

    def __init__(self, hue, spawn_delay=0):
        self.hue          = hue
        self._spawn_delay = spawn_delay      # ticks until solo butterfly appears
        self._join_delay  = random.randint(600, 1800)  # ticks after solo until love arrives
        self._lifetime    = random.randint(2400, 5400)  # total pair lifespan
        self._age         = -spawn_delay
        self._orbit_ang   = 0.0
        self._orbit_r     = 260.0
        self.solo         = None
        self.love         = None
        self._departing   = False

    @property
    def dead(self):
        """True once both butterflies are off-screen after departing."""
        if not self._departing:
            return False
        b1_gone = self.solo is None or self.solo.off_screen
        b2_gone = self.love is None or self.love.off_screen
        return b1_gone and b2_gone

    def update(self, bass, beat, global_hue, t):
        self._age += 1

        # Spawn solo
        if self.solo is None and self._age >= 0:
            x, y = _edge_spawn()
            self.solo = _Butterfly(x, y, hue=global_hue, scale=4.0)

        if self.solo is None:
            return

        # Hue tracking
        self.solo.hue = global_hue
        if self.love:
            self.love.hue = (global_hue + 0.50) % 1.0

        # Spawn love butterfly
        if self.love is None and self._age >= self._join_delay:
            x, y = _edge_spawn()
            self.love = _Butterfly(x, y,
                                   hue=(global_hue + 0.50) % 1.0,
                                   scale=3.8)

        # Start departure when lifetime exceeded
        if self._age >= self._lifetime and not self._departing:
            self._departing = True
            self.solo.start_depart()
            if self.love:
                self.love.start_depart()

        # Orbit angle
        self._orbit_ang += 0.007 + beat * 0.012
        if self._orbit_r > 160:
            self._orbit_r -= 0.04

        # Update
        self.solo.update(bass, beat, t)
        if self.love:
            self.love.update(bass, beat, t,
                             orbit_pos=(self.solo.x, self.solo.y),
                             orbit_angle=self._orbit_ang,
                             orbit_r=self._orbit_r)

            # Wing sync when close
            dist = math.hypot(self.love.x - self.solo.x,
                              self.love.y - self.solo.y)
            if dist < 130 * 4:
                sync = 1.0 - dist / (130 * 4)
                diff = self.love.wing_phase - self.solo.wing_phase
                self.love.wing_phase -= diff * sync * 0.12

    def draw(self, surf, beat, global_hue):
        if self.solo is None:
            return

        # Sparkles when close together and on beat
        if self.love and beat > 0.8 and not self._departing:
            dist = math.hypot(self.love.x - self.solo.x,
                              self.love.y - self.solo.y)
            if dist < 300:
                mx = (self.solo.x + self.love.x) / 2
                my = (self.solo.y + self.love.y) / 2
                for _ in range(4):
                    sx = int(mx + random.gauss(0, 25))
                    sy = int(my + random.gauss(0, 25))
                    pygame.draw.circle(surf,
                                       hsl((global_hue + 0.12) % 1.0, l=0.80),
                                       (sx, sy), random.randint(2, 5))

        oc1 = hsl((global_hue + 0.05) % 1.0, l=0.20)
        oc2 = hsl((global_hue + 0.55) % 1.0, l=0.20)
        self.solo.draw(surf, outline_col=oc1)
        if self.love:
            self.love.draw(surf, outline_col=oc2)


# ── Main effect ───────────────────────────────────────────────────────────────

class Butterflies:
    """Three pairs of butterflies.  Each pair has its own lifecycle:
    solo → partner joins → they orbit in love → wander off-screen → new pair."""

    TRAIL_ALPHA = 22
    MAX_PAIRS   = 3

    def __init__(self):
        self._tick       = 0
        self._global_hue = random.random()
        # Stagger pair spawns
        self._pairs: list[_Pair] = []
        offsets = [0,
                   random.randint(300, 700),
                   random.randint(800, 1400)]
        for i, off in enumerate(offsets):
            hue = (self._global_hue + i / self.MAX_PAIRS) % 1.0
            self._pairs.append(_Pair(hue, spawn_delay=off))

    def draw(self, surf, waveform, fft, beat, tick):
        self._tick       += 1
        self._global_hue  = (self._global_hue + 0.0014) % 1.0
        bass = float(np.mean(fft[:6]))

        # Remove dead pairs and spawn replacements
        self._pairs = [p for p in self._pairs if not p.dead]
        while len(self._pairs) < self.MAX_PAIRS:
            hue = (self._global_hue + random.random() * 0.5) % 1.0
            self._pairs.append(_Pair(hue, spawn_delay=random.randint(60, 200)))

        for i, pair in enumerate(self._pairs):
            gh = (self._global_hue + i / self.MAX_PAIRS) % 1.0
            pair.update(bass, beat, gh, self._tick)
            pair.draw(surf, beat, gh)
