#!/usr/bin/env python3
"""
Music Visualizer — Real-time audio → visuals.

Controls:
  SPACE / click   Switch to next mode
  1-9             Jump to modes 1-9
  0               Jump to mode 10 (Flax)
  -               Jump to mode 11 (Glow Squares)
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
    """Logarithmic spiral arms that pulse and warp with every frequency band."""

    def __init__(self):
        self.angle = 0.0
        self.hue   = 0.0

    def draw(self, surf, waveform, fft, beat, tick):
        cx, cy = WIDTH // 2, HEIGHT // 2
        self.angle += 0.008 + beat * 0.04
        self.hue   += 0.003
        arms   = 7
        points = 320
        scale  = 210 + beat * 380

        for arm in range(arms):
            offset = (arm / arms) * math.tau
            prev   = None
            for i in range(points):
                t     = i / points
                fi    = min(int(t * len(fft)), len(fft) - 1)
                r     = t * scale + fft[fi] * 160
                theta = t * math.pi * 10 + self.angle + offset
                x     = cx + r * math.cos(theta)
                y     = cy + r * math.sin(theta)
                if prev:
                    h     = (self.hue + t + arm / arms) % 1.0
                    color = hsl(h, l=0.35 + fft[fi] * 0.65)
                    pygame.draw.line(surf, color, prev, (int(x), int(y)), 2)
                prev = (int(x), int(y))


class Tentacles:
    """Segmented arms rooted at the centre that sway and writhe with audio."""

    N = 14

    def __init__(self):
        self.hue   = 0.0
        self.phase = 0.0
        self.arms  = [
            {"angle": (i / self.N) * math.tau,
             "segs":  20,
             "slen":  random.uniform(45, 85)}
            for i in range(self.N)
        ]

    def draw(self, surf, waveform, fft, beat, tick):
        cx, cy = WIDTH // 2, HEIGHT // 2
        self.hue   += 0.005
        self.phase += 0.035 + beat * 0.07
        norm = fft / (fft.max() + 1e-6)

        for ti, arm in enumerate(self.arms):
            slen  = arm["slen"] * (1 + beat * 1.6)
            angle = arm["angle"] + self.phase * 0.12
            x, y  = float(cx), float(cy)

            for s in range(arm["segs"]):
                fi    = min(int(s / arm["segs"] * len(norm) * 0.35), len(norm) - 1)
                freq  = norm[fi]
                angle += math.sin(self.phase + s * 0.38 + ti * 0.7) * (0.22 + freq * 0.55)
                nx    = x + math.cos(angle) * slen
                ny    = y + math.sin(angle) * slen
                h     = (self.hue + ti / self.N + s / arm["segs"] * 0.3) % 1.0
                color = hsl(h, l=0.28 + freq * 0.72)
                width = max(1, int((1 - s / arm["segs"]) * 7 * (1 + beat)))
                pygame.draw.line(surf, color, (int(x), int(y)), (int(nx), int(ny)), width)
                x, y = nx, ny


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
    """Burst of colour particles expelled from the centre on every beat."""

    MAX = 800

    def __init__(self):
        self.hue  = 0.0
        self.pool = []

    def _spawn(self, fft, beat):
        for _ in range(int(3 + beat * 12)):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(1, 4) * (1 + beat * 5)
            fi    = random.randint(0, len(fft) - 1)
            self.pool.append({
                "x":    WIDTH  // 2 + random.gauss(0, 20),
                "y":    HEIGHT // 2 + random.gauss(0, 20),
                "vx":   math.cos(angle) * speed,
                "vy":   math.sin(angle) * speed,
                "life": 1.0,
                "hue":  (self.hue + fi / len(fft)) % 1.0,
                "size": max(2, int(2 + fft[fi] * 9)),
            })

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue += 0.004
        self._spawn(fft, beat)
        alive = []
        for p in self.pool:
            p["x"]    += p["vx"]
            p["y"]    += p["vy"]
            p["vy"]   += 0.06          # gravity
            p["vx"]   *= 0.99
            p["life"] -= 0.014
            if p["life"] > 0:
                color = hsl(p["hue"], l=0.3 + p["life"] * 0.5)
                r     = max(1, int(p["size"] * p["life"]))
                pygame.draw.circle(surf, color, (int(p["x"]), int(p["y"])), r)
                alive.append(p)
        self.pool = alive[-self.MAX:]


class Tunnel:
    """First-person ride through a curving tube — rings + longitudinal wall lines."""

    N_RINGS = 24
    N_SIDES = 20    # smoothness of tube cross-section
    TUBE_R  = 2.0   # world-space tube radius

    def __init__(self):
        self.hue  = 0.0
        self.time = 0.0

    def _path(self, t):
        """World-space tube centre at path parameter t."""
        return (math.sin(t * 0.21) * 1.4,
                math.cos(t * 0.16) * 1.0)

    def _proj(self, wx, wy, wz):
        fov = min(WIDTH, HEIGHT) * 0.72
        z   = max(wz, 0.05)
        return (int(wx * fov / z + WIDTH  / 2),
                int(wy * fov / z + HEIGHT / 2),
                fov / z)

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue  += 0.003
        bass       = float(np.mean(fft[:6]))
        self.time += 0.020 + bass * 0.040 + beat * 0.060

        # Build ring list far → near
        rings = []
        for i in range(self.N_RINGS + 1):
            z  = 0.3 + (1 - i / self.N_RINGS) * 7.7   # far=8, near=0.3
            cx, cy = self._path(self.time + z)
            fi = min(int((1 - z / 8) * len(fft) * 0.8), len(fft) - 1)
            rings.append((cx, cy, z, fi))

        # Render pairs far → near
        for i in range(len(rings) - 1):
            cx1, cy1, z1, fi1 = rings[i]
            cx2, cy2, z2, fi2 = rings[i + 1]

            sx1, sy1, sc1 = self._proj(cx1, cy1, z1)
            sx2, sy2, sc2 = self._proj(cx2, cy2, z2)

            # Tube radius pulses slightly with audio
            sr1 = max(1, int(self.TUBE_R * sc1 * (1 + fft[fi1] * 0.25)))
            sr2 = max(1, int(self.TUBE_R * sc2 * (1 + fft[fi2] * 0.25)))

            near_t = 1 - z1 / 8
            h      = (self.hue + near_t * 0.45) % 1.0
            bright = 0.10 + near_t * 0.60 + fft[fi1] * 0.28
            lw     = max(1, int(1 + beat * 2.5))

            # Ring outline
            pygame.draw.circle(surf, hsl(h, l=bright), (sx1, sy1), sr1, lw)

            # Longitudinal wall lines connecting adjacent rings
            for side in range(self.N_SIDES):
                angle = side / self.N_SIDES * math.tau + self.time * 0.07
                p1 = (sx1 + int(math.cos(angle) * sr1),
                      sy1 + int(math.sin(angle) * sr1))
                p2 = (sx2 + int(math.cos(angle) * sr2),
                      sy2 + int(math.sin(angle) * sr2))
                hs = (h + side / self.N_SIDES * 0.12) % 1.0
                pygame.draw.line(surf, hsl(hs, l=bright * 0.65), p1, p2, 1)

        # Brightest nearest ring
        if rings:
            cx, cy, z, fi = rings[-1]
            sx, sy, sc = self._proj(cx, cy, z)
            sr = max(1, int(self.TUBE_R * sc * (1 + fft[fi] * 0.25)))
            pygame.draw.circle(surf, hsl(self.hue, l=0.85), (sx, sy), sr, 2)


class Lissajous:
    """3-D Lissajous figure mapped onto a rotating plane — morphs with audio."""

    def __init__(self):
        self.hue   = 0.0
        self.angle = 0.0
        self.hist  = deque(maxlen=1200)

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue   += 0.003
        self.angle += 0.004 + beat * 0.02

        bass = float(np.mean(fft[:6]))
        mid  = float(np.mean(fft[6:30]))
        high = float(np.mean(fft[30:]))

        ax, ay = 3 + bass * 2, 2 + mid * 2
        px     = math.sin(ax * tick * 0.015 + high * 2)
        py     = math.sin(ay * tick * 0.015)
        self.hist.append((px, py))

        scale = 260 + beat * 180
        cx, cy = WIDTH // 2, HEIGHT // 2

        prev = None
        for j, (px, py) in enumerate(self.hist):
            t     = j / len(self.hist)
            # gentle 3-D rotation projected
            rx    = px * math.cos(self.angle) - py * math.sin(self.angle) * 0.3
            ry    = py * math.cos(self.angle * 0.7)
            sx    = int(cx + rx * scale)
            sy    = int(cy + ry * scale)
            if prev:
                h     = (self.hue + t) % 1.0
                color = hsl(h, l=0.2 + t * 0.7)
                pygame.draw.line(surf, color, prev, (sx, sy), max(1, int(t * 3)))
            prev = (sx, sy)


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
        self.time += 0.007 + beat * 0.018
        bass = float(np.mean(fft[:6]))

        alive = []
        for p in self.pool:
            nx  = p["x"] / WIDTH
            ny  = p["y"] / HEIGHT
            fi  = min(int(nx * len(fft) * 0.45), len(fft) - 1)
            # Flow angle: sine noise field perturbed by the FFT at that x position
            angle = (math.sin(nx * 5.1 + self.time) *
                     math.cos(ny * 3.7 + self.time * 0.6) +
                     fft[fi] * 2.8) * math.pi

            speed = 1.8 + bass * 5 + beat * 2.5
            p["trail"].append((int(p["x"]), int(p["y"])))
            if len(p["trail"]) > self.MAX_TRAIL:
                p["trail"].pop(0)

            p["x"]    += math.cos(angle) * speed
            p["y"]    += math.sin(angle) * speed
            p["life"] -= 0.010

            if (p["life"] > 0
                    and -10 < p["x"] < WIDTH + 10
                    and -10 < p["y"] < HEIGHT + 10
                    and len(p["trail"]) > 1):
                h = (self.hue + p["hoff"] + ny * 0.25) % 1.0
                for j in range(1, len(p["trail"])):
                    t     = j / len(p["trail"])
                    color = hsl(h, l=0.15 + t * 0.65)
                    pygame.draw.line(surf, color,
                                     p["trail"][j - 1], p["trail"][j], 1)
                alive.append(p)

        # Refill dead / out-of-bounds particles
        while len(alive) < self.TARGET_N:
            alive.append(self._new())
        self.pool = alive


class GlowSquares:
    """Grid of squares that bloom and pulse — each column tracks a frequency band."""

    COLS = 22
    ROWS = 13

    def __init__(self):
        self.hue      = 0.0
        self.energies = np.zeros(self.COLS * self.ROWS)

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue += 0.003
        sq_w = WIDTH  // self.COLS
        sq_h = HEIGHT // self.ROWS
        pad  = 5

        for row in range(self.ROWS):
            for col in range(self.COLS):
                idx = row * self.COLS + col
                fi  = min(int(col / self.COLS * len(fft) * 0.55), len(fft) - 1)
                # Higher rows amplify higher energy for a stacked look
                target = fft[fi] * (0.6 + row / self.ROWS * 0.8) * (1 + beat * 0.5)
                self.energies[idx] = self.energies[idx] * 0.75 + target * 0.25
                e = float(self.energies[idx])
                if e < 0.015:
                    continue

                x = col * sq_w + pad
                y = row * sq_h + pad
                w = sq_w - pad * 2
                h = sq_h - pad * 2
                hue = (self.hue + col / self.COLS + row / self.ROWS * 0.25) % 1.0

                # Glow layers — progressively larger & more transparent
                for g in range(4, 0, -1):
                    gs    = g * 5
                    alpha = int(e * 80 / g)
                    if alpha < 5:
                        continue
                    gs_surf = pygame.Surface((w + gs * 2, h + gs * 2), pygame.SRCALPHA)
                    pygame.draw.rect(gs_surf,
                                     (*hsl(hue, l=0.55), alpha),
                                     (0, 0, w + gs * 2, h + gs * 2),
                                     border_radius=4)
                    surf.blit(gs_surf, (x - gs, y - gs))

                # Core square
                pygame.draw.rect(surf, hsl(hue, l=0.25 + e * 0.75),
                                 (x, y, w, h), border_radius=3)


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
                    else:
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
