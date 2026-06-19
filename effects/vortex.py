"""Vortex — pixel feedback wormhole tunnel with fireworks.

Each frame the previous frame is zoom-rotated and multiplied dark, building
an infinite falling psychedelic tunnel.  Firework rockets launch from the
bottom, arc upward under gravity, and explode into glowing embers at the
apex.  Beat fires extra rockets and cranks the zoom/rotation speed.
The feedback loop swallows all trails into the wormhole.
"""
import math
import random

import pygame

import config
from .utils import hsl


_GRAV = 0.13    # pixels/frame² downward
_DRAG = 0.991   # velocity multiplier per frame


from .base import Effect

class Vortex(Effect):
    TRAIL_ALPHA = 0   # we manage the surface
    RES_DIV     = 3   # Render at 1/3 resolution for FPS boost
    _FADE_ALPHA = 20

    _BASE_ZOOM       = 1.0038
    _BASE_ROT        = 0.42
    _BEAT_ZOOM       = 1.015
    _BEAT_ROT        = 2.4
    _BEAT_FRAMES     = 50
    _HUE_BASE_STEP   = 0.0015
    _HUE_BASS_GAIN   = 0.002
    _HUE_HIGH_GAIN   = 0.001
    _ZOOM_BASS_GAIN  = 0.002
    _ZOOM_HIGH_GAIN  = 0.001
    _ROT_MID_GAIN    = 0.45
    # Auto-launch interval at gain=1.0.  Scales linearly with gain so that
    # higher intensity → longer interval (fewer rockets) and lower → shorter.
    # Formula: interval = _BASE_INTERVAL * gain  (clamped 20..200)
    _BASE_INTERVAL   = 40   # frames between auto-launches at gain 1.0
    _AUTO_INTERVAL_MIN = 30
    _AUTO_INTERVAL_MAX = 200
    _AUTO_START_STAGGER = (0, 40)
    _LAUNCH_X_RANGE   = (0.10, 0.90)
    _LAUNCH_VY_RANGE  = (-15.0, -10.0)
    _LAUNCH_VX_RANGE  = (-2.0, 2.0)
    _LAUNCH_HUE_JITTER = 0.25
    _EXPLODE_EMBERS   = (80, 120)
    _EXPLODE_TREBLE_COUNT_GAIN = 1.5
    _EXPLODE_SPEED_MEAN = 4.5
    _EXPLODE_SPEED_STD  = 1.8
    _EXPLODE_TREBLE_SPEED_GAIN = 1.2
    _EXPLODE_VERTICAL_DAMP = 0.85
    _EXPLODE_UPLIFT_RANGE = (0.0, 1.5)
    _EXPLODE_LIFE = (50, 100)
    _EXPLODE_HUE_JITTER = 0.09
    _EXPLODE_RADIUS_BASE = 2
    _EXPLODE_RADIUS_RAND = 3
    _ROCKET_TRAIL_LEN = 8
    _ROCKET_TRAIL_SKIP = 2
    _ROCKET_TRAIL_LIGHT = 0.8
    _ROCKET_TRAIL_TREBLE_RADIUS_GAIN = 2.0
    _ROCKET_CULL_MARGIN = 20
    _EMBER_CULL_MARGIN = 40
    _EMBER_LIGHT_BASE = 0.4
    _EMBER_LIGHT_LIFE_GAIN = 0.5
    _EMBER_LIGHT_TREBLE_GAIN = 0.15

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        W, H = config.WIDTH // self.RES_DIV, config.HEIGHT // self.RES_DIV
        self._trail   = pygame.Surface((W, H))
        self._trail.fill((0, 0, 0))
        self._scaled = pygame.Surface((config.WIDTH, config.HEIGHT))
        self._fade = pygame.Surface((W, H), pygame.SRCALPHA)
        self._fade.fill((0, 0, 0, self._FADE_ALPHA))
        self._hue     = random.random()
        self._beat_t  = 0
        self._rockets = []   # [x, y, vx, vy, hue, trail_pts]
        self._embers  = []   # [x, y, vx, vy, hue, radius, life, max_life]
        self._auto_t  = random.randint(*self._AUTO_START_STAGGER)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _launch(self):
        W, H = config.WIDTH // self.RES_DIV, config.HEIGHT // self.RES_DIV
        x  = random.uniform(W * self._LAUNCH_X_RANGE[0], W * self._LAUNCH_X_RANGE[1])
        vy = random.uniform(self._LAUNCH_VY_RANGE[0] / self.RES_DIV, self._LAUNCH_VY_RANGE[1] / self.RES_DIV)
        vx = random.uniform(self._LAUNCH_VX_RANGE[0] / self.RES_DIV, self._LAUNCH_VX_RANGE[1] / self.RES_DIV)
        h  = (self._hue + random.uniform(-self._LAUNCH_HUE_JITTER, self._LAUNCH_HUE_JITTER)) % 1.0
        self._rockets.append([float(x), float(H), vx, vy, h, []])

    def _explode(self, x, y, hue, treble=0.0):
        # Scale ember count and velocity with treble energy
        n = int(random.randint(*self._EXPLODE_EMBERS) * (1.0 + treble * self._EXPLODE_TREBLE_COUNT_GAIN))
        for _ in range(n):
            ang = random.uniform(0, math.tau)
            spd = random.gauss(self._EXPLODE_SPEED_MEAN / self.RES_DIV,
                               self._EXPLODE_SPEED_STD / self.RES_DIV) * (1.0 + treble * self._EXPLODE_TREBLE_SPEED_GAIN)
            vx  = math.cos(ang) * spd
            vy  = math.sin(ang) * spd * self._EXPLODE_VERTICAL_DAMP - random.uniform(
                self._EXPLODE_UPLIFT_RANGE[0], self._EXPLODE_UPLIFT_RANGE[1] / self.RES_DIV
            )
            life = random.randint(*self._EXPLODE_LIFE)
            h    = (hue + random.uniform(-self._EXPLODE_HUE_JITTER, self._EXPLODE_HUE_JITTER)) % 1.0
            r    = (self._EXPLODE_RADIUS_BASE + random.randint(0, self._EXPLODE_RADIUS_RAND)) // self.RES_DIV
            self._embers.append([x, y, vx, vy, h, max(1, r), life, life])

    # ── main draw ─────────────────────────────────────────────────────────────

    def draw(self, surf, waveform, fft, beat, tick):
        W, H  = config.WIDTH // self.RES_DIV, config.HEIGHT // self.RES_DIV
        bass  = beat
        mid   = config.MID_ENERGY
        high  = config.TREBLE_ENERGY

        if self._trail.get_width() != W or self._trail.get_height() != H:
            self._trail = pygame.Surface((W, H))
            self._trail.fill((0, 0, 0))
            self._fade = pygame.Surface((W, H), pygame.SRCALPHA)
            self._fade.fill((0, 0, 0, self._FADE_ALPHA))
        if self._scaled.get_width() != config.WIDTH or self._scaled.get_height() != config.HEIGHT:
            self._scaled = pygame.Surface((config.WIDTH, config.HEIGHT))
        
        self._hue = (self._hue + self._HUE_BASE_STEP + bass * self._HUE_BASS_GAIN + high * self._HUE_HIGH_GAIN) % 1.0

        # Beat: launch rockets + boost
        if beat > 0.7:
            self._beat_t = self._BEAT_FRAMES
            for _ in range(1 + int(beat)):
                self._launch()

        # Auto-launch between beats
        gain     = max(0.1, getattr(config, 'EFFECT_GAIN', 1.0))
        interval = int(max(self._AUTO_INTERVAL_MIN,
                           min(self._AUTO_INTERVAL_MAX, self._BASE_INTERVAL * gain)))
        self._auto_t += 1
        if self._auto_t >= interval:
            self._auto_t = 0
            self._launch()

        # ── feedback: zoom + rotate trail ─────────────────────────────────────
        t = self._beat_t / self._BEAT_FRAMES if self._beat_t > 0 else 0.0
        self._beat_t = max(0, self._beat_t - 1)
        zoom    = self._BASE_ZOOM + t * (self._BEAT_ZOOM - self._BASE_ZOOM) + bass * self._ZOOM_BASS_GAIN + high * self._ZOOM_HIGH_GAIN
        rot_deg = self._BASE_ROT  + t * (self._BEAT_ROT  - self._BASE_ROT) + mid * self._ROT_MID_GAIN

        # Optimize: rotozoom is expensive, but faster at lower res
        rotated = pygame.transform.rotozoom(self._trail, rot_deg, zoom)
        rw, rh  = rotated.get_size()
        self._trail.fill((0, 0, 0))
        self._trail.blit(rotated, (-((rw - W) // 2), -((rh - H) // 2)))

        # Fade with alpha overlay to preserve chroma better than RGB multiply.
        self._trail.blit(self._fade, (0, 0))

        # ── rockets ───────────────────────────────────────────────────────────
        live = []
        for rk in self._rockets:
            x, y, vx, vy, hue, trail = rk
            vy += _GRAV / self.RES_DIV
            vx *= _DRAG
            x += vx; y += vy
            # Thinned trail for performance
            if tick % self._ROCKET_TRAIL_SKIP == 0:
                trail.append((int(x), int(y)))
                if len(trail) > self._ROCKET_TRAIL_LEN:
                    trail.pop(0)
            rk[0], rk[1], rk[2], rk[3] = x, y, vx, vy

            # Draw rocket trail core only (shimmers with treble)
            if trail:
                pygame.draw.circle(
                    self._trail,
                    hsl(hue, l=self._ROCKET_TRAIL_LIGHT),
                    trail[-1],
                    max(1, int(1.0 + high * self._ROCKET_TRAIL_TREBLE_RADIUS_GAIN)),
                )

            if vy >= 0 or y < -20:
                self._explode(x, y, hue, treble=high)
            elif -self._ROCKET_CULL_MARGIN < x < W + self._ROCKET_CULL_MARGIN:
                live.append(rk)
        self._rockets = live

        # ── embers ────────────────────────────────────────────────────────────
        live = []
        for em in self._embers:
            x, y, vx, vy, hue, radius, life, max_life = em
            vy += _GRAV / self.RES_DIV
            vx *= _DRAG
            vy *= _DRAG
            x += vx; y += vy
            life -= 1
            em[0], em[1], em[2], em[3], em[6] = x, y, vx, vy, life
            if life > 0 and -self._EMBER_CULL_MARGIN < x < W + self._EMBER_CULL_MARGIN and y < H + self._EMBER_CULL_MARGIN:
                brightness = (
                    self._EMBER_LIGHT_BASE
                    + (life / max_life) * self._EMBER_LIGHT_LIFE_GAIN
                    + high * self._EMBER_LIGHT_TREBLE_GAIN
                )
                pygame.draw.circle(self._trail, hsl(hue, l=brightness),
                                   (int(x), int(y)), radius)
                live.append(em)
        self._embers = live

        if self.RES_DIV > 1:
            pygame.transform.scale(self._trail, (config.WIDTH, config.HEIGHT), self._scaled)
            surf.blit(self._scaled, (0, 0), special_flags=pygame.BLEND_RGB_MAX)
        else:
            surf.blit(self._trail, (0, 0), special_flags=pygame.BLEND_RGB_MAX)
