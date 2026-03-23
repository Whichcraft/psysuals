#!/usr/bin/env python3
"""
Music Visualizer — Real-time audio → visuals.

Controls:
  SPACE / click   Switch to next mode
  1-8             Jump to a specific mode
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
        self.hue = 0.0

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

    def _project(self, v, fov=420):
        z = v[2] + 4.5
        return (int(v[0] * fov / z + WIDTH // 2),
                int(v[1] * fov / z + HEIGHT // 2))

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue += 0.004
        bass = min(float(np.mean(fft[:5])),   1.0)
        mid  = min(float(np.mean(fft[5:25])), 1.0)
        high = min(float(np.mean(fft[25:])),  1.0)
        self.rx += 0.005 + mid  * 0.055
        self.ry += 0.007 + bass * 0.075
        self.rz += 0.003 + high * 0.040

        R = self._Rx(self.rx) @ self._Ry(self.ry) @ self._Rz(self.rz)

        for scale, hue_off in ((1.0 + beat * 0.8, 0.0), (0.5 + beat * 0.3, 0.5)):
            verts = (R @ (self.VERTS * scale).T).T
            proj  = [self._project(v) for v in verts]
            for ei, (a, b) in enumerate(self.EDGES):
                h     = (self.hue + hue_off + ei / len(self.EDGES)) % 1.0
                lw    = max(1, int(2 + beat * 3)) if scale > 0.6 else 1
                color = hsl(h, l=0.45 + beat * 0.3)
                pygame.draw.line(surf, color, proj[a], proj[b], lw)


class Bars:
    """Classic spectrum bars with peak markers and a waveform overlay."""

    N = 80

    def __init__(self):
        self.hue   = 0.0
        self.peaks = np.zeros(self.N)

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue += 0.003
        bar_w   = WIDTH // self.N
        indices = np.linspace(0, len(fft) // 3, self.N + 1, dtype=int)
        heights = np.array([np.mean(fft[indices[i]:indices[i+1]+1])
                            for i in range(self.N)])
        heights /= (heights.max() + 1e-6)
        self.peaks = np.maximum(self.peaks * 0.97, heights)

        for i, h in enumerate(heights):
            bar_h = int(h * HEIGHT * 0.82)
            peak  = int(self.peaks[i] * HEIGHT * 0.82)
            x     = i * bar_w
            hue   = (self.hue + i / self.N) % 1.0
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
    """Receding hexagonal rings — speed and glow driven by bass."""

    def __init__(self):
        self.hue   = 0.0
        self.depth = 0.0

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue   += 0.005
        self.depth += 0.018 + beat * 0.09
        cx, cy = WIDTH // 2, HEIGHT // 2
        rings  = 22

        for i in range(rings, 0, -1):
            t      = i / rings
            d      = (t + self.depth) % 1.0
            fi     = min(int(d * len(fft)), len(fft) - 1)
            radius = (1 - d) * max(WIDTH, HEIGHT) * 0.72 + fft[fi] * 90
            h      = (self.hue + d * 0.4) % 1.0
            color  = hsl(h, l=0.18 + d * 0.6 + fft[fi] * 0.3)
            sides  = 6
            pts    = [
                (int(cx + radius * math.cos(k / sides * math.tau + self.depth * 0.5)),
                 int(cy + radius * math.sin(k / sides * math.tau + self.depth * 0.5)))
                for k in range(sides)
            ]
            if radius > 4:
                pygame.draw.polygon(surf, color, pts, max(1, int(2 + beat * 3)))


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


# ── Mode registry ─────────────────────────────────────────────────────────────

MODES = [
    ("Spiral",      Spiral),
    ("Tentacles",   Tentacles),
    ("Cube",        Cube),
    ("Spectrum",    Bars),
    ("Particles",   Particles),
    ("Tunnel",      Tunnel),
    ("Lissajous",   Lissajous),
    ("Mandelbrot",  Mandelbrot),
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
