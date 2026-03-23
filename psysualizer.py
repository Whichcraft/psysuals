#!/usr/bin/env python3
"""
Music Visualizer — Real-time audio → visuals.

Controls:
  SPACE / click   Switch to next mode
  1-9             Jump to modes 1-9
  0               Jump to mode 10 (Flax)
  -               Jump to mode 11 (Waterfall)
  F               Toggle fullscreen
  Q / ESC         Quit
"""

import math
import random
import colorsys
import threading
from collections import deque

import numpy as np
import pygame
import sounddevice as sd

# ── Audio ────────────────────────────────────────────────────────────────────
SAMPLE_RATE = 44100
BLOCK_SIZE  = 1024
CHANNELS    = 1

# ── Window ───────────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1280, 720
FPS           = 60

# ── Shared audio state ───────────────────────────────────────────────────────
_lock        = threading.Lock()
_waveform    = np.zeros(BLOCK_SIZE)
_smooth_fft  = np.zeros(BLOCK_SIZE // 2)
_beat_energy = 0.0


def _audio_cb(indata, frames, time, status):
    global _waveform, _smooth_fft, _beat_energy
    mono     = indata[:, 0]
    windowed = mono * np.hanning(len(mono))
    spectrum = np.abs(np.fft.rfft(windowed))[: BLOCK_SIZE // 2]
    spectrum = np.log1p(spectrum) / 10.0
    with _lock:
        _waveform    = mono.copy()
        _smooth_fft  = _smooth_fft * 0.75 + spectrum * 0.25
        _beat_energy = float(np.mean(_smooth_fft[:20]))  # bass band


def get_audio():
    with _lock:
        return _waveform.copy(), _smooth_fft.copy(), _beat_energy


# ── Colour helpers ────────────────────────────────────────────────────────────

def hsl(h, s=1.0, l=0.5):
    r, g, b = colorsys.hls_to_rgb(h % 1.0, l, s)
    return (int(r * 255), int(g * 255), int(b * 255))


# ── Visualisers ───────────────────────────────────────────────────────────────

class Spiral:
    """Fly through a curving 3-D helix vortex — the tunnel axis drifts like Tunnel,
    arms leave long rainbow trails that fade from black in the distance to bright
    saturated colour up close."""

    N_ARMS = 6
    N_PTS  = 70
    Z_FAR  = 11.0
    Z_NEAR = 0.14
    RADIUS = 1.1   # helix radius in world units
    SPIN   = 1.4   # radians of rotation per unit depth

    def __init__(self):
        self.hue  = 0.0
        self.time = 0.0
        spacing   = (self.Z_FAR - self.Z_NEAR) / self.N_PTS
        self.pts  = [
            {"arm": arm, "z": self.Z_NEAR + j * spacing,
             "pt":  self.Z_NEAR + j * spacing}
            for arm in range(self.N_ARMS)
            for j   in range(self.N_PTS)
        ]

    def _path(self, t):
        """Subtle sway — small enough that the camera stays inside the helix."""
        return (math.sin(t * 0.18) * 0.25,
                math.cos(t * 0.13) * 0.20)

    def _world_pos(self, pt, arm):
        angle   = pt * self.SPIN + arm / self.N_ARMS * math.tau
        cx, cy  = self._path(pt)
        return (cx + self.RADIUS * math.cos(angle),
                cy + self.RADIUS * math.sin(angle))

    def _proj(self, wx, wy, wz):
        fov = min(WIDTH, HEIGHT) * 0.72
        z   = max(wz, 0.01)
        return (int(wx * fov / z + WIDTH  / 2),
                int(wy * fov / z + HEIGHT / 2),
                fov / z)

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue  += 0.005
        bass       = float(np.mean(fft[:6]))
        dt         = 0.05 + bass * 0.09 + beat * 0.13
        self.time += dt

        for p in self.pts:
            p["z"] -= dt
            if p["z"] < self.Z_NEAR:
                p["z"]  += self.Z_FAR
                p["pt"]  = self.time + p["z"]

        # Group by arm, sort far→near, draw connected trail segments
        by_arm = [[] for _ in range(self.N_ARMS)]
        for p in self.pts:
            by_arm[p["arm"]].append(p)

        for arm_idx, arm_pts in enumerate(by_arm):
            arm_pts.sort(key=lambda p: -p["z"])
            prev      = None
            prev_color = None
            for p in arm_pts:
                wx, wy     = self._world_pos(p["pt"], arm_idx)
                sx, sy, sc = self._proj(wx, wy, p["z"])
                near_t     = max(0.0, 1.0 - p["z"] / self.Z_FAR)
                # Hue sweeps a full rainbow from far to near + per-arm offset
                h          = (self.hue + arm_idx / self.N_ARMS * 0.6 + near_t) % 1.0
                # Brightness: near-zero far away, bright & saturated up close
                bright     = near_t ** 1.8 * 0.85 + fft[min(int(near_t * len(fft) * 0.7), len(fft)-1)] * 0.15
                color      = hsl(h, l=max(0.01, bright))
                dot_r      = min(max(1, int(sc * 0.045)), 55)
                lw         = max(1, dot_r // 2)
                if prev and dot_r < 55:
                    # Draw segment with gradient: blend prev and current colour
                    pygame.draw.line(surf, color, prev, (sx, sy), lw)
                if dot_r > 0:
                    pygame.draw.circle(surf, color, (sx, sy), dot_r)
                prev       = (sx, sy)
                prev_color = color


class Tentacles:
    """8 octopus tentacles in 3-D — arms spread over a hemisphere, scene
    rotates slowly around Y to reveal depth.  Suckers placed in screen space."""

    N_ARMS = 8
    N_SEGS = 20
    SEG_W  = 0.30   # world-unit segment length

    def __init__(self):
        self.hue   = 0.0
        self.phase = 0.0
        self.ry    = 0.0
        # Arm base directions: evenly spaced azimuth, fixed elevation (~105° from top)
        el = math.pi * 0.58
        self.dirs = [
            np.array([math.sin(el) * math.cos(i / self.N_ARMS * math.tau),
                      math.cos(el),
                      math.sin(el) * math.sin(i / self.N_ARMS * math.tau)],
                     dtype=float)
            for i in range(self.N_ARMS)
        ]

    def _proj(self, x, y, z):
        fov  = min(WIDTH, HEIGHT) * 0.52
        zcam = max(z + 5.0, 0.05)
        return (int(x * fov / zcam + WIDTH  / 2),
                int(y * fov / zcam + HEIGHT / 2),
                fov / zcam)

    def _rot_y(self, v, c, s):
        return np.array([v[0]*c + v[2]*s, v[1], -v[0]*s + v[2]*c])

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue   += 0.002
        self.phase += 0.045 + beat * 0.07
        self.ry    += 0.007
        norm  = fft / (fft.max() + 1e-6)
        bass  = float(np.mean(norm[:5]))
        cy_s, sy_s = math.cos(self.ry), math.sin(self.ry)

        # Mantle body at world origin
        mx, my, _ = self._proj(0, 0, 0)
        mr = int(32 + bass * 16 + beat * 10)
        pygame.draw.circle(surf, hsl(self.hue, l=0.28), (mx, my), mr)
        pygame.draw.circle(surf, hsl(self.hue, l=0.45), (mx, my), mr, 2)

        for ai in range(self.N_ARMS):
            b_lo   = int( ai      / self.N_ARMS * len(norm) * 0.45)
            b_hi   = int((ai + 1) / self.N_ARMS * len(norm) * 0.45)
            energy = float(np.mean(norm[b_lo : max(b_lo + 1, b_hi)]))
            seg_w  = self.SEG_W * (1 + energy * 0.45 + beat * 0.18)

            d   = self._rot_y(self.dirs[ai], cy_s, sy_s)
            pos = np.zeros(3)
            spts = []   # (sx, sy, width) for sucker pass

            for s in range(self.N_SEGS):
                t  = s / self.N_SEGS
                wh = (math.sin(self.phase * 1.3 - s * 0.55 + ai * 1.1) *
                      (0.26 + energy * 0.72) * (1 - t * 0.4))
                wv = (math.sin(self.phase * 0.85 - s * 0.42 + ai * 0.75) *
                      (0.10 + energy * 0.28) * (1 - t * 0.4))
                # Bend in 3-D: horizontal (around Y) then vertical (around X)
                d = self._rot_y(d, math.cos(wh), math.sin(wh))
                cxv, sxv = math.cos(wv), math.sin(wv)
                d = np.array([d[0], d[1]*cxv - d[2]*sxv, d[1]*sxv + d[2]*cxv])
                ln = np.linalg.norm(d)
                if ln > 1e-6:
                    d /= ln

                npos = pos + d * seg_w * (1 - t * 0.68)
                sx1, sy1, sc1 = self._proj(*pos)
                sx2, sy2, _   = self._proj(*npos)
                w_px = max(1, int((1 - t) * sc1 * 0.14 * (1 + beat * 0.35)))
                hh   = (self.hue + ai / self.N_ARMS * 0.35 + t * 0.12) % 1.0
                pygame.draw.line(surf, hsl(hh, l=0.22 + energy * 0.50 + beat * 0.08),
                                 (sx1, sy1), (sx2, sy2), w_px)
                spts.append((sx1, sy1, w_px))
                pos = npos

            # Suckers in screen space
            for s in range(1, len(spts) - 1, 2):
                px, py, pw = spts[s]
                nx, ny, _  = spts[min(s + 1, len(spts) - 1)]
                bx, by, _  = spts[s - 1]
                dx, dy = nx - bx, ny - by
                dl = math.sqrt(dx*dx + dy*dy) + 1e-6
                ox, oy = -dy / dl, dx / dl
                sr  = max(1, pw // 3)
                ssx = int(px + ox * pw * 0.55)
                ssy = int(py + oy * pw * 0.55)
                pygame.draw.circle(surf, hsl((self.hue + 0.55) % 1.0, l=0.65),
                                   (ssx, ssy), sr)
                pygame.draw.circle(surf, (30, 30, 30), (ssx, ssy), max(1, sr - 1))


class Cube:
    """Dual rotating wireframe cubes — each axis driven by a different band."""

    VERTS = np.array([
        [-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],
        [-1,-1, 1],[1,-1, 1],[1,1, 1],[-1,1, 1],
    ], dtype=float)
    EDGES = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),
             (0,4),(1,5),(2,6),(3,7)]

    def __init__(self):
        self.rx = self.ry = self.rz = 0.0
        self.hue     = 0.0
        self.fade_hue = 0.0   # slowly drifting base hue for colour fade
        self.scale   = 1.0
        self.svel    = 0.0
        self.rvx = self.rvy = self.rvz = 0.0

    @staticmethod
    def _Rx(a):
        c, s = math.cos(a), math.sin(a)
        return np.array([[1,0,0],[0,c,-s],[0,s,c]])

    @staticmethod
    def _Ry(a):
        c, s = math.cos(a), math.sin(a)
        return np.array([[c,0,s],[0,1,0],[-s,0,c]])

    @staticmethod
    def _Rz(a):
        c, s = math.cos(a), math.sin(a)
        return np.array([[c,-s,0],[s,c,0],[0,0,1]])

    def _project(self, v, fov=680):
        z = v[2] + 3.8
        return (int(v[0] * fov / z + WIDTH // 2),
                int(v[1] * fov / z + HEIGHT // 2))

    def draw(self, surf, waveform, fft, beat, tick):
        # Slow colour fade independent of beat
        self.fade_hue += 0.0008
        bass = min(float(np.mean(fft[:5])),   1.0)
        mid  = min(float(np.mean(fft[5:25])), 1.0)
        high = min(float(np.mean(fft[25:])),  1.0)

        # Slower rotation — gentler base speed, smaller beat kick
        self.rvx += 0.002 + mid  * 0.025 + beat * 0.04
        self.rvy += 0.003 + bass * 0.030 + beat * 0.05
        self.rvz += 0.001 + high * 0.015 + beat * 0.02
        # More damping → settles faster, stays slow between beats
        self.rvx *= 0.92
        self.rvy *= 0.92
        self.rvz *= 0.92
        self.rx  += self.rvx
        self.ry  += self.rvy
        self.rz  += self.rvz

        # Gentler spring: smaller impulse, softer restore, heavier damping
        self.svel  += beat * 0.18
        self.svel  += (1.0 - self.scale) * 0.12
        self.svel  *= 0.75
        self.scale += self.svel
        self.scale  = max(0.5, self.scale)

        R = self._Rx(self.rx) @ self._Ry(self.ry) @ self._Rz(self.rz)

        for base_scale, hue_off in ((self.scale, 0.0), (self.scale * 0.45, 0.5)):
            verts = (R @ (self.VERTS * base_scale).T).T
            proj  = [self._project(v) for v in verts]
            for ei, (a, b) in enumerate(self.EDGES):
                # Colour fades slowly across the full spectrum; edges shift slightly
                h     = (self.fade_hue + hue_off + ei / len(self.EDGES) * 0.4) % 1.0
                lw    = max(1, int(2 + self.svel * 4)) if base_scale > 0.4 else 1
                color = hsl(h, l=0.40 + min(self.svel, 1.0) * 0.25)
                pygame.draw.line(surf, color, proj[a], proj[b], lw)


class Bars:
    """Classic spectrum bars with peak markers and a waveform overlay."""

    def __init__(self):
        self.hue = 0.0
        # Pre-compute unique log-spaced bin edges (done once, not per frame).
        # np.unique removes duplicates that astype(int) creates at the low end,
        # so every bar always covers a distinct, non-overlapping range of bins.
        n_bins     = BLOCK_SIZE // 2
        raw        = np.geomspace(2, int(n_bins * 0.85), 81).astype(int)
        self.edges = np.unique(np.clip(raw, 1, n_bins - 1))
        self.n     = len(self.edges) - 1   # actual bar count after dedup
        self.peaks = np.zeros(self.n)

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue += 0.003
        bar_w   = WIDTH // self.n
        heights = np.array([
            np.mean(fft[self.edges[i] : self.edges[i + 1]])
            for i in range(self.n)
        ])
        heights /= (heights.max() + 1e-6)
        self.peaks = np.maximum(self.peaks * 0.97, heights)

        for i, h in enumerate(heights):
            bar_h = int(h * HEIGHT * 0.82)
            peak  = int(self.peaks[i] * HEIGHT * 0.82)
            x     = i * bar_w
            hue   = (self.hue + i / self.n) % 1.0
            pygame.draw.rect(surf, hsl(hue, l=0.38 + h * 0.42),
                             (x, HEIGHT - bar_h, bar_w - 2, bar_h))
            pygame.draw.rect(surf, hsl(hue, l=0.9),
                             (x, HEIGHT - peak - 3, bar_w - 2, 3))

        # Waveform overlay
        step = max(1, len(waveform) // WIDTH)
        pts  = [(int(i * WIDTH / (len(waveform) // step)),
                 int(HEIGHT // 2 + waveform[i * step] * 120))
                for i in range(len(waveform) // step)]
        if len(pts) > 1:
            pygame.draw.lines(surf, hsl(self.hue, l=0.75), False, pts, 2)


class Particles:
    """3-D particle burst — beats spawn spherical shells that fly outward with
    perspective projection; depth gives a genuine volumetric feel."""

    MAX = 1200

    def __init__(self):
        self.hue  = 0.0
        self.pool = []

    def _proj(self, x, y, z):
        fov  = min(WIDTH, HEIGHT) * 0.55
        zcam = max(z + 6.0, 0.05)
        return (int(x * fov / zcam + WIDTH  / 2),
                int(y * fov / zcam + HEIGHT / 2),
                fov / zcam)

    def _spawn(self, fft, beat):
        for _ in range(int(4 + beat * 18)):
            phi   = random.uniform(0, math.tau)
            theta = math.acos(random.uniform(-1, 1))
            sp, cp = math.sin(phi), math.cos(phi)
            st, ct = math.sin(theta), math.cos(theta)
            fi    = random.randint(0, len(fft) - 1)
            speed = random.uniform(0.06, 0.22) * (1 + beat * 3.5 + fft[fi] * 2)
            self.pool.append({
                "x": 0.0, "y": 0.0, "z": 0.0,
                "vx": st * cp * speed,
                "vy": ct * speed,
                "vz": st * sp * speed,
                "life": 1.0,
                "hue":  (self.hue + fi / len(fft)) % 1.0,
                "size": max(2, int(2 + fft[fi] * 10)),
            })

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue += 0.004
        self._spawn(fft, beat)
        alive = []
        for p in self.pool:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["z"] += p["vz"]
            p["vy"]  -= 0.003      # gentle gravity
            p["life"] -= 0.013
            if p["life"] <= 0:
                continue
            sx, sy, sc = self._proj(p["x"], p["y"], p["z"])
            if sc < 0.5:
                continue
            r = max(1, int(p["size"] * p["life"] * sc * 0.08))
            color = hsl(p["hue"], l=0.3 + p["life"] * 0.5)
            pygame.draw.circle(surf, color, (sx, sy), r)
            alive.append(p)
        self.pool = alive[-self.MAX:]


class Tunnel:
    """First-person ride through a curving tube.

    Each ring has a fixed position on the tube path and a z-depth that
    decreases every frame so rings physically fly toward the camera.
    When a ring passes through (z < Z_NEAR) it is recycled to the far end.
    """

    N_RINGS = 30
    N_SIDES = 20
    TUBE_R  = 2.0
    Z_FAR   = 10.0
    Z_NEAR  = 0.18

    def __init__(self):
        self.hue  = 0.0
        self.time = 0.0
        # Each ring: z (depth ahead) and pt (fixed position on the tube path)
        spacing = (self.Z_FAR - self.Z_NEAR) / self.N_RINGS
        self.rings = [
            {"z": self.Z_NEAR + i * spacing,
             "pt": self.Z_NEAR + i * spacing}
            for i in range(self.N_RINGS)
        ]

    def _path(self, t):
        return (math.sin(t * 0.21) * 1.4,
                math.cos(t * 0.16) * 1.0)

    def _proj(self, wx, wy, wz):
        fov = min(WIDTH, HEIGHT) * 0.75
        z   = max(wz, 0.01)
        return (int(wx * fov / z + WIDTH  / 2),
                int(wy * fov / z + HEIGHT / 2),
                fov / z)

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue  += 0.003
        bass       = float(np.mean(fft[:6]))

        # Forward speed — bass and beat push you faster
        dt         = 0.06 + bass * 0.10 + beat * 0.14
        self.time += dt

        # Move every ring toward the camera; recycle past ones to the far end
        for r in self.rings:
            r["z"] -= dt
            if r["z"] < self.Z_NEAR:
                r["z"]  += self.Z_FAR           # wrap to far end
                r["pt"]  = self.time + r["z"]   # new path position

        # Sort far → near so nearer rings overdraw farther ones
        ordered = sorted(self.rings, key=lambda r: -r["z"])

        for i in range(len(ordered) - 1):
            r1 = ordered[i]       # farther
            r2 = ordered[i + 1]  # nearer

            cx1, cy1 = self._path(r1["pt"])
            cx2, cy2 = self._path(r2["pt"])

            sx1, sy1, sc1 = self._proj(cx1, cy1, r1["z"])
            sx2, sy2, sc2 = self._proj(cx2, cy2, r2["z"])

            sr1 = max(1, int(self.TUBE_R * sc1))
            sr2 = max(1, int(self.TUBE_R * sc2))

            near_t = max(0.0, 1.0 - r1["z"] / self.Z_FAR)
            fi     = min(int(near_t * len(fft) * 0.8), len(fft) - 1)
            h      = (self.hue + near_t * 0.5) % 1.0
            bright = 0.08 + near_t * 0.65 + fft[fi] * 0.25
            lw     = max(1, int(1 + beat * 2))

            # Ring circle
            pygame.draw.circle(surf, hsl(h, l=bright), (sx1, sy1), sr1, lw)

            # Longitudinal wall lines to the next (nearer) ring
            for side in range(self.N_SIDES):
                angle = side / self.N_SIDES * math.tau
                p1 = (sx1 + int(math.cos(angle) * sr1),
                      sy1 + int(math.sin(angle) * sr1))
                p2 = (sx2 + int(math.cos(angle) * sr2),
                      sy2 + int(math.sin(angle) * sr2))
                hs = (h + side / self.N_SIDES * 0.10) % 1.0
                pygame.draw.line(surf, hsl(hs, l=bright * 0.6), p1, p2, 1)


class Lissajous:
    """True 3-D Lissajous knot — x=sin(ax·t+dx), y=sin(ay·t+dy), z=sin(az·t+dz).
    Audio drives the frequency ratios; the knot rotates freely in 3-D."""

    TRAIL = 2400

    def __init__(self):
        self.hue  = 0.0
        self.t    = 0.0
        self.rx   = 0.0
        self.ry   = 0.0
        self.rvx  = 0.005
        self.rvy  = 0.007
        self.hist = deque(maxlen=self.TRAIL)
        self.dx   = 0.0
        self.dy   = math.pi / 2
        self.dz   = math.pi / 4

    def _proj(self, x, y, z):
        fov  = min(WIDTH, HEIGHT) * 0.42
        zcam = max(z + 2.8, 0.05)
        return (int(x * fov / zcam + WIDTH  / 2),
                int(y * fov / zcam + HEIGHT / 2))

    def _rot(self, x, y, z):
        cx, sx = math.cos(self.rx), math.sin(self.rx)
        cy, sy = math.cos(self.ry), math.sin(self.ry)
        y2 =  y * cx - z * sx
        z2 =  y * sx + z * cx
        x3 =  x * cy + z2 * sy
        z3 = -x * sy + z2 * cy
        return x3, y2, z3

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue += 0.003
        bass = float(np.mean(fft[:6]))
        mid  = float(np.mean(fft[6:30]))
        high = float(np.mean(fft[30:]))

        ax = 3.0 + bass * 1.0
        ay = 2.0 + mid  * 1.0
        az = 5.0 + high * 1.0

        self.dx += 0.0007 + bass * 0.002
        self.dz += 0.0005 + high * 0.0015

        self.t += 0.018 + beat * 0.04
        self.hist.append((math.sin(ax * self.t + self.dx),
                          math.sin(ay * self.t + self.dy),
                          math.sin(az * self.t + self.dz)))

        self.rvx += 0.0001 + beat * 0.003
        self.rvy += 0.0002 + beat * 0.004
        self.rvx *= 0.98
        self.rvy *= 0.98
        self.rx  += self.rvx
        self.ry  += self.rvy

        scale = 0.82 + beat * 0.18
        pts2d = [self._proj(*self._rot(px * scale, py * scale, pz * scale))
                 for px, py, pz in self.hist]

        n = len(pts2d)
        for j in range(1, n):
            t  = j / n
            pygame.draw.line(surf, hsl((self.hue + t) % 1.0, l=0.2 + t * 0.65),
                             pts2d[j - 1], pts2d[j], max(1, int(t * 3)))


class Mandelbrot:
    """Animated Mandelbrot zoom — always centred on a vivid boundary region."""

    # Curated boundary points: all confirmed to stay colourful when deep-zoomed
    TARGETS = [
        (-0.7435669,   0.1314023),   # Seahorse valley
        (-0.74364085,  0.13182733),  # Deep seahorse spiral
        (-0.7269,      0.1889),      # Classic mini-brot spiral
        (-0.16070135,  1.0375665),   # Upper antenna filament
        (-1.25066,     0.02012),     # Elephant valley tip
        ( 0.37865401,  0.66940249),  # Rabbit island
        (-0.5591870,   0.6347110),   # Dendrite arms
    ]
    RES_W, RES_H = 320, 180
    MAX_ITER     = 80

    def __init__(self):
        self.hue      = 0.0
        self.zoom     = 1.0
        self.target_i = 0
        self.cx, self.cy = self.TARGETS[0]
        self._surf    = pygame.Surface((self.RES_W, self.RES_H))

    def _next_target(self):
        self.target_i = (self.target_i + 1) % len(self.TARGETS)
        self.cx, self.cy = self.TARGETS[self.target_i]
        self.zoom = 1.0

    # ── Vectorised HSL → RGB (operates on 2-D numpy arrays) ──────────────────
    @staticmethod
    def _hsl_to_rgb(h, l):
        """h, l are (H, W) float arrays in [0, 1]; s is fixed at 1."""
        c  = (1.0 - np.abs(2.0 * l - 1.0))
        h6 = h * 6.0
        x  = c * (1.0 - np.abs(h6 % 2.0 - 1.0))
        m  = l - c / 2.0
        i  = h6.astype(int) % 6

        def ch(v0, v1, v2, v3, v4, v5):
            return np.select([i==0,i==1,i==2,i==3,i==4,i==5],
                             [v0,  v1,  v2,  v3,  v4,  v5]) + m

        z = np.zeros_like(h)
        r = ch(c, x, z, z, x, c)
        g = ch(x, c, c, x, z, z)
        b = ch(z, z, x, c, c, x)
        to8 = lambda a: np.clip(a * 255, 0, 255).astype(np.uint8)
        return to8(r), to8(g), to8(b)

    # ── Escape-time computation ───────────────────────────────────────────────
    def _compute(self):
        w  = 3.5 / self.zoom
        h  = 2.0 / self.zoom
        x0 = np.linspace(self.cx - w/2, self.cx + w/2, self.RES_W)
        y0 = np.linspace(self.cy - h/2, self.cy + h/2, self.RES_H)
        C  = x0[np.newaxis, :] + 1j * y0[:, np.newaxis]
        Z  = np.zeros_like(C)
        M  = np.full(C.shape, float(self.MAX_ITER), dtype=float)
        alive = np.ones(C.shape, dtype=bool)

        for i in range(self.MAX_ITER):
            Z[alive]   = Z[alive] ** 2 + C[alive]
            escaped    = alive & (np.abs(Z) > 2.0)
            M[escaped] = i + 1.0 - np.log2(np.log2(np.abs(Z[escaped]) + 1e-10))
            alive[escaped] = False

        return M / self.MAX_ITER   # (RES_H, RES_W) in [0, 1]

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue  += 0.004
        bass       = float(np.mean(fft[:6]))
        self.zoom *= 1.004 + bass * 0.012 + beat * 0.015

        M      = self._compute()
        inside = M >= 0.999

        # If >80 % of pixels are inside the set (black) or zoom too deep → next target
        if float(np.mean(inside)) > 0.80 or self.zoom > 8e5:
            self._next_target()

        # Colour: hue shifts with music; inside set stays black
        mid   = float(np.mean(fft[6:30]))
        h_arr = (M * 4.0 + self.hue + mid) % 1.0
        l_arr = np.where(inside, 0.0, 0.35 + M * 0.45)

        r, g, b = self._hsl_to_rgb(h_arr, l_arr)

        # Assemble pixel array — pygame surfarray uses (W, H, 3)
        rgb = np.stack([r, g, b], axis=2).transpose(1, 0, 2)
        pygame.surfarray.blit_array(self._surf, rgb)

        scaled = pygame.transform.scale(self._surf, (WIDTH, HEIGHT))
        surf.blit(scaled, (0, 0))


class Bubbles:
    """Translucent rising bubbles — size and spawn rate driven by bass."""

    MAX = 250

    def __init__(self):
        self.hue  = 0.0
        self.pool = []

    def _spawn(self, beat, bass):
        for _ in range(int(1 + beat * 7 + bass * 5)):
            r = random.uniform(8, 45) * (1 + bass * 1.5)
            self.pool.append({
                "x":      random.uniform(WIDTH * 0.05, WIDTH * 0.95),
                "y":      float(HEIGHT + r),
                "r":      r,
                "vx":     random.gauss(0, 0.4),
                "vy":    -random.uniform(1.2, 3.5) * (1 + beat * 0.8),
                "hue":    (self.hue + random.uniform(0, 0.35)) % 1.0,
                "wobble": random.uniform(0.025, 0.07),
                "phase":  random.uniform(0, math.tau),
            })

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue += 0.003
        bass = float(np.mean(fft[:8]))
        self._spawn(beat, bass)

        alive = []
        for b in self.pool:
            b["x"] += b["vx"] + math.sin(tick * b["wobble"] + b["phase"]) * 0.9
            b["y"] += b["vy"]
            if b["y"] + b["r"] < 0:
                continue

            life  = max(0.0, min(1.0, (HEIGHT - b["y"]) / HEIGHT))
            r     = int(b["r"])
            alpha = int(life * 130)
            bsurf = pygame.Surface((r * 2 + 6, r * 2 + 6), pygame.SRCALPHA)
            cx, cy = r + 3, r + 3
            # Outer glow ring
            pygame.draw.circle(bsurf, (*hsl(b["hue"], l=0.55), alpha // 2),
                               (cx, cy), r + 2, 3)
            # Main bubble rim
            pygame.draw.circle(bsurf, (*hsl(b["hue"], l=0.70), alpha),
                               (cx, cy), r, 2)
            # Specular highlight
            hr = max(1, r // 4)
            pygame.draw.circle(bsurf, (255, 255, 255, alpha // 2),
                               (cx - r // 3, cy - r // 3), hr)
            surf.blit(bsurf, (int(b["x"]) - cx, int(b["y"]) - cy))
            alive.append(b)

        self.pool = alive[-self.MAX:]


class Flax:
    """Flow-field strands — particle trails follow a noise-like vector field
    modulated by the audio spectrum, creating silk/fibre-like motion."""

    TARGET_N = 300
    MAX_TRAIL = 14

    def __init__(self):
        self.hue  = 0.0
        self.time = 0.0
        self.pool = [self._new() for _ in range(self.TARGET_N)]

    @staticmethod
    def _new():
        return {
            "x":    random.uniform(0, WIDTH),
            "y":    random.uniform(0, HEIGHT),
            "life": random.uniform(0.4, 1.0),
            "hoff": random.uniform(0, 0.4),
            "trail": [],
        }

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue  += 0.003
        # time must advance fast enough for the sine field to visibly shift
        self.time += 0.035 + beat * 0.06
        bass = float(np.mean(fft[:6]))
        mid  = float(np.mean(fft[6:40]))

        alive = []
        for p in self.pool:
            nx  = p["x"] / WIDTH
            ny  = p["y"] / HEIGHT
            fi  = min(int(nx * len(fft) * 0.55), len(fft) - 1)
            # Flow angle: strongly perturbed by audio so field reacts visibly
            angle = (math.sin(nx * 4.8 + self.time) *
                     math.cos(ny * 3.5 + self.time * 0.7) +
                     fft[fi] * 4.5 + mid * 2.0) * math.pi

            speed = 2.5 + bass * 7 + beat * 4
            p["trail"].append((int(p["x"]), int(p["y"])))
            if len(p["trail"]) > self.MAX_TRAIL:
                p["trail"].pop(0)

            p["x"]    += math.cos(angle) * speed
            p["y"]    += math.sin(angle) * speed
            p["life"] -= 0.012

            if (p["life"] > 0
                    and -10 < p["x"] < WIDTH + 10
                    and -10 < p["y"] < HEIGHT + 10
                    and len(p["trail"]) > 1):
                h = (self.hue + p["hoff"] + ny * 0.3) % 1.0
                for j in range(1, len(p["trail"])):
                    t     = j / len(p["trail"])
                    color = hsl(h, l=0.15 + t * 0.70)
                    pygame.draw.line(surf, color,
                                     p["trail"][j - 1], p["trail"][j], 1)
                alive.append(p)

        # Refill dead / out-of-bounds particles
        while len(alive) < self.TARGET_N:
            alive.append(self._new())
        self.pool = alive


class GlowSquares:
    """Waterfall spectrogram — scrolling time-frequency display.

    Each new frame adds a row at the top; older slices scroll downward.
    Log-spaced frequency bins; hue = frequency position, brightness = energy.
    """

    ROWS = 100   # time slices to keep (history depth)
    COLS = 80    # frequency bins

    def __init__(self):
        self.hue   = 0.0
        n_bins     = BLOCK_SIZE // 2
        raw        = np.geomspace(2, int(n_bins * 0.85), self.COLS + 1).astype(int)
        self.edges = np.unique(np.clip(raw, 1, n_bins - 1))
        self.cols  = len(self.edges) - 1
        self.buf   = deque(maxlen=self.ROWS)

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue += 0.003
        row = np.array([
            float(np.mean(fft[self.edges[c]:self.edges[c + 1]]))
            for c in range(self.cols)
        ])
        row /= (row.max() + 1e-6)
        self.buf.appendleft(row)

        bw  = max(1, WIDTH  // self.cols)
        bh  = max(4, HEIGHT // self.ROWS)

        for ri, r in enumerate(self.buf):
            y = ri * bh
            if y > HEIGHT:
                break
            age = ri / max(len(self.buf), 1)
            for ci, e in enumerate(r):
                if e < 0.02:
                    continue
                x   = ci * bw
                hue = (self.hue + ci / self.cols * 0.75) % 1.0
                lit = (1 - age * 0.7) * (0.2 + e * 0.8)
                pygame.draw.rect(surf, hsl(hue, l=min(lit, 0.95)),
                                 (x, y, bw - 1, bh - 1))


# ── Mode registry ─────────────────────────────────────────────────────────────

MODES = [
    ("Spiral",      Spiral),
    ("Tentacles",   Tentacles),
    ("Cube",        Cube),
    ("Spectrum",    Bars),
    ("Particles",   Particles),
    ("Tunnel",      Tunnel),
    ("Lissajous",   Lissajous),
    ("Mandelbrot",   Mandelbrot),
    ("Bubbles",      Bubbles),
    ("Flax",         Flax),
    ("Glow Squares", GlowSquares),
]


# ── Device picker ─────────────────────────────────────────────────────────────

def _input_devices():
    """Return list of (index, name) for all input-capable devices."""
    devs = []
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            devs.append((i, d["name"]))
    return devs


def _draw_device_picker(screen, font, devices, selected, active_idx):
    """Render the device-picker overlay; returns nothing."""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 210))
    screen.blit(overlay, (0, 0))

    title = font.render("SELECT INPUT DEVICE   ↑↓ navigate   Enter confirm   Esc cancel",
                         True, (200, 200, 200))
    screen.blit(title, (40, 30))

    row_h  = 28
    y0     = 80
    visn   = min(len(devices), (HEIGHT - y0 - 20) // row_h)
    # Scroll window so `selected` is always visible
    start  = max(0, min(selected - visn // 2, len(devices) - visn))

    for i, (dev_idx, name) in enumerate(devices[start:start + visn]):
        row   = start + i
        y     = y0 + i * row_h
        is_sel   = row == selected
        is_live  = dev_idx == active_idx
        bg_col   = (40, 80, 140) if is_sel else (0, 0, 0, 0)
        if is_sel:
            pygame.draw.rect(screen, bg_col, (30, y - 2, WIDTH - 60, row_h - 2))
        marker = "► " if is_live else "  "
        label  = f"{marker}{dev_idx:3d}  {name}"
        color  = (255, 255, 100) if is_sel else (140, 140, 140)
        screen.blit(font.render(label, True, color), (40, y))


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    global WIDTH, HEIGHT

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Music Visualizer")
    clock  = pygame.time.Clock()
    font   = pygame.font.SysFont("monospace", 16)

    devices    = _input_devices()
    active_dev = None          # None → sounddevice default
    stream     = sd.InputStream(
        samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE,
        channels=CHANNELS, device=active_dev, callback=_audio_cb)
    stream.start()

    mode_idx      = 0
    name, VisCls  = MODES[mode_idx]
    vis           = VisCls()
    fullscreen    = False
    tick          = 0
    energy_hist   = deque(maxlen=45)
    picking       = False      # device-picker overlay open?
    pick_sel      = 0          # highlighted row in picker

    def make_fade():
        s = pygame.Surface((WIDTH, HEIGHT))
        s.set_alpha(38)
        s.fill((0, 0, 0))
        return s

    fade = make_fade()

    hint = ("  SPACE/click: next mode  |  1-{n}: pick mode  "
            "|  D: device  |  F: fullscreen  |  Q: quit").format(n=len(MODES))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stream.stop(); stream.close()
                pygame.quit(); return

            elif event.type == pygame.KEYDOWN:

                # ── device picker open ────────────────────────────────────────
                if picking:
                    if event.key == pygame.K_ESCAPE:
                        picking = False
                    elif event.key == pygame.K_UP:
                        pick_sel = max(0, pick_sel - 1)
                    elif event.key == pygame.K_DOWN:
                        pick_sel = min(len(devices) - 1, pick_sel + 1)
                    elif event.key == pygame.K_RETURN:
                        new_idx  = devices[pick_sel][0]
                        if new_idx != active_dev:
                            stream.stop(); stream.close()
                            active_dev = new_idx
                            stream = sd.InputStream(
                                samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE,
                                channels=CHANNELS, device=active_dev,
                                callback=_audio_cb)
                            stream.start()
                        picking = False

                # ── normal key handling ───────────────────────────────────────
                else:
                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        stream.stop(); stream.close()
                        pygame.quit(); return
                    elif event.key == pygame.K_SPACE:
                        mode_idx = (mode_idx + 1) % len(MODES)
                        name, VisCls = MODES[mode_idx]; vis = VisCls()
                    elif event.key == pygame.K_f:
                        fullscreen = not fullscreen
                        flags  = pygame.FULLSCREEN if fullscreen else 0
                        screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
                        WIDTH, HEIGHT = screen.get_size()
                        fade = make_fade()
                        vis  = VisCls()   # re-init with new dimensions
                    elif event.key == pygame.K_d:
                        devices  = _input_devices()   # refresh list
                        picking  = True
                        # Pre-select currently active device
                        active_indices = [d[0] for d in devices]
                        pick_sel = (active_indices.index(active_dev)
                                    if active_dev in active_indices else 0)
                    elif event.key == pygame.K_0:
                        mode_idx = 9
                        name, VisCls = MODES[mode_idx]; vis = VisCls()
                    elif event.key == pygame.K_MINUS:
                        mode_idx = 10
                        name, VisCls = MODES[mode_idx]; vis = VisCls()
                    else:
                        idx = event.key - pygame.K_1
                        if 0 <= idx < len(MODES):
                            mode_idx = idx
                            name, VisCls = MODES[mode_idx]; vis = VisCls()

            elif event.type == pygame.MOUSEBUTTONDOWN and not picking:
                mode_idx = (mode_idx + 1) % len(MODES)
                name, VisCls = MODES[mode_idx]; vis = VisCls()

        waveform, fft, raw_beat = get_audio()
        energy_hist.append(raw_beat)
        avg  = float(np.mean(energy_hist)) if energy_hist else 1e-6
        beat = max(0.0, min(raw_beat / (avg + 1e-6) - 1.0, 3.0))

        screen.blit(fade, (0, 0))
        vis.draw(screen, waveform, fft, beat, tick)

        # HUD
        dev_name = (sd.query_devices(active_dev)["name"]
                    if active_dev is not None else "default")
        label = font.render(
            f"  [{mode_idx+1}/{len(MODES)}] {name}  |  🎤 {dev_name}{hint}",
            True, (90, 90, 90))
        screen.blit(label, (6, 6))

        if picking:
            _draw_device_picker(screen, font, devices, pick_sel, active_dev)

        pygame.display.flip()
        clock.tick(FPS)
        tick += 1


if __name__ == "__main__":
    main()
