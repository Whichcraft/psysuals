"""Butterflies — up to three pairs dancing to the music.

Each pair: a solo butterfly flutters in first; its partner joins after
10–30 s.  Once together they *chase each other* in a tightening mutual
orbit — both turning toward the other's position, creating a playful
love-pursuit spiral.  After a random lifetime the pair wanders off-screen
and vanishes.  New pairs can re-enter from the edges.
Wing flapping syncs when partners are close; sparkles on the beat.

Trail is managed on an internal surface (TRAIL_ALPHA = 0) so it is
preserved correctly on Android / OpenGL backends where the display
backbuffer is not guaranteed between frames.
"""
import math
import random

import numpy as np
import pygame

import config
from .utils import hsl


from .base import Effect

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


def _wing_mask_frame(scale, flap, size):
    """Build one cached wing-mask frame for a given scale and flap amount."""
    upper_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    lower_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    for upper, surf in ((1, upper_surf), (-1, lower_surf)):
        for side in (-1, 1):
            pts = _wing_poly(center, center, 0.0, side, upper, flap, scale)
            pygame.draw.polygon(surf, (255, 255, 255, 255), pts)
    return upper_surf, lower_surf


# ── Single butterfly ──────────────────────────────────────────────────────────

class _Butterfly:
    BODY_LEN_SCALE = 8
    BODY_WIDTH_SCALE = 2
    OUTLINE_SCALE_THRESHOLD = 3.0
    OFFSCREEN_MARGIN = 80
    BOUNDARY_CLAMP_SCALE = 28
    BOUNDARY_BOUNCE_NUDGE = 1.5
    BOUNCE_RECOVER_CD = (45, 120)
    WANDER_TURN = math.pi * 0.6
    WANDER_CD = (60, 180)
    EDGE_REPEL_SCALE = 50
    EDGE_PUSH = 2.5
    EDGE_TURN_LIMIT = 0.35
    EDGE_TURN_GAIN = 0.50
    WANDER_TURN_LIMIT = 0.10
    WANDER_TURN_GAIN = 0.14
    DEPART_SPEED = 2.5
    DEPART_BASS_GAIN = 0.5
    FLAP_BASE = 0.09
    FLAP_BASS_GAIN = 0.20
    FLAP_MID_GAIN = 0.35
    FLAP_HIGH_GAIN = 0.15
    FLIGHT_BASE = 1.5
    FLIGHT_BASS_GAIN = 0.8
    FLIGHT_MID_GAIN = 0.60
    WING_FRAME_COUNT = 16
    _WING_FRAME_CACHE = {}

    def __init__(self, x, y, hue, scale=4.0):
        self.x           = float(x)
        self.y           = float(y)
        self.heading     = random.uniform(0, math.tau)
        self.wing_phase  = random.uniform(0, math.tau)
        self.hue         = hue
        self.scale       = scale
        self._wander_des = self.heading
        self._wander_cd  = 0
        self._depart_ang = None
        self._wing_cache_key = None
        self._wing_frames = None
        self._wing_layers = None
        self._ensure_wing_cache()

    @property
    def off_screen(self):
        m = self.OFFSCREEN_MARGIN * self.scale
        return (self.x < -m or self.x > config.WIDTH  + m or
                self.y < -m or self.y > config.HEIGHT + m)

    def start_depart(self):
        if self._depart_ang is None:
            self._depart_ang = random.uniform(0, math.tau)

    @classmethod
    def _get_wing_frames(cls, scale):
        key = round(float(scale), 2)
        frames = cls._WING_FRAME_CACHE.get(key)
        if frames is None:
            size = max(32, int(scale * 36) + 18)
            if cls.WING_FRAME_COUNT <= 1:
                flaps = [0.0]
            else:
                flaps = [i / (cls.WING_FRAME_COUNT - 1) for i in range(cls.WING_FRAME_COUNT)]
            frames = [_wing_mask_frame(scale, flap, size) for flap in flaps]
            cls._WING_FRAME_CACHE[key] = frames
        return frames

    def _ensure_wing_cache(self):
        key = round(float(self.scale), 2)
        if self._wing_cache_key == key and self._wing_frames is not None:
            return
        self._wing_cache_key = key
        self._wing_frames = self._get_wing_frames(self.scale)
        frame_size = self._wing_frames[0][0].get_size()
        self._wing_layers = [
            pygame.Surface(frame_size, pygame.SRCALPHA),
            pygame.Surface(frame_size, pygame.SRCALPHA),
        ]

    def _bounce_from_bounds(self):
        cl = float(int(self.BOUNDARY_CLAMP_SCALE * self.scale))
        hit = False

        if self.x <= cl:
            self.x = cl + self.BOUNDARY_BOUNCE_NUDGE * self.scale
            if math.cos(self.heading) < 0.0:
                self.heading = math.pi - self.heading
            hit = True
        elif self.x >= config.WIDTH - cl:
            self.x = float(config.WIDTH) - cl - self.BOUNDARY_BOUNCE_NUDGE * self.scale
            if math.cos(self.heading) > 0.0:
                self.heading = math.pi - self.heading
            hit = True

        if self.y <= cl:
            self.y = cl + self.BOUNDARY_BOUNCE_NUDGE * self.scale
            if math.sin(self.heading) < 0.0:
                self.heading = -self.heading
            hit = True
        elif self.y >= config.HEIGHT - cl:
            self.y = float(config.HEIGHT) - cl - self.BOUNDARY_BOUNCE_NUDGE * self.scale
            if math.sin(self.heading) > 0.0:
                self.heading = -self.heading
            hit = True

        if hit:
            self.heading %= math.tau
            self._wander_des = self.heading
            self._wander_cd = random.randint(*self.BOUNCE_RECOVER_CD)

    def update(self, bass, beat, mid, high, t, chase_pos=None):
        """Update position and wing phase.

        chase_pos: if set, the butterfly steers toward this (x, y) target
                   instead of wandering.  Used for the mutual-chase love pairs.
        """
        # Mids and treble accelerate wing flapping speed
        self.wing_phase += (
            self.FLAP_BASE
            + bass * self.FLAP_BASS_GAIN
            + mid * self.FLAP_MID_GAIN
            + high * self.FLAP_HIGH_GAIN
        )

        if self._depart_ang is not None:
            self.heading += (self._depart_ang - self.heading + math.pi) % math.tau - math.pi
            spd = (self.DEPART_SPEED + bass * self.DEPART_BASS_GAIN) * self.scale
            self.x += math.cos(self.heading) * spd
            self.y += math.sin(self.heading) * spd
            return

        if chase_pos is not None:
            desired = math.atan2(chase_pos[1] - self.y, chase_pos[0] - self.x)
        else:
            self._wander_cd -= 1
            if self._wander_cd <= 0:
                self._wander_des = (self.heading
                                    + random.uniform(-self.WANDER_TURN, self.WANDER_TURN))
                self._wander_cd = random.randint(*self.WANDER_CD)
            desired = self._wander_des

        # ── Boundary repulsion ────────────────────────────────────────────────
        m = min(int(self.EDGE_REPEL_SCALE * self.scale), config.WIDTH // 5, config.HEIGHT // 5)
        rx, ry = 0.0, 0.0
        if self.x < m:
            rx = (m - self.x) / m
        elif self.x > config.WIDTH - m:
            rx = (config.WIDTH - m - self.x) / m
        if self.y < m:
            ry = (m - self.y) / m
        elif self.y > config.HEIGHT - m:
            ry = (config.HEIGHT - m - self.y) / m

        if rx or ry:
            push = self.scale * max(abs(rx), abs(ry)) * self.EDGE_PUSH
            self.x += rx * push
            self.y += ry * push
            desired = math.atan2(ry, rx)
            diff = (desired - self.heading + math.pi) % math.tau - math.pi
            self.heading += max(-self.EDGE_TURN_LIMIT, min(self.EDGE_TURN_LIMIT, diff * self.EDGE_TURN_GAIN))
            self._wander_des = desired
            self._wander_cd  = random.randint(*self.WANDER_CD)
        else:
            diff = (desired - self.heading + math.pi) % math.tau - math.pi
            self.heading += max(-self.WANDER_TURN_LIMIT, min(self.WANDER_TURN_LIMIT, diff * self.WANDER_TURN_GAIN))

        # Mids speed up flight velocity
        spd = (self.FLIGHT_BASE + bass * self.FLIGHT_BASS_GAIN + mid * self.FLIGHT_MID_GAIN) * self.scale
        self.x += math.cos(self.heading) * spd
        self.y += math.sin(self.heading) * spd

        self._bounce_from_bounds()

    def draw(self, surf, outline_col=None):
        self._ensure_wing_cache()
        flap     = math.sin(self.wing_phase) * 0.5 + 0.5
        body_col = hsl(self.hue, l=0.28)
        wc1      = hsl(self.hue, l=0.58)
        wc2      = hsl((self.hue + 0.10) % 1.0, l=0.46)
        frame_idx = min(self.WING_FRAME_COUNT - 1,
                        max(0, int(round(flap * (self.WING_FRAME_COUNT - 1)))))
        upper_mask, lower_mask = self._wing_frames[frame_idx]
        angle_deg = -math.degrees(self.heading)
        center = (int(self.x), int(self.y))

        for layer, mask, col in (
            (self._wing_layers[0], upper_mask, wc1),
            (self._wing_layers[1], lower_mask, wc2),
        ):
            layer.fill((0, 0, 0, 0))
            layer.blit(mask, (0, 0))
            layer.fill((*col, 255), special_flags=pygame.BLEND_RGBA_MULT)
            rotated = pygame.transform.rotate(layer, angle_deg)
            rect = rotated.get_rect(center=center)
            surf.blit(rotated, rect)

        ca, sa = math.cos(self.heading), math.sin(self.heading)
        bl = int(self.BODY_LEN_SCALE * self.scale) # Slightly shorter body
        hx, hy = int(self.x + ca * bl), int(self.y + sa * bl)
        tx, ty = int(self.x - ca * bl), int(self.y - sa * bl)
        lw = max(1, int(self.BODY_WIDTH_SCALE * self.scale))
        pygame.draw.line(surf, body_col, (hx, hy), (tx, ty), lw)

        # Skip antennas for better FPS
        # for s in (-1, 1):
        #     a_ang = self.heading + s * 0.38
        #     aex = int(hx + math.cos(a_ang) * 9 * self.scale)
        #     aey = int(hy + math.sin(a_ang) * 9 * self.scale)
        #     pygame.draw.line(surf, body_col, (hx, hy), (aex, aey), 1)


# ── Pair ──────────────────────────────────────────────────────────────────────

def _edge_spawn():
    """Return a position just inside one screen edge."""
    m = 60
    edge = random.choice("LRTB")
    if edge == "L":  return float(m), random.uniform(m, config.HEIGHT - m)
    if edge == "R":  return float(config.WIDTH - m), random.uniform(m, config.HEIGHT - m)
    if edge == "T":  return random.uniform(m, config.WIDTH - m), float(m)
    return random.uniform(m, config.WIDTH - m), float(config.HEIGHT - m)


# Scale is 70 % of the original 7.2 / 6.84 (big); small is 35 % of original
_BIG_SOLO_SCALE   = round(7.2  * 0.70, 2)   # 5.04
_BIG_LOVE_SCALE   = round(6.84 * 0.70, 2)   # 4.79
_SMALL_SOLO_SCALE = round(7.2  * 0.35, 2)   # 2.52
_SMALL_LOVE_SCALE = round(6.84 * 0.35, 2)   # 2.39

# Per-pair size assignments: [big, small, big] — rotated for replacement pairs
_PAIR_SIZES = [
    (_BIG_SOLO_SCALE,   _BIG_LOVE_SCALE),
    (_SMALL_SOLO_SCALE, _SMALL_LOVE_SCALE),
    (_BIG_SOLO_SCALE,   _BIG_LOVE_SCALE),
]

# Keep old names as aliases so any external references continue to work
_SOLO_SCALE = _BIG_SOLO_SCALE
_LOVE_SCALE = _BIG_LOVE_SCALE


class _Pair:
    """One loving pair of butterflies with its own lifecycle.

    Once both butterflies are alive they chase each other — solo steers
    toward love and love steers toward solo, each targeting a point offset
    by a rotating angle at a shrinking radius.  This creates a playful
    spiral pursuit that eventually settles into a tight mutual orbit.
    """

    JOIN_DELAY = (120, 300)
    LIFETIME = (2400, 5400)
    BREAK_CD = (800, 1600)
    BREAK_TIMER = (200, 500)
    BREAK_RESET_CD = (900, 1800)
    ORBIT_RADIUS_START = 120.0
    ORBIT_RADIUS_MIN = 40.0
    ORBIT_RADIUS_RESET_BOOST = 80.0
    ORBIT_RADIUS_RESET_MAX = 200.0
    ORBIT_BASE_SPEED = 0.012
    ORBIT_BEAT_GAIN = 0.020
    ORBIT_MID_GAIN = 0.015
    ORBIT_TIGHTEN_GAIN = 0.003
    ORBIT_TIGHTEN_REF = 240.0
    ORBIT_DECAY = 0.06
    WING_SYNC_RANGE = 130
    SPARKLE_DIST = 300
    SPARKLE_BASE = 4
    SPARKLE_BEAT_GAIN = 6
    SPARKLE_TREBLE_GAIN = 10
    SPARKLE_SIGMA = 25
    SPARKLE_RADIUS_BASE = 5

    def __init__(self, hue, spawn_delay=0,
                 solo_scale=_BIG_SOLO_SCALE, love_scale=_BIG_LOVE_SCALE):
        self.hue          = hue
        self._spawn_delay = spawn_delay
        self._solo_scale  = solo_scale
        self._love_scale  = love_scale
        self._join_delay  = random.randint(*self.JOIN_DELAY)
        self._lifetime    = random.randint(*self.LIFETIME)
        self._age         = -spawn_delay
        self._orbit_ang   = random.uniform(0, math.tau)
        self._orbit_r     = self.ORBIT_RADIUS_START
        self.solo         = None
        self.love         = None
        self._departing   = False
        # Wander-break: occasionally one butterfly leaves the orbit briefly
        self._break_cd    = random.randint(*self.BREAK_CD)
        self._break_timer = 0                          # counts down during break

    @property
    def dead(self):
        if not self._departing:
            return False
        b1_gone = self.solo is None or self.solo.off_screen
        b2_gone = self.love is None or self.love.off_screen
        return b1_gone and b2_gone

    def update(self, bass, beat, mid, high, global_hue, t):
        self._age += 1

        if self.solo is None and self._age >= 0:
            x, y = _edge_spawn()
            self.solo = _Butterfly(x, y, hue=global_hue, scale=self._solo_scale)

        if self.solo is None:
            return

        self.solo.hue = global_hue
        if self.love:
            self.love.hue = (global_hue + 0.50) % 1.0

        if self.love is None and self._age >= self._join_delay:
            x, y = _edge_spawn()
            self.love = _Butterfly(x, y,
                                   hue=(global_hue + 0.50) % 1.0,
                                   scale=self._love_scale)

        if self._age >= self._lifetime and not self._departing:
            self._departing = True
            self.solo.start_depart()
            if self.love:
                self.love.start_depart()

        if self.love is not None and not self._departing:
            # Wander-break countdown
            if self._break_timer > 0:
                self._break_timer -= 1
            else:
                self._break_cd -= 1
                if self._break_cd <= 0:
                    self._break_timer = random.randint(*self.BREAK_TIMER)
                    self._break_cd    = random.randint(*self.BREAK_RESET_CD)
                    # Expand orbit radius back out so reunion feels fresh
                    self._orbit_r = min(self._orbit_r + self.ORBIT_RADIUS_RESET_BOOST,
                                        self.ORBIT_RADIUS_RESET_MAX)

            if self._break_timer > 0:
                # One butterfly wanders freely; the orbit pauses
                self.solo.update(bass, beat, mid, high, t)
                self.love.update(bass, beat, mid, high, t)
            else:
                # Mutual chase: orbit angle rotates faster as radius shrinks
                # (conservation-of-angular-momentum feel)
                ang_speed = (
                    self.ORBIT_BASE_SPEED
                    + beat * self.ORBIT_BEAT_GAIN
                    + mid * self.ORBIT_MID_GAIN
                    + self.ORBIT_TIGHTEN_GAIN * max(0.0, 1.0 - self._orbit_r / self.ORBIT_TIGHTEN_REF)
                )
                self._orbit_ang += ang_speed
                if self._orbit_r > self.ORBIT_RADIUS_MIN:
                    self._orbit_r -= self.ORBIT_DECAY

                r = self._orbit_r
                # Solo chases: point offset from love's position at opposite angle
                solo_target = (
                    self.love.x + math.cos(self._orbit_ang + math.pi) * r,
                    self.love.y + math.sin(self._orbit_ang + math.pi) * r,
                )
                # Love chases: point offset from solo's position at the orbit angle
                love_target = (
                    self.solo.x + math.cos(self._orbit_ang) * r,
                    self.solo.y + math.sin(self._orbit_ang) * r,
                )
                self.solo.update(bass, beat, mid, high, t, chase_pos=solo_target)
                self.love.update(bass, beat, mid, high, t, chase_pos=love_target)
        else:
            self.solo.update(bass, beat, mid, high, t)
            if self.love:
                self.love.update(bass, beat, mid, high, t)

        # Wing sync when close
        if self.love is not None:
            dist = math.hypot(self.love.x - self.solo.x,
                              self.love.y - self.solo.y)
            sync_range = self.WING_SYNC_RANGE * self._solo_scale
            if dist < sync_range:
                sync = 1.0 - dist / sync_range
                diff = self.love.wing_phase - self.solo.wing_phase
                self.love.wing_phase -= diff * sync * 0.12
                self.solo.wing_phase += diff * sync * 0.12

    def draw(self, surf, beat, global_hue, treble=0.0):
        if self.solo is None:
            return

        # Sparkles on treble transients and bass beats
        if self.love and (beat > 0.8 or treble > 0.45) and not self._departing:
            dist = math.hypot(self.love.x - self.solo.x,
                              self.love.y - self.solo.y)
            if dist < self.SPARKLE_DIST:
                mx = (self.solo.x + self.love.x) / 2
                my = (self.solo.y + self.love.y) / 2
                sparkle_n = int(self.SPARKLE_BASE + beat * self.SPARKLE_BEAT_GAIN + treble * self.SPARKLE_TREBLE_GAIN)
                sx_arr = self._rng.normal(mx, self.SPARKLE_SIGMA, sparkle_n)
                sy_arr = self._rng.normal(my, self.SPARKLE_SIGMA, sparkle_n)
                r_arr = self._rng.integers(2, int(self.SPARKLE_RADIUS_BASE + treble * 6) + 1, sparkle_n)
                for sx, sy, r in zip(sx_arr, sy_arr, r_arr):
                    pygame.draw.circle(surf,
                                       hsl((global_hue + 0.12) % 1.0, l=0.80),
                                       (int(sx), int(sy)), int(r))

        self.solo.draw(surf)
        if self.love:
            self.love.draw(surf)


# ── Main effect ───────────────────────────────────────────────────────────────

class Butterflies(Effect):
    """Three pairs of butterflies.  Each pair has its own lifecycle:
    solo → partner joins → mutual love chase → wander off-screen → new pair.

    TRAIL_ALPHA = 0: trails are managed on an internal surface so they survive
    on Android / OpenGL backends where the display backbuffer is not preserved
    between frames.
    """

    TRAIL_ALPHA = 0    # owns its trail surface
    RES_DIV     = 2    # Render at 1/2 resolution
    MAX_PAIRS   = 3
    _FADE_ALPHA = 22
    SPAWN_OFFSETS = ((30, 90), (80, 160))
    RESPAWN_DELAY = (20, 60)
    COHESION_BASE = 0.010
    COHESION_BEAT_GAIN = 0.008
    COHESION_MIN_RANGE = 90.0
    COHESION_ORBIT_SCALE = 1.55
    COHESION_PULL_MAX = 1.6
    COHESION_PULL_SCALE = 0.02
    SEPARATION_BASE = 1.1
    SEPARATION_BEAT_GAIN = 0.9
    SAME_PAIR_BASE = 16.0
    SAME_PAIR_BEAT_GAIN = 4.0
    SAME_PAIR_STRENGTH = 0.35
    CROSS_PAIR_BASE = 22.0
    CROSS_PAIR_BEAT_GAIN = 7.0
    CROSS_PAIR_STRENGTH = 1.0
    SEPARATION_TURN_MAX = 0.08
    SEPARATION_TURN_SCALE = 0.02

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rng = np.random.default_rng(config.RNG_SEED or None)
        W, H, RD = self._render_size()
        self._tick       = 0
        self._global_hue = random.random()
        self._trail      = pygame.Surface((W, H))
        self._trail.fill((0, 0, 0))
        self._scaled     = pygame.Surface((config.WIDTH, config.HEIGHT))
        self._fade       = pygame.Surface((W, H), pygame.SRCALPHA)
        self._fade.fill((0, 0, 0, self._FADE_ALPHA))
        self._pairs: list[_Pair] = []
        offsets = [0,
                   random.randint(*self.SPAWN_OFFSETS[0]),
                   random.randint(*self.SPAWN_OFFSETS[1])]
        for i, off in enumerate(offsets):
            hue = (self._global_hue + i / self.MAX_PAIRS) % 1.0
            ss, ls = _PAIR_SIZES[i % len(_PAIR_SIZES)]
            self._pairs.append(_Pair(hue, spawn_delay=off, solo_scale=ss, love_scale=ls))

    def _apply_swarm_forces(self, beat):
        entries = []
        for idx, pair in enumerate(self._pairs):
            if pair.solo and not pair.solo.off_screen:
                entries.append((pair.solo, idx))
            if pair.love and not pair.love.off_screen:
                entries.append((pair.love, idx))

        # Mild pair cohesion keeps active partners from drifting too far apart
        # during wander/break phases without overpowering the chase motion.
        cohesion = self.COHESION_BASE + beat * self.COHESION_BEAT_GAIN
        for pair in self._pairs:
            if pair.solo is None or pair.love is None or pair._departing:
                continue
            dx = pair.love.x - pair.solo.x
            dy = pair.love.y - pair.solo.y
            dist = math.hypot(dx, dy)
            target = max(self.COHESION_MIN_RANGE, pair._orbit_r * self.COHESION_ORBIT_SCALE)
            if dist > target:
                pull = min(self.COHESION_PULL_MAX, (dist - target) * cohesion * self.COHESION_PULL_SCALE)
                nx = dx / (dist + 1e-6)
                ny = dy / (dist + 1e-6)
                pair.solo.x += nx * pull * pair.solo.scale
                pair.solo.y += ny * pull * pair.solo.scale
                pair.love.x -= nx * pull * pair.love.scale
                pair.love.y -= ny * pull * pair.love.scale

        # Pairwise separation keeps butterflies from collapsing into the same
        # pixels when multiple pairs cross through the same region.
        sep_gain = self.SEPARATION_BASE + beat * self.SEPARATION_BEAT_GAIN
        for i in range(len(entries)):
            a, a_pair = entries[i]
            for j in range(i + 1, len(entries)):
                b, b_pair = entries[j]
                dx = b.x - a.x
                dy = b.y - a.y
                dist2 = dx * dx + dy * dy
                if dist2 <= 1e-6:
                    ang = random.uniform(0.0, math.tau)
                    dx = math.cos(ang)
                    dy = math.sin(ang)
                    dist2 = 1.0
                dist = math.sqrt(dist2)

                if a_pair == b_pair:
                    desired = (a.scale + b.scale) * (self.SAME_PAIR_BASE + beat * self.SAME_PAIR_BEAT_GAIN)
                    strength = self.SAME_PAIR_STRENGTH
                else:
                    desired = (a.scale + b.scale) * (self.CROSS_PAIR_BASE + beat * self.CROSS_PAIR_BEAT_GAIN)
                    strength = self.CROSS_PAIR_STRENGTH

                if dist >= desired:
                    continue

                nx = dx / dist
                ny = dy / dist
                push = (1.0 - dist / desired) * sep_gain * strength
                a.x -= nx * push * a.scale
                a.y -= ny * push * a.scale
                b.x += nx * push * b.scale
                b.y += ny * push * b.scale

                turn = min(self.SEPARATION_TURN_MAX, push * self.SEPARATION_TURN_SCALE)
                a.heading = (a.heading - turn) % math.tau
                b.heading = (b.heading + turn) % math.tau

        for butterfly, _ in entries:
            butterfly._bounce_from_bounds()

    def draw(self, surf, waveform, fft, beat, tick):
        self._tick       += 1
        self._global_hue  = (self._global_hue + 0.0014) % 1.0
        
        bass = beat
        mid  = config.MID_ENERGY
        high = config.TREBLE_ENERGY

        W, H, RD = self._render_size()
        if self._trail.get_width() != W or self._trail.get_height() != H:
            self._trail = pygame.Surface((W, H))
            self._trail.fill((0, 0, 0))
            self._fade = pygame.Surface((W, H), pygame.SRCALPHA)
            self._fade.fill((0, 0, 0, self._FADE_ALPHA))
        if self._scaled.get_width() != config.WIDTH or self._scaled.get_height() != config.HEIGHT:
            self._scaled = pygame.Surface((config.WIDTH, config.HEIGHT))

        self._pairs = [p for p in self._pairs if not p.dead]
        while len(self._pairs) < self.MAX_PAIRS:
            i = len(self._pairs)
            ss, ls = _PAIR_SIZES[i % len(_PAIR_SIZES)]
            hue = (self._global_hue + random.random() * 0.5) % 1.0
            self._pairs.append(_Pair(hue, spawn_delay=random.randint(*self.RESPAWN_DELAY),
                                     solo_scale=ss, love_scale=ls))

        # Fade with alpha overlay so color trails stay cleaner over time.
        self._trail.blit(self._fade, (0, 0))

        for i, pair in enumerate(self._pairs):
            gh = (self._global_hue + i / self.MAX_PAIRS) % 1.0
            pair.update(bass, beat, mid, high, gh, self._tick)

        self._apply_swarm_forces(beat)

        for i, pair in enumerate(self._pairs):
            gh = (self._global_hue + i / self.MAX_PAIRS) % 1.0
            pair.draw(self._trail, beat, gh, treble=high)

        if RD > 1:
            pygame.transform.scale(self._trail, (config.WIDTH, config.HEIGHT), self._scaled)
            surf.blit(self._scaled, (0, 0), special_flags=pygame.BLEND_RGB_MAX)
        else:
            surf.blit(self._trail, (0, 0), special_flags=pygame.BLEND_RGB_MAX)
