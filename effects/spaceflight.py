"""Spaceflight — psychedelic hyperspace trip.

· Rainbow warp streaks burst from the ship's focal point outward
· Every beat fires concentric neon rings that expand and fade
· Drifting nebula clouds breathe with the bass
· Vivid planets grow from tiny dots to enormous spheres
· Ship banks through it all with twin neon exhausts
· Global hue cycles constantly — nothing is ever the same colour twice
"""
import math
import random

import numpy as np
import pygame

import config
from .utils import hsl


# ── Ship polygon — from behind, nose pointing away ────────────────────────────
_SHIP_PTS = [
    ( 0, -64),
    (-44,  24), (-20,   8), (-14,  36),
    ( 14,  36), ( 20,   8), ( 44,  24),
]
_ENGINE_L = (-14,  36)
_ENGINE_R = ( 14,  36)


def _rotpts(pts, cx, cy, ca, sa):
    return [(int(cx + px * ca - py * sa),
             int(cy + px * sa + py * ca)) for px, py in pts]


# ── Maneuvers ─────────────────────────────────────────────────────────────────
def _jink(s):
    return (lambda t: s * math.sin(t * math.pi) * 200,
            lambda t: 0.0,
            lambda t: s * math.sin(t * math.pi) * 0.65)

def _climb(s):
    return (lambda t: 0.0,
            lambda t: s * math.sin(t * math.pi) * 150,
            lambda t: s * math.sin(t * math.pi) * 0.30)

def _barrel():
    return (lambda t: math.sin(t * math.tau) * 150,
            lambda t: math.cos(t * math.tau) * 110 - 110,
            lambda t: t * math.tau)

_MANEUVERS = [
    (160, _jink(-1)), (160, _jink(1)),
    (140, _climb(-1)), (140, _climb(1)),
    (230, _barrel()),
]


