#!/usr/bin/env python3
"""
Music Visualizer — Real-time audio → visuals.

Controls:
  SPACE / click   Switch to next mode
  1-9             Jump to modes 1-9
  0               Jump to mode 10 (Waterfall)
  F               Toggle fullscreen
  H               Toggle HUD / legend
  Q / ESC         Quit
"""

__version__ = "1.1.0"

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
_lock           = threading.Lock()
_waveform       = np.zeros(BLOCK_SIZE)
_smooth_fft     = np.zeros(BLOCK_SIZE // 2)
_beat_energy    = 0.0
_hanning_window = np.hanning(BLOCK_SIZE)


def _audio_cb(indata, frames, time, status):
    global _waveform, _smooth_fft, _beat_energy
    mono     = indata[:, 0]
    spectrum = np.abs(np.fft.rfft(mono * _hanning_window))[: BLOCK_SIZE // 2]
    np.log1p(spectrum, out=spectrum)
    spectrum /= 10.0
    with _lock:
        _waveform    = mono.copy()
        _smooth_fft *= 0.75
        _smooth_fft += spectrum * 0.25
        _beat_energy = float(_smooth_fft[:20].mean())  # bass band


def get_audio():
    with _lock:
        return _waveform.copy(), _smooth_fft.copy(), _beat_energy


# ── Colour helpers ────────────────────────────────────────────────────────────

def hsl(h, s=1.0, l=0.5):
    r, g, b = colorsys.hls_to_rgb(h % 1.0, max(0.0, min(l, 1.0)), s)
    return (int(r * 255), int(g * 255), int(b * 255))


def _hsl_batch(h, l, s=1.0):
    """Vectorised HSL→RGB for numpy arrays; returns uint8 array of shape (..., 3)."""
    h  = np.asarray(h, dtype=float) % 1.0
    l  = np.clip(np.asarray(l, dtype=float), 0.0, 1.0)
    c  = (1.0 - np.abs(2.0 * l - 1.0)) * s
    h6 = h * 6.0
    x  = c * (1.0 - np.abs(h6 % 2.0 - 1.0))
    m  = l - c / 2.0
    i  = h6.astype(np.int32) % 6
    z  = np.zeros_like(h)
    r  = np.select([i==0,i==1,i==2,i==3,i==4,i==5], [c,x,z,z,x,c]) + m
    g  = np.select([i==0,i==1,i==2,i==3,i==4,i==5], [x,c,c,x,z,z]) + m
    b  = np.select([i==0,i==1,i==2,i==3,i==4,i==5], [z,z,x,c,c,x]) + m
    return np.stack([
        np.clip(r * 255, 0, 255).astype(np.uint8),
        np.clip(g * 255, 0, 255).astype(np.uint8),
        np.clip(b * 255, 0, 255).astype(np.uint8),
    ], axis=-1)


# ── Visualisers ───────────────────────────────────────────────────────────────

class Spiral:
    """Neon helix vortex — 6 arms fly toward the viewer with audio-reactive radius
    breathing, two-pass neon glow on arm lines, and cross-ring connections between
    arms at regular depth intervals.  Beat spring explodes the whole structure
    outward and snaps the hue palette."""

    N_ARMS    = 6
    N_PTS     = 80
    Z_FAR     = 10.0
    Z_NEAR    = 0.12
    RADIUS    = 1.0
    SPIN      = 1.6
    N_SYM     = 3
    RING_STEP = 8   # draw a cross-ring every N depth points

    def __init__(self):
        self.hue   = 0.0
        self.time  = 0.0
        self.scale = 1.0
        self.svel  = 0.0
        spacing    = (self.Z_FAR - self.Z_NEAR) / self.N_PTS
        self.pts   = [
            {"arm": arm, "z": self.Z_NEAR + j * spacing,
             "pt":  self.Z_NEAR + j * spacing}
            for arm in range(self.N_ARMS)
            for j   in range(self.N_PTS)
        ]

    def _path(self, t):
        return (math.sin(t * 0.18) * 0.25, math.cos(t * 0.13) * 0.20)

    def _proj(self, wx, wy, wz):
        fov = min(WIDTH, HEIGHT) * 0.72
        z   = max(wz, 0.01)
        return (int(wx * fov / z + WIDTH  // 2),
                int(wy * fov / z + HEIGHT // 2),
                fov / z)

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue  += 0.007 + beat * 0.04
        bass       = float(np.mean(fft[:6]))
        dt         = 0.038 + bass * 0.10 + beat * 0.18
        self.time += dt

        # Spring scale — beat kicks outward, restores to 1.0
        self.svel += beat * 0.48
        self.svel += (1.0 - self.scale) * 0.25
        self.svel *= 0.81
        self.scale = max(0.4, self.scale + self.svel)

        for p in self.pts:
            p["z"] -= dt
            if p["z"] < self.Z_NEAR:
                p["z"] += self.Z_FAR
                p["pt"] = self.time + p["z"]

        # Build per-arm screen-point lists (sorted far→near — same z order across arms)
        by_arm = [[] for _ in range(self.N_ARMS)]
        for p in self.pts:
            by_arm[p["arm"]].append(p)

        cx0, cy0 = WIDTH // 2, HEIGHT // 2

        arm_segs = []
        for arm_idx, arm_pts in enumerate(by_arm):
            arm_pts.sort(key=lambda p: -p["z"])
            segs = []
            for p in arm_pts:
                near_t = max(0.0, 1.0 - p["z"] / self.Z_FAR)
                band   = min(int(near_t * len(fft) * 0.55), len(fft) - 1)
                r_mod  = float(fft[band]) * 1.5   # radius breathes with audio
                angle  = p["pt"] * self.SPIN + arm_idx / self.N_ARMS * math.tau
                pcx, pcy = self._path(p["pt"])
                r      = (self.RADIUS + r_mod) * self.scale
                wx     = pcx + r * math.cos(angle)
                wy     = pcy + r * math.sin(angle)
                sx, sy, sc = self._proj(wx, wy, p["z"])
                h      = (self.hue + arm_idx / self.N_ARMS * 0.5 + near_t * 1.3) % 1.0
                bright = near_t ** 1.15
                segs.append((sx, sy, h, bright, sc, near_t))
            arm_segs.append(segs)

        for sym in range(self.N_SYM):
            ang    = sym / self.N_SYM * math.tau
            ca, sa = math.cos(ang), math.sin(ang)

            def rot(sx, sy, _ca=ca, _sa=sa):
                dx, dy = sx - cx0, sy - cy0
                return (int(cx0 + dx * _ca - dy * _sa),
                        int(cy0 + dx * _sa + dy * _ca))

            # Arm dots — two-pass neon glow per point
            for segs in arm_segs:
                for sx, sy, h, bright, sc, near_t in segs:
                    rx, ry  = rot(sx, sy)
                    r_dot   = max(1, min(int(sc * 0.028), 9))
                    c_halo  = hsl(h, l=bright * 0.20)
                    c_core  = hsl(h, l=min(bright * 0.90 + 0.08, 0.95))
                    pygame.draw.circle(surf, c_halo, (rx, ry), r_dot * 3 + 1)
                    pygame.draw.circle(surf, c_core, (rx, ry), r_dot)
                    if near_t > 0.80 and beat > 0.35:
                        fr = max(3, int(r_dot * (2.2 + beat * 0.9)))
                        pygame.draw.circle(surf, hsl(h, l=0.96), (rx, ry), fr)

            # Cross-ring dots — bright dot at each arm×depth intersection
            n = len(arm_segs[0]) if arm_segs else 0
            for j in range(0, n, self.RING_STEP):
                for a_segs in arm_segs:
                    if j < len(a_segs):
                        sx, sy, h, bright, sc, near_t = a_segs[j]
                        rp      = rot(sx, sy)
                        r_dot   = max(1, min(int(sc * 0.022), 7))
                        c_halo  = hsl(h, l=bright * 0.35)
                        c_core  = hsl(h, l=min(bright * 0.85 + 0.10, 0.92))
                        pygame.draw.circle(surf, c_halo, rp, r_dot * 3)
                        pygame.draw.circle(surf, c_core, rp, r_dot + 1)


class Plasma:
    """Full-screen sine-interference plasma — four overlapping wave fields
    create a flowing psychedelic texture.  Audio modulates wave frequency,
    time speed, palette, and beat triggers a global brightness flash."""

    RES_DIV = 4   # render at ¼ resolution then upscale (keeps 60 fps)

    def __init__(self):
        self.hue  = 0.0
        self.time = 0.0
        rw = max(1, WIDTH  // self.RES_DIV)
        rh = max(1, HEIGHT // self.RES_DIV)
        self._surf = pygame.Surface((rw, rh))
        # Centred coordinate grids, reused every frame
        xs = np.linspace(-math.pi * 2.5, math.pi * 2.5, rw)
        ys = np.linspace(-math.pi * 2.5, math.pi * 2.5, rh)
        self._X, self._Y = np.meshgrid(xs, ys)
        self._R = np.sqrt(self._X ** 2 + self._Y ** 2)

    @staticmethod
    def _hsl_arr(h, l):
        """Vectorised HSL→RGB (s=1) for 2-D numpy arrays; returns uint8 (H,W,3)."""
        c  = 1.0 - np.abs(2.0 * l - 1.0)
        h6 = h * 6.0
        x  = c * (1.0 - np.abs(h6 % 2.0 - 1.0))
        m  = l - c / 2.0
        i  = h6.astype(int) % 6
        z  = np.zeros_like(h)
        r = np.select([i==0,i==1,i==2,i==3,i==4,i==5], [c,x,z,z,x,c]) + m
        g = np.select([i==0,i==1,i==2,i==3,i==4,i==5], [x,c,c,x,z,z]) + m
        b = np.select([i==0,i==1,i==2,i==3,i==4,i==5], [z,z,x,c,c,x]) + m
        u8 = lambda a: np.clip(a * 255, 0, 255).astype(np.uint8)
        return np.stack([u8(r), u8(g), u8(b)], axis=2)

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue  += 0.005
        bass = float(np.mean(fft[:6]))
        mid  = float(np.mean(fft[6:30]))
        high = float(np.mean(fft[30:]))

        self.time += 0.045 + bass * 0.09 + beat * 0.14

        # Frequency modulation — mid pushes waves tighter
        fm = 1.0 + mid * 0.7

        t  = self.time
        # Four sine fields at different angles and phases
        v  = (np.sin(self._X * fm          +  t        ) +
              np.sin(self._Y * fm * 0.8    +  t * 1.4  ) +
              np.sin((self._X * 0.6 + self._Y * 0.8) * fm + t * 0.9) +
              np.sin(self._R * fm * 0.5    -  t * 1.2  )) * 0.25   # −1 … 1

        # Hue: plasma value + slowly drifting global hue + bass palette shift
        h = (v * 0.55 + 0.5 + self.hue + bass * 0.35) % 1.0
        # Brightness: beat flashes the whole screen
        l = np.clip(0.28 + v * 0.22 + beat * 0.22 + high * 0.08, 0.0, 0.95)

        rgb = self._hsl_arr(h, l)
        # surfarray expects (W, H, 3)
        pygame.surfarray.blit_array(self._surf, rgb.transpose(1, 0, 2))
        surf.blit(pygame.transform.scale(self._surf, (WIDTH, HEIGHT)), (0, 0))


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
        self.fade_hue += 0.0018
        bass = min(float(np.mean(fft[:5])),   1.0)
        mid  = min(float(np.mean(fft[5:25])), 1.0)
        high = min(float(np.mean(fft[25:])),  1.0)

        # Slower rotation — gentler base speed, smaller beat kick
        self.rvx += 0.001 + mid  * 0.012 + beat * 0.05
        self.rvy += 0.0015 + bass * 0.015 + beat * 0.06
        self.rvz += 0.0005 + high * 0.008 + beat * 0.025
        # Heavy damping → stays slow, only kicks on strong beats
        self.rvx *= 0.94
        self.rvy *= 0.94
        self.rvz *= 0.94
        self.rx  += self.rvx
        self.ry  += self.rvy
        self.rz  += self.rvz

        # Gentler spring: smaller impulse, softer restore, heavier damping
        self.svel  += beat * 0.32
        self.svel  += (1.0 - self.scale) * 0.18
        self.svel  *= 0.68
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
        sums    = np.add.reduceat(fft[:self.edges[-1]], self.edges[:-1])
        heights = sums / np.maximum(np.diff(self.edges), 1).astype(float)
        heights = heights[:self.n]
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


class Nova:
    """Extremely psychedelic waveform kaleidoscope — audio waveform mapped to
    polar sectors with 7-fold mirror symmetry across 4 concentric spinning
    layers.  Each layer reacts to a different frequency band; beat explodes
    all layers outward with spring physics then snaps them back."""

    N_SYM    = 7    # prime-fold kaleidoscope symmetry
    N_LAYERS = 4
    N_WAVE   = 120  # waveform samples per sector

    def __init__(self):
        self.hue  = 0.0
        self.time = 0.0
        signs = [1, -1, 1, -1]
        self.rot   = [i / self.N_LAYERS * math.pi for i in range(self.N_LAYERS)]
        self.rvel  = [signs[i] * (0.005 + i * 0.0022) for i in range(self.N_LAYERS)]
        self.poff  = [0.0] * self.N_LAYERS
        self.pvel  = [0.0] * self.N_LAYERS

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue  += 0.007
        self.time += 0.018 + beat * 0.025
        bass = float(np.mean(fft[:6]))
        mid  = float(np.mean(fft[6:30]))
        high = float(np.mean(fft[30:]))
        bands = [bass, mid, high, (bass + mid + high) / 3.0]

        cx, cy = WIDTH // 2, HEIGHT // 2
        max_r  = min(WIDTH, HEIGHT) * 0.44

        # Spring physics per layer
        for i in range(self.N_LAYERS):
            e = min(bands[i], 1.0)
            self.pvel[i] += beat * (0.32 + e * 0.14)
            self.pvel[i] += -self.poff[i] * 0.24
            self.pvel[i] *= 0.63
            self.poff[i] += self.pvel[i]
            self.rot[i]  += self.rvel[i] * (1.0 + e * 2.8 + bass * 1.2)

        # Downsample waveform
        step   = max(1, len(waveform) // self.N_WAVE)
        wave   = waveform[::step][:self.N_WAVE]
        sector = math.tau / self.N_SYM

        # Draw outermost layer first
        for i in range(self.N_LAYERS - 1, -1, -1):
            e      = min(bands[i], 1.0)
            base_r = max_r * (0.22 + i / max(self.N_LAYERS - 1, 1) * 0.72)
            r_off  = self.poff[i] * base_r * 0.42
            h      = (self.hue + i / self.N_LAYERS * 0.45) % 1.0
            bright = 0.44 + e * 0.44 + beat * 0.10
            amp    = base_r * (0.14 + e * 0.20 + beat * 0.10)
            lw     = max(1, int(1 + e * 2.5 + beat * 2))

            for sym in range(self.N_SYM):
                # Alternate sectors are time-reversed for mirror continuity
                w_slice   = wave if sym % 2 == 0 else wave[::-1]
                angle_off = sym * sector + self.rot[i]
                n_w   = len(w_slice)
                j_arr = np.arange(n_w, dtype=float)
                theta = j_arr / n_w * sector + angle_off
                r_pts = np.maximum(2.0, base_r + r_off + w_slice.astype(float) * amp)
                xs    = np.round(cx + np.cos(theta) * r_pts).astype(int)
                ys    = np.round(cy + np.sin(theta) * r_pts).astype(int)
                pts   = list(zip(xs.tolist(), ys.tolist()))
                if len(pts) > 1:
                    pygame.draw.lines(surf, hsl(h, l=bright), False, pts, lw)

            # Thin connecting ring at base radius
            pygame.draw.circle(surf, hsl(h, l=bright * 0.28),
                               (cx, cy), max(1, int(base_r + r_off)), 1)

        # ── Rotating triangles at sector boundaries ───────────────────────────
        # Two counter-rotating triangle rings — one CW, one CCW.
        # Each triangle points outward along a sector boundary.
        for tri_layer, (t_rvel, t_r_frac, t_h_off) in enumerate(
                [(0.012, 0.58, 0.25), (-0.008, 0.82, 0.55)]):
            t_rot = self.rot[0] * t_rvel / 0.005   # reuse layer-0 angle scaled
            t_r   = max_r * t_r_frac * (1 + self.poff[0] * 0.25)
            t_h   = (self.hue + t_h_off) % 1.0
            t_l   = 0.50 + bass * 0.30 + beat * 0.18
            t_lw  = max(1, int(1 + beat * 2.5))
            for sym in range(self.N_SYM):
                a_mid  = sym / self.N_SYM * math.tau + t_rot
                a_l    = a_mid - math.pi / self.N_SYM * 0.55
                a_r    = a_mid + math.pi / self.N_SYM * 0.55
                tip    = (int(cx + math.cos(a_mid) * t_r * 1.18),
                          int(cy + math.sin(a_mid) * t_r * 1.18))
                base_l = (int(cx + math.cos(a_l)  * t_r * 0.82),
                          int(cy + math.sin(a_l)  * t_r * 0.82))
                base_r = (int(cx + math.cos(a_r)  * t_r * 0.82),
                          int(cy + math.sin(a_r)  * t_r * 0.82))
                pygame.draw.polygon(surf, hsl(t_h, l=t_l),
                                    [tip, base_l, base_r], t_lw)

        # Central pulse on beat
        cr = max(2, int(10 + bass * 22 + beat * 40))
        pygame.draw.circle(surf, hsl(self.hue, l=0.55 + beat * 0.35), (cx, cy), cr)
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), max(1, cr // 4))


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
        spacing = (self.Z_FAR - self.Z_NEAR) / self.N_RINGS
        self.rings = [
            {"z": self.Z_NEAR + i * spacing,
             "pt": self.Z_NEAR + i * spacing}
            for i in range(self.N_RINGS)
        ]
        self.tris = []   # beat-spawned triangles flying toward camera

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
        self.hue  += 0.006
        bass       = float(np.mean(fft[:6]))
        mid        = float(np.mean(fft[6:30]))

        dt         = 0.05 + bass * 0.13 + beat * 0.28
        self.time += dt

        # Spawn triangles on beat
        if beat > 0.5:
            for _ in range(int(1 + beat * 2.5)):
                z = self.Z_FAR * random.uniform(0.65, 0.95)
                self.tris.append({
                    "z":    z,
                    "pt":   self.time + z,
                    "rot":  random.uniform(0, math.tau),
                    "rvel": random.choice([-1, 1]) * random.uniform(0.04, 0.12),
                    "size": random.uniform(0.45, 1.1),
                    "hue":  (self.hue + random.uniform(0, 0.5)) % 1.0,
                })

        for r in self.rings:
            r["z"] -= dt
            if r["z"] < self.Z_NEAR:
                r["z"]  += self.Z_FAR
                r["pt"]  = self.time + r["z"]

        ordered = sorted(self.rings, key=lambda r: -r["z"])

        for i in range(len(ordered) - 1):
            r1 = ordered[i]
            r2 = ordered[i + 1]

            cx1, cy1 = self._path(r1["pt"])
            cx2, cy2 = self._path(r2["pt"])

            sx1, sy1, sc1 = self._proj(cx1, cy1, r1["z"])
            sx2, sy2, sc2 = self._proj(cx2, cy2, r2["z"])

            sr1 = max(1, int(self.TUBE_R * sc1))
            sr2 = max(1, int(self.TUBE_R * sc2))

            near_t = max(0.0, 1.0 - r1["z"] / self.Z_FAR)
            fi     = min(int(near_t * len(fft) * 0.8), len(fft) - 1)
            # Full rainbow sweep across depth; beat flares nearest rings
            h      = (self.hue + near_t) % 1.0
            bright = 0.06 + near_t * 0.70 + fft[fi] * 0.20 + beat * near_t * 0.50
            lw     = max(1, int(1 + beat * 3 * near_t))

            # Neon glow: wide dim halo then thin bright ring
            pygame.draw.circle(surf, hsl(h, l=bright * 0.35), (sx1, sy1), sr1 + 4, lw + 3)
            pygame.draw.circle(surf, hsl(h, l=bright),        (sx1, sy1), sr1,     lw)

            # Longitudinal wall lines
            for side in range(self.N_SIDES):
                angle = side / self.N_SIDES * math.tau
                p1 = (sx1 + int(math.cos(angle) * sr1),
                      sy1 + int(math.sin(angle) * sr1))
                p2 = (sx2 + int(math.cos(angle) * sr2),
                      sy2 + int(math.sin(angle) * sr2))
                hs = (h + side / self.N_SIDES * 0.25) % 1.0
                pygame.draw.line(surf, hsl(hs, l=bright * 0.55), p1, p2, 1)

            # Rotating inner polygon — 3-to-6 sides, alternating direction per ring
            n_star  = 3 + (i % 4)
            s_dir   = 1 if i % 2 == 0 else -1
            s_rot   = self.time * 0.45 * s_dir + i * 0.52
            s_r     = max(2, int(sr1 * 0.52))
            s_h     = (h + 0.5) % 1.0
            s_l     = min(bright * 1.1 + mid * 0.2, 0.92)
            s_pts   = [
                (sx1 + int(math.cos(v / n_star * math.tau + s_rot) * s_r),
                 sy1 + int(math.sin(v / n_star * math.tau + s_rot) * s_r))
                for v in range(n_star)
            ]
            pygame.draw.polygon(surf, hsl(s_h, l=s_l), s_pts, max(1, lw))

        # ── Beat-spawned triangles flying toward camera ───────────────────────
        live = []
        for tri in self.tris:
            tri["z"]   -= dt
            tri["rot"] += tri["rvel"]
            if tri["z"] < self.Z_NEAR:
                continue
            tcx, tcy   = self._path(tri["pt"])
            sx, sy, sc = self._proj(tcx, tcy, tri["z"])
            near_t     = max(0.0, 1.0 - tri["z"] / self.Z_FAR)
            tr         = max(3, int(tri["size"] * sc))
            h          = (tri["hue"] + near_t * 0.4) % 1.0
            bright     = 0.35 + near_t * 0.60
            lw         = max(1, int(1 + near_t * 3))
            pts = [
                (sx + int(math.cos(tri["rot"] + v * math.tau / 3) * tr),
                 sy + int(math.sin(tri["rot"] + v * math.tau / 3) * tr))
                for v in range(3)
            ]
            # Neon glow: wide dim halo, then bright core
            pygame.draw.polygon(surf, hsl(h, l=bright * 0.30), pts, lw + 4)
            pygame.draw.polygon(surf, hsl(h, l=bright),         pts, lw)
            live.append(tri)
        self.tris = live[-80:]


class Lissajous:
    """Psytrance 3-D Lissajous knot — trefoil (3-fold) symmetry, neon glow,
    beat-driven spring bursts.

    Three copies of the knot are drawn at 0 / 120 / 240 ° around the centre.
    Each trail is rendered in two passes (wide dim halo + thin bright core)
    for a neon bloom effect.  Beat explodes the scale outward then snaps back.
    """

    TRAIL = 1400
    N_SYM = 3

    def __init__(self):
        self.hue   = 0.0
        self.t     = 0.0
        self.rx    = 0.0
        self.ry    = 0.0
        self.rvx   = 0.006
        self.rvy   = 0.009
        self.hist  = deque(maxlen=self.TRAIL)
        self.dx    = 0.0
        self.dy    = math.pi / 2
        self.dz    = math.pi / 4
        self.scale = 1.0
        self.svel  = 0.0

    def _rot(self, x, y, z):
        cx, sx = math.cos(self.rx), math.sin(self.rx)
        cy, sy = math.cos(self.ry), math.sin(self.ry)
        y2 =  y * cx - z * sx
        z2 =  y * sx + z * cx
        x3 =  x * cy + z2 * sy
        z3 = -x * sy + z2 * cy
        return x3, y2, z3

    def _proj_flat(self, x, y, z):
        """Return (float, float) relative to centre — no rounding yet."""
        fov  = min(WIDTH, HEIGHT) * 0.40
        zcam = max(z + 2.8, 0.05)
        return x * fov / zcam, y * fov / zcam

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue += 0.006
        bass = float(np.mean(fft[:6]))
        mid  = float(np.mean(fft[6:30]))
        high = float(np.mean(fft[30:]))

        ax = 3.0 + bass * 1.3
        ay = 2.0 + mid  * 1.3
        az = 5.0 + high * 1.3

        self.dx += 0.001  + bass * 0.003
        self.dz += 0.0008 + high * 0.002

        self.t += 0.022 + beat * 0.06
        self.hist.append((math.sin(ax * self.t + self.dx),
                          math.sin(ay * self.t + self.dy),
                          math.sin(az * self.t + self.dz)))

        # Beat scale burst — spring physics
        self.svel  += beat * 0.55
        self.svel  += (1.0 - self.scale) * 0.26
        self.svel  *= 0.60
        self.scale += self.svel
        self.scale  = max(0.35, self.scale)

        # Hue jump on beat — each kick shifts the palette
        self.hue += beat * 0.12

        # 3-D rotation with stronger beat inertia
        self.rvx += beat * 0.016 + 0.0002
        self.rvy += beat * 0.019 + 0.0003
        self.rvx *= 0.97
        self.rvy *= 0.97
        self.rx  += self.rvx
        self.ry  += self.rvy

        s  = self.scale
        n  = len(self.hist)
        if n < 2:
            return

        # Vectorised rotation + projection for all trail points
        pts_3d = np.array(self.hist) * s           # (n, 3)
        px_a, py_a, pz_a = pts_3d[:, 0], pts_3d[:, 1], pts_3d[:, 2]
        cx_r, sx_r = math.cos(self.rx), math.sin(self.rx)
        cy_r, sy_r = math.cos(self.ry), math.sin(self.ry)
        y2   = py_a * cx_r - pz_a * sx_r
        z2   = py_a * sx_r + pz_a * cx_r
        x3   = px_a * cy_r + z2 * sy_r
        z3   = -px_a * sy_r + z2 * cy_r
        fov_l  = min(WIDTH, HEIGHT) * 0.40
        zcam   = np.maximum(z3 + 2.8, 0.05)
        raw_x  = x3 * fov_l / zcam
        raw_y  = y2 * fov_l / zcam

        cx, cy = WIDTH // 2, HEIGHT // 2

        # Glow pass constants: (line-width multiplier, l_tail, l_head)
        # Beat raises the bright-core brightness
        l1_bright = min(0.90 + beat * 0.08, 0.98)
        PASSES = [(4, 0.08, 0.22), (1, 0.50, l1_bright)]

        t_arr = np.arange(n, dtype=float) / n
        lw_base = (t_arr * 4).astype(int)

        for sym in range(self.N_SYM):
            a      = sym / self.N_SYM * math.tau
            ca, sa = math.cos(a), math.sin(a)
            sx_arr = np.round(cx + raw_x * ca - raw_y * sa).astype(int)
            sy_arr = np.round(cy + raw_x * sa + raw_y * ca).astype(int)
            pts    = list(zip(sx_arr.tolist(), sy_arr.tolist()))

            for lw_mul, l0, l1 in PASSES:
                h_arr  = (self.hue + sym / self.N_SYM * 0.33 + t_arr * 0.55) % 1.0
                l_arr  = l0 + t_arr * (l1 - l0)
                colors = _hsl_batch(h_arr, l_arr)      # (n, 3) uint8
                lw_arr = np.maximum(1, lw_base * lw_mul)
                for j in range(1, n):
                    pygame.draw.line(surf,
                                     (int(colors[j, 0]), int(colors[j, 1]), int(colors[j, 2])),
                                     pts[j - 1], pts[j], int(lw_arr[j]))

        # Bright head dot — radius and a white flash scale with beat
        hx, hy = raw[-1]
        for sym in range(self.N_SYM):
            a      = sym / self.N_SYM * math.tau
            ca, sa = math.cos(a), math.sin(a)
            sx     = int(cx + hx * ca - hy * sa)
            sy_    = int(cy + hx * sa + hy * ca)
            r      = max(3, int(7 + beat * 22))
            pygame.draw.circle(surf,
                               hsl((self.hue + sym * 0.33) % 1.0, l=0.88), (sx, sy_), r)
            pygame.draw.circle(surf, (255, 255, 255), (sx, sy_), max(1, r // 3))
            # Extra glow halo on strong beats
            if beat > 0.5:
                pygame.draw.circle(surf,
                                   hsl((self.hue + sym * 0.33 + 0.5) % 1.0,
                                       l=0.45 + beat * 0.25),
                                   (sx, sy_), max(2, int(r * 1.8)), 2)


class Yantra:
    """Psychedelic sacred-geometry mandala for psytrance.

    Six concentric polygon rings (triangle → octagon) alternate rotation
    direction, each driven by its own frequency band.  Web lines connect
    adjacent ring vertices. Neon spokes radiate from the centre. Beat
    triggers spring-physics pulses that push every ring outward then snap
    it back — timed to the kick drum of fast BPM tracks.
    """

    N_RINGS  = 6    # triangle(3) → octagon(8)
    N_SPOKES = 24   # radial lines from centre

    def __init__(self):
        self.hue  = 0.0
        self.time = 0.0
        signs = [1, -1, 1, -1, 1, -1]
        # per-ring state: rotation angle, velocity, pulse offset, pulse velocity
        self.rot  = [0.0] * self.N_RINGS
        self.rvel = [signs[i] * (0.004 + i * 0.0018) for i in range(self.N_RINGS)]
        self.poff = [0.0] * self.N_RINGS
        self.pvel = [0.0] * self.N_RINGS

    def _ring_verts(self, i, r, cx, cy):
        """Polygon vertices for ring i at radius r."""
        n   = 3 + i
        rot = self.rot[i]
        return [(cx + math.cos(v / n * math.tau + rot) * r,
                 cy + math.sin(v / n * math.tau + rot) * r)
                for v in range(n)]

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue  += 0.005
        self.time += 0.02 + beat * 0.04

        cx, cy  = WIDTH // 2, HEIGHT // 2
        max_r   = min(WIDTH, HEIGHT) * 0.46

        bass = float(np.mean(fft[:6]))
        mid  = float(np.mean(fft[6:30]))
        high = float(np.mean(fft[30:]))
        bands = [bass, (bass + mid) * 0.5, mid,
                 (mid + high) * 0.5, high, (bass + high) * 0.5]

        # ── Physics update ────────────────────────────────────────────────────
        for i in range(self.N_RINGS):
            e = min(bands[i], 1.0)
            # Spring: beat kick pushes out, restore force pulls back
            self.pvel[i] += beat * (0.24 + e * 0.12)
            self.pvel[i] += -self.poff[i] * 0.22
            self.pvel[i] *= 0.65
            self.poff[i] += self.pvel[i]
            # Rotation speed driven by band energy
            self.rot[i]  += self.rvel[i] * (1.0 + e * 2.8 + bass * 1.2)

        # ── Collect all ring vertex lists ─────────────────────────────────────
        all_verts = []
        for i in range(self.N_RINGS):
            base_r = max_r * (0.13 + i / (self.N_RINGS - 1) * 0.83)
            r      = base_r * (1.0 + self.poff[i] * 0.38)
            all_verts.append(self._ring_verts(i, r, cx, cy))

        # ── Draw web lines between adjacent rings (inner first) ───────────────
        for i in range(self.N_RINGS - 1):
            v_out = all_verts[i + 1]
            v_in  = all_verts[i]
            n_out = len(v_out)
            n_in  = len(v_in)
            e     = min(bands[i], 1.0)
            h     = (self.hue + i / self.N_RINGS * 0.5) % 1.0
            for k, (ox, oy) in enumerate(v_out):
                nearest = round(k / n_out * n_in) % n_in
                ix, iy  = v_in[nearest]
                pygame.draw.line(surf,
                                 hsl(h, l=0.18 + e * 0.28),
                                 (int(ox), int(oy)), (int(ix), int(iy)), 1)

        # ── Draw polygon rings (outer → inner so inner overdraw outer) ────────
        for i in range(self.N_RINGS - 1, -1, -1):
            e     = min(bands[i], 1.0)
            h     = (self.hue + i / self.N_RINGS * 0.55) % 1.0
            bright = 0.42 + e * 0.44
            lw    = max(1, int(1 + e * 2.5 + beat * 1.5))
            ipts  = [(int(x), int(y)) for x, y in all_verts[i]]
            pygame.draw.polygon(surf, hsl(h, l=bright), ipts, lw)
            # Star: connect every vertex to the one two steps ahead
            n = len(ipts)
            if n >= 5:
                step = 2
                for k in range(n):
                    pygame.draw.line(surf, hsl(h, l=bright * 0.6),
                                     ipts[k], ipts[(k + step) % n], 1)

        # ── Radial spokes from centre ─────────────────────────────────────────
        outer_r = max_r * (1.02 + beat * 0.18)
        for s in range(self.N_SPOKES):
            a   = s / self.N_SPOKES * math.tau + self.time * 0.22
            # Wiggle spokes with audio-driven sine
            a  += math.sin(self.time * 2.4 + s * 0.85) * (0.05 + mid * 0.10)
            x2  = int(cx + math.cos(a) * outer_r)
            y2  = int(cy + math.sin(a) * outer_r)
            h   = (self.hue + s / self.N_SPOKES * 0.35 + high * 0.2) % 1.0
            lw  = max(1, int(beat * 2.5))
            if lw:
                pygame.draw.line(surf,
                                 hsl(h, l=0.18 + beat * 0.50 + high * 0.18),
                                 (cx, cy), (x2, y2), lw)

        # ── Central bright circle that pulses with bass ───────────────────────
        cr = max(2, int(8 + bass * 28 + beat * 20))
        pygame.draw.circle(surf, hsl(self.hue, l=0.55 + beat * 0.35), (cx, cy), cr)
        pygame.draw.circle(surf, hsl((self.hue + 0.5) % 1.0, l=0.75),
                           (cx, cy), max(1, cr // 3))


class Bubbles:
    """Translucent rising bubbles — fills the full screen; size and spawn rate driven by bass."""

    MAX = 700

    def __init__(self):
        self.hue   = 0.0
        self.pulse = 0.0   # shared spring — all bubbles swell together on beat
        self.pvel  = 0.0
        # Pre-populate bubbles scattered across the whole screen so it fills instantly
        self.pool = [self._make(y=random.uniform(0, HEIGHT)) for _ in range(400)]
        self._surf_cache: dict = {}

    @staticmethod
    def _make(y=None):
        r = random.uniform(8, 45)
        return {
            "x":      random.uniform(WIDTH * 0.02, WIDTH * 0.98),
            "y":      float(HEIGHT + r) if y is None else y,
            "r":      r,
            "vx":     random.gauss(0, 0.4),
            "vy":    -random.uniform(1.0, 3.2),
            "hue":    random.uniform(0, 1.0),
            "wobble": random.uniform(0.025, 0.07),
            "phase":  random.uniform(0, math.tau),
        }

    def _get_bsurf(self, size):
        """Return a cleared SRCALPHA surface of (size×size), reusing cached instances."""
        s = self._surf_cache.get(size)
        if s is None:
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            self._surf_cache[size] = s
        s.fill((0, 0, 0, 0))
        return s

    def _spawn(self, beat, bass):
        for _ in range(int(2 + beat * 12 + bass * 6)):
            b = self._make()
            b["vy"]  *= (1 + beat * 0.8)
            b["r"]   *= (1 + bass * 1.2)
            b["hue"]  = (self.hue + random.uniform(0, 0.35)) % 1.0
            self.pool.append(b)

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue += 0.005
        bass = float(np.mean(fft[:8]))
        mid  = float(np.mean(fft[6:30]))

        # Global beat spring — kick hard, snap back fast
        self.pvel += beat * 0.75
        self.pvel += -self.pulse * 0.35
        self.pvel *= 0.52
        self.pulse += self.pvel

        self._spawn(beat, bass)

        alive = []
        for b in self.pool:
            b["x"]   += b["vx"] + math.sin(tick * b["wobble"] + b["phase"]) * 0.9
            b["y"]   += b["vy"]
            # Hue drifts per bubble for rainbow cycling
            b["hue"]  = (b["hue"] + 0.004) % 1.0
            if b["y"] + b["r"] < 0:
                continue

            life  = max(0.0, min(1.0, b["y"] / HEIGHT))
            # All bubbles swell together on beat via shared spring
            r     = max(2, int(b["r"] * (1 + self.pulse * 0.90 + mid * 0.15)))
            pad   = r + 14
            alpha = int(life * 160)
            bsurf = self._get_bsurf(pad * 2)
            cc = pad  # local centre

            # Multi-layer glow halos (outermost to innermost)
            for g, (g_exp, g_l, g_a_mul) in enumerate(
                    [(1.55, 0.40, 0.18), (1.28, 0.52, 0.35), (1.10, 0.65, 0.60)]):
                gr    = max(1, int(r * g_exp))
                galpha = int(alpha * g_a_mul)
                pygame.draw.circle(bsurf, (*hsl(b["hue"], l=g_l), galpha),
                                   (cc, cc), gr, max(2, gr // 5))

            # Main neon rim
            pygame.draw.circle(bsurf, (*hsl(b["hue"], l=0.78), alpha),
                               (cc, cc), r, 2)
            # Filled translucent core
            pygame.draw.circle(bsurf,
                               (*hsl((b["hue"] + 0.5) % 1.0, l=0.55),
                                int(alpha * 0.22)),
                               (cc, cc), max(1, r - 2))
            # Specular highlight
            hr = max(1, r // 3)
            pygame.draw.circle(bsurf, (255, 255, 255, int(alpha * 0.55)),
                               (cc - r // 3, cc - r // 3), hr)
            # Beat flash: extra bright ring
            if beat > 0.5:
                flash_r = max(1, int(r * 1.4))
                pygame.draw.circle(bsurf,
                                   (*hsl((b["hue"] + 0.25) % 1.0, l=0.88),
                                    int(alpha * beat * 0.4)),
                                   (cc, cc), flash_r, 2)

            surf.blit(bsurf, (int(b["x"]) - cc, int(b["y"]) - cc))
            alive.append(b)

        self.pool = alive[-self.MAX:]



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
        self.hue += 0.003 + beat * 0.015
        sums = np.add.reduceat(fft[:self.edges[-1]], self.edges[:-1])
        row  = sums / np.maximum(np.diff(self.edges), 1).astype(float)
        row  = row[:self.cols]
        row /= (row.max() + 1e-6)
        self.buf.appendleft(row)

        bw    = max(1, WIDTH  // self.cols)
        bh    = max(4, HEIGHT // self.ROWS)
        flash = beat * 0.35   # brightness bonus on kick

        for ri, r in enumerate(self.buf):
            y = ri * bh
            if y > HEIGHT:
                break
            age     = ri / max(len(self.buf), 1)
            # Newest rows get the beat flash; it decays with age
            row_boost = flash * max(0.0, 1.0 - age * 6)
            for ci, e in enumerate(r):
                if e < 0.02:
                    continue
                x   = ci * bw
                hue = (self.hue + ci / self.cols * 0.75) % 1.0
                lit = (1 - age * 0.7) * (0.2 + e * 0.8) + row_boost
                pygame.draw.rect(surf, hsl(hue, l=min(lit, 0.95)),
                                 (x, y, bw - 1, bh - 1))


# ── Mode registry ─────────────────────────────────────────────────────────────

MODES = [
    ("Yantra",      Yantra),      # 1
    ("Cube",        Cube),        # 2
    ("Plasma",      Plasma),      # 3
    ("Tunnel",      Tunnel),      # 4
    ("Lissajous",   Lissajous),   # 5
    ("Nova",        Nova),         # 6
    ("Spiral",      Spiral),      # 7
    ("Bubbles",     Bubbles),     # 8
    ("Spectrum",    Bars),        # 9
    ("Waterfall",   GlowSquares), # 0
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
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
    pygame.display.set_caption(f"psysuals v{__version__}")
    WIDTH, HEIGHT = screen.get_size()
    clock  = pygame.time.Clock()
    font   = pygame.font.SysFont("monospace", 16)

    devices    = _input_devices()
    active_dev = None          # None → sounddevice default
    stream     = sd.InputStream(
        samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE,
        channels=CHANNELS, device=active_dev, callback=_audio_cb)
    stream.start()

    mode_idx       = 0
    name, VisCls   = MODES[mode_idx]
    vis            = VisCls()
    fullscreen     = True
    tick           = 0
    energy_hist    = deque(maxlen=30)
    energy_sum     = 0.0
    dev_name_cache = {None: "default"}
    picking        = False      # device-picker overlay open?
    pick_sel       = 0          # highlighted row in picker
    show_hud       = True       # H toggles HUD visibility

    def make_fade():
        s = pygame.Surface((WIDTH, HEIGHT))
        s.set_alpha(28)
        s.fill((0, 0, 0))
        return s

    fade = make_fade()

    hint = ("  SPACE/click: next mode  |  1-{n}: pick mode  "
            "|  D: device  |  F: fullscreen  |  H: hide HUD  |  Q: quit").format(n=len(MODES))

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
                    elif event.key == pygame.K_h:
                        show_hud = not show_hud
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
                    else:
                        idx = event.key - pygame.K_1
                        if 0 <= idx < len(MODES):
                            mode_idx = idx
                            name, VisCls = MODES[mode_idx]; vis = VisCls()

            elif event.type == pygame.MOUSEBUTTONDOWN and not picking:
                mode_idx = (mode_idx + 1) % len(MODES)
                name, VisCls = MODES[mode_idx]; vis = VisCls()

        waveform, fft, raw_beat = get_audio()
        if len(energy_hist) == energy_hist.maxlen:
            energy_sum -= energy_hist[0]
        energy_hist.append(raw_beat)
        energy_sum += raw_beat
        avg  = energy_sum / len(energy_hist) if energy_hist else 1e-6
        beat = max(0.0, min(raw_beat / (avg + 1e-6) - 1.0, 3.0))

        screen.blit(fade, (0, 0))
        vis.draw(screen, waveform, fft, beat, tick)

        # HUD
        if show_hud:
            if active_dev not in dev_name_cache:
                dev_name_cache[active_dev] = sd.query_devices(active_dev)["name"]
            dev_name = dev_name_cache[active_dev]
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