class Spaceflight:
    """Psychedelic warp tunnel with neon streaks, beat rings and nebula clouds."""

    TRAIL_ALPHA = 20
    N_STARS     = 340

    def __init__(self):
        self.hue   = random.random()
        self.t     = 0
        self.speed = 1.0

        # Ship / focal point
        self._ship_x    = float(config.WIDTH  / 2)
        self._ship_y    = float(config.HEIGHT / 2)
        self._ship_roll = 0.0
        self._focal_x   = self._ship_x
        self._focal_y   = self._ship_y
        self._man       = None
        self._man_cd    = random.randint(100, 250)

        # Stars: [angle, depth, speed_frac, own_hue]
        self._stars = [
            [random.uniform(0, math.tau),
             random.random(),
             random.uniform(0.4, 1.6),
             random.uniform(0, 1.0)]
            for _ in range(self.N_STARS)
        ]

        # Beat rings: [x, y, r, hue, age, max_age]
        self._rings: list[list] = []

        # Planets
        self.planets    = []
        self._planet_cd = random.randint(150, 350)

        # Glow surface for engine bloom
        self._gsurf = pygame.Surface((160, 160), pygame.SRCALPHA)

    # ── Factories ─────────────────────────────────────────────────────────────

    def _spawn_planet(self):
        return {
            "angle":    random.uniform(0, math.tau),
            "radial":   random.uniform(0.25, 0.82),
            "depth":    0.03,
            "dd":       random.uniform(0.0014, 0.0032),
            "base_r":   random.uniform(32, 95),
            "hue":      random.uniform(0, 1.0),
            "rings":    random.random() > 0.45,
            "ring_hue": random.uniform(0, 1.0),
        }

    # ── Drawing helpers ───────────────────────────────────────────────────────

    def _draw_planet(self, surf, p):
        max_r = math.hypot(config.WIDTH, config.HEIGHT) * 0.75
        r_d   = p["depth"] * max_r * p["radial"]
        px    = int(self._focal_x + math.cos(p["angle"]) * r_d)
        py    = int(self._focal_y + math.sin(p["angle"]) * r_d)
        r     = max(2, int(p["base_r"] * p["depth"]))
        h     = p["hue"]
        pygame.draw.circle(surf, hsl(h, l=0.18), (px, py), r)
        if r > 5:
            pygame.draw.circle(surf, hsl(h, l=0.34), (px, py), max(2, int(r * 0.80)))
            pygame.draw.circle(surf, hsl(h, l=0.52), (px, py), max(2, int(r * 0.56)))
            pygame.draw.circle(surf, hsl(h, l=0.72), (px - r//3, py - r//3), max(2, r//4))
        pygame.draw.circle(surf, hsl((h + 0.12) % 1.0, l=0.68), (px, py), r, 2)
        if p["rings"] and r > 10:
            rw = int(r * 1.85)
            rh = max(3, int(r * 0.30))
            pygame.draw.ellipse(surf, hsl(p["ring_hue"], l=0.62),
                                (px - rw, py - rh, rw * 2, rh * 2), 2)

    def _draw_ship(self, surf, x, y, heading, roll, beat):
        ang = heading + roll
        ca, sa = math.cos(ang), math.sin(ang)
        pts = _rotpts(_SHIP_PTS, x, y, ca, sa)

        # Twin neon engine blooms
        gr = max(14, int(22 + beat * 44))
        for eox, eoy in (_ENGINE_L, _ENGINE_R):
            ex = int(x + eox * ca - eoy * sa)
            ey = int(y + eox * sa + eoy * ca)
            self._gsurf.fill((0, 0, 0, 0))
            eh = (self.hue + 0.55) % 1.0
            pygame.draw.circle(self._gsurf,
                               (*hsl(eh, l=0.42), 95), (80, 80), gr)
            pygame.draw.circle(self._gsurf,
                               (*hsl(eh, l=0.95), 230), (80, 80), max(4, gr // 2))
            surf.blit(self._gsurf, (ex - 80, ey - 80))
            pygame.draw.circle(surf, hsl(eh, l=0.97), (ex, ey), max(5, gr // 3))

        # Neon hull — fill + bright outline
        pygame.draw.polygon(surf, hsl((self.hue + 0.12) % 1.0, l=0.30), pts)
        pygame.draw.polygon(surf, hsl(self.hue, l=0.82), pts, 2)

        # Heat panel between nozzles
        panel = _rotpts(
            [(_ENGINE_L[0], _ENGINE_L[1] - 5),
             (_ENGINE_R[0], _ENGINE_R[1] - 5),
             (_ENGINE_R[0], _ENGINE_R[1] + 3),
             (_ENGINE_L[0], _ENGINE_L[1] + 3)],
            x, y, ca, sa)
        pygame.draw.polygon(surf, hsl((self.hue + 0.55) % 1.0, l=0.28), panel)

    # ── Main draw ─────────────────────────────────────────────────────────────

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue = (self.hue + 0.005) % 1.0
        self.t  += 1
        bass = float(np.mean(fft[:6]))

        # Warp speed ramps with audio
        self.speed += (1.0 + bass * 3.8 + beat * 5.5 - self.speed) * 0.10

        # ── Ship maneuvers ────────────────────────────────────────────────────
        cx = config.WIDTH  / 2
        cy = config.HEIGHT / 2

        if self._man:
            self._man["t"] += 1
            tn = self._man["t"] / self._man["dur"]
            if tn >= 1.0:
                self._man       = None
                self._man_cd    = random.randint(80, 200)
                self._ship_x    = cx;  self._ship_y    = cy
                self._ship_roll = 0.0
            else:
                dxf, dyf, rf    = self._man["fns"]
                self._ship_x    = cx + dxf(tn)
                self._ship_y    = cy + dyf(tn)
                self._ship_roll = rf(tn)
        else:
            self._man_cd -= 1
            if self._man_cd <= 0:
                dur, fns = random.choice(_MANEUVERS)
                self._man = {"t": 0, "dur": dur, "fns": fns}
            self._ship_x    = cx + math.sin(self.t * 0.018) * 20
            self._ship_y    = cy + math.sin(self.t * 0.011) * 14
            self._ship_roll = math.sin(self.t * 0.018) * 0.14

        # Focal point lags the ship
        self._focal_x += (self._ship_x - self._focal_x) * 0.08
        self._focal_y += (self._ship_y - self._focal_y) * 0.08

        fx, fy = self._focal_x, self._focal_y

        # Ship heading: nose points toward focal point (flight axis vanishing point).
        # When nearly centred fall back to straight-ahead (up = −π/2).
        dx = fx - self._ship_x
        dy = fy - self._ship_y
        dist = math.hypot(dx, dy)
        ship_heading = math.atan2(dy, dx) if dist > 6 else -math.pi / 2

        # ── Beat rings ────────────────────────────────────────────────────────
        if beat > 0.5:
            n_new = 1 + int(beat * 1.5)
            for _ in range(n_new):
                h_r = (self.hue + random.uniform(0, 0.6)) % 1.0
                self._rings.append([fx, fy, 8.0, h_r, 0, int(30 + beat * 18)])

        alive = []
        for ring in self._rings:
            ring[2] += 5.0 + self.speed * 1.8   # expand radius
            ring[4] += 1                          # age
            frac = ring[4] / ring[5]
            if frac < 1.0:
                alive.append(ring)
                brt = 0.85 - frac * 0.55
                lw  = max(1, int(3 - frac * 2) + 1)
                r_i = int(ring[2])
                if r_i > 0:
                    pygame.draw.circle(surf, hsl(ring[3], l=brt),
                                       (int(ring[0]), int(ring[1])), r_i, lw)
        self._rings = alive[:40]

        # ── Rainbow warp streaks ──────────────────────────────────────────────
        max_r = math.hypot(config.WIDTH, config.HEIGHT) * 0.80
        for st in self._stars:
            old_d  = st[1]
            st[1] += 0.0024 * st[2] * self.speed

            ox = fx + math.cos(st[0]) * old_d * max_r
            oy = fy + math.sin(st[0]) * old_d * max_r
            nx = fx + math.cos(st[0]) * st[1]  * max_r
            ny = fy + math.sin(st[0]) * st[1]  * max_r

            # Hue shifts through spectrum as star approaches
            h   = (st[3] + st[1] * 0.45 + self.hue) % 1.0
            brt = min(0.98, 0.28 + st[1] * 0.68 + beat * 0.12)
            lw  = max(1, int(st[1] * 5.0 + beat * 3.0))
            pygame.draw.line(surf, hsl(h, l=brt),
                             (int(ox), int(oy)), (int(nx), int(ny)), lw)

            if st[1] >= 1.0:
                st[0] = random.uniform(0, math.tau)
                st[1] = random.uniform(0.0, 0.06)
                st[2] = random.uniform(0.4, 1.6)
                st[3] = random.uniform(0, 1.0)

        # ── Planets ───────────────────────────────────────────────────────────
        self._planet_cd -= 1
        if self._planet_cd <= 0 and len(self.planets) < 4:
            self.planets.append(self._spawn_planet())
            self._planet_cd = random.randint(260, 600)

        alive_p = []
        for p in self.planets:
            p["depth"] += p["dd"] * self.speed * 0.28
            if p["depth"] < 1.15:
                alive_p.append(p)
                self._draw_planet(surf, p)
        self.planets = alive_p

        # ── Ship ──────────────────────────────────────────────────────────────
        self._draw_ship(surf, self._ship_x, self._ship_y,
                        ship_heading, self._ship_roll, beat)
