"""
effects/plasma_gl.py — Plasma rendered as a GLSL fragment shader.

Drop-in replacement for Plasma with the same interface:
    draw(surf, waveform, fft, beat, tick)

Desktop GL path:
    Pass a GLRenderer at construction time.  draw() sets uniforms and
    renders a fullscreen quad; *surf* is ignored (OpenGL owns the window).

CPU fallback:
    If no renderer is provided (or moderngl is absent), falls back to the
    original numpy implementation so the file works everywhere.

Android / draw_frame() path:
    effect.draw_frame(w, h, waveform, fft, beat, tick, renderer)
    renders to an offscreen FBO and returns an (H, W, 4) RGBA uint8 array —
    no pygame required.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

try:
    import moderngl
    HAS_MODERNGL = True
except ImportError:
    HAS_MODERNGL = False

if TYPE_CHECKING:
    from gl_renderer import GLRenderer

import config
from .base import Effect

# ── Shaders ───────────────────────────────────────────────────────────────────

_VERT = """
#version 330
in vec2 in_vert;
out vec2 v_uv;
void main() {
    v_uv = in_vert * 0.5 + 0.5;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

_FRAG = """
#version 330
in  vec2  v_uv;
out vec4  fragColor;

uniform float u_time;
uniform float u_hue;
uniform float u_bass;
uniform float u_mid;
uniform float u_beat;
uniform float u_high;

#define PI 3.14159265358979

// Vectorised HSL (s=1) → RGB, matching the numpy _hsl_arr implementation.
vec3 hsl2rgb(float h, float l) {
    float c  = 1.0 - abs(2.0 * l - 1.0);
    float h6 = h * 6.0;
    float x  = c * (1.0 - abs(mod(h6, 2.0) - 1.0));
    float m  = l - c * 0.5;
    int   i  = int(h6) % 6;
    vec3  rgb;
    if      (i == 0) rgb = vec3(c, x, 0);
    else if (i == 1) rgb = vec3(x, c, 0);
    else if (i == 2) rgb = vec3(0, c, x);
    else if (i == 3) rgb = vec3(0, x, c);
    else if (i == 4) rgb = vec3(x, 0, c);
    else             rgb = vec3(c, 0, x);
    return clamp(rgb + m, 0.0, 1.0);
}

void main() {
    // Map UV [0,1]² → plasma coordinate space [-pi*2.5, pi*2.5]²
    vec2  p  = (v_uv * 2.0 - 1.0) * PI * 2.5;
    float r  = length(p);
    float fm = 1.0 + u_mid * 0.7;
    float t  = u_time;

    // Four-wave interference — matches numpy Plasma exactly
    float v = (sin(p.x * fm          +  t       ) +
               sin(p.y * fm * 0.8    +  t * 1.4 ) +
               sin((p.x * 0.6 + p.y * 0.8) * fm + t * 0.9) +
               sin(r    * fm * 0.5   -  t * 1.2 )) * 0.25;

    float h = mod(v * 0.55 + 0.5 + u_hue + u_bass * 0.35, 1.0);
    float l = clamp(0.28 + v * 0.22 + u_beat * 0.22 + u_high * 0.08, 0.0, 0.95);

    fragColor = vec4(hsl2rgb(h, l), 1.0);
}
"""

# ── Helper (CPU fallback) ─────────────────────────────────────────────────────

def _hsl_arr(h: np.ndarray, l: np.ndarray) -> np.ndarray:
    """Vectorised HSL (s=1) → uint8 RGB array — same as original Plasma."""
    c  = 1.0 - np.abs(2.0 * l - 1.0)
    h6 = h * 6.0
    x  = c * (1.0 - np.abs(h6 % 2.0 - 1.0))
    m  = l - c / 2.0
    i  = h6.astype(int) % 6
    z  = np.zeros_like(h)
    r  = np.select([i==0,i==1,i==2,i==3,i==4,i==5], [c,x,z,z,x,c]) + m
    g  = np.select([i==0,i==1,i==2,i==3,i==4,i==5], [x,c,c,x,z,z]) + m
    b  = np.select([i==0,i==1,i==2,i==3,i==4,i==5], [z,z,x,c,c,x]) + m
    u8 = lambda a: np.clip(a * 255, 0, 255).astype(np.uint8)
    return np.stack([u8(r), u8(g), u8(b)], axis=2)


# ── Effect class ──────────────────────────────────────────────────────────────

class PlasmaGL(Effect):
    """
    GPU-accelerated Plasma effect.

    Identical audio math to the original Plasma; the pixel evaluation moves
    from a numpy CPU loop to a GLSL fragment shader executed on the GPU.
    """
    IS_GL = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._hue      = 0.0
        self._time     = 0.0
        self._prog     = None   # compiled lazily on first draw
        self._vao      = None
        self._fbo_cache: dict = {}  # (w,h) → Framebuffer, for draw_frame reuse

        # CPU fallback grids — built only when pygame is available
        if HAS_PYGAME:
            rw = max(1, config.WIDTH  // 4)
            rh = max(1, config.HEIGHT // 4)
            self._fallback_surf = pygame.Surface((rw, rh))
            xs = np.linspace(-math.pi * 2.5, math.pi * 2.5, rw)
            ys = np.linspace(-math.pi * 2.5, math.pi * 2.5, rh)
            X, Y = np.meshgrid(xs, ys)
            self._X = X; self._Y = Y
            self._R = np.sqrt(X ** 2 + Y ** 2)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _ensure_shader(self, renderer: "GLRenderer") -> None:
        """Lazily compile the fragment shader on first use."""
        if self._prog is None:
            self.renderer = renderer
            self._prog, self._vao = renderer.program(_VERT, _FRAG)

    def _advance(self, fft: np.ndarray, beat: float) -> tuple[float, float, float]:
        """Tick time forward; return (bass, mid, high) scalar energies."""
        bass = float(np.mean(fft[:6]))
        mid  = float(np.mean(fft[6:30]))
        high = float(np.mean(fft[30:]))
        self._hue  += 0.005
        self._time += 0.018 + bass * 0.09 + beat * 0.14
        return bass, mid, high

    def _set_uniforms(self, bass: float, mid: float, high: float, beat: float) -> None:
        self._prog["u_time"] = self._time
        self._prog["u_hue"]  = self._hue
        self._prog["u_bass"] = bass
        self._prog["u_mid"]  = mid
        self._prog["u_beat"] = float(beat)
        self._prog["u_high"] = high

    # ── Desktop draw — same signature as all other effects ────────────────────

    def draw(self, surf, waveform: np.ndarray, fft: np.ndarray,
             beat: float, tick: int) -> None:
        """
        Render one frame.
        GL path:  *surf* is ignored; output goes to the active GL framebuffer.
        CPU path: output blitted to *surf* (pygame.Surface).
        """
        bass, mid, high = self._advance(fft, beat)

        if self.renderer is not None and HAS_MODERNGL:
            self._ensure_shader(self.renderer)
            self._set_uniforms(bass, mid, high, beat)
            self.renderer.render(self._vao)
        elif HAS_PYGAME and surf is not None:
            self._draw_numpy(surf, bass, mid, high, beat)

    # ── CPU numpy fallback ────────────────────────────────────────────────────

    def _draw_numpy(self, surf, bass: float, mid: float,
                    high: float, beat: float) -> None:
        fm = 1.0 + mid * 0.7
        t  = self._time
        v  = (np.sin(self._X * fm              +  t       ) +
              np.sin(self._Y * fm * 0.8        +  t * 1.4 ) +
              np.sin((self._X*0.6 + self._Y*0.8)*fm + t*0.9) +
              np.sin(self._R * fm * 0.5        -  t * 1.2 )) * 0.25
        h = (v * 0.55 + 0.5 + self._hue + bass * 0.35) % 1.0
        l = np.clip(0.28 + v * 0.22 + beat * 0.22 + high * 0.08, 0.0, 0.95)
        rgb = _hsl_arr(h, l)
        pygame.surfarray.blit_array(self._fallback_surf, rgb.transpose(1, 0, 2))
        surf.blit(pygame.transform.scale(
            self._fallback_surf, (config.WIDTH, config.HEIGHT)), (0, 0))

    # ── Android / offscreen API ───────────────────────────────────────────────

    def draw_frame(self, width: int, height: int,
                   waveform: np.ndarray, fft: np.ndarray,
                   beat: float, tick: int,
                   renderer: "GLRenderer | None" = None) -> np.ndarray:
        """
        Render one frame offscreen → (H, W, 4) RGBA uint8 numpy array.

        No pygame required.  On Android, the host creates the moderngl context
        (via EGL) and passes it in as renderer.

        The returned array is a fresh copy safe to hand to Kotlin/Chaquopy.
        """
        r = renderer or self.renderer
        if r is None or not HAS_MODERNGL:
            raise RuntimeError("A GLRenderer is required for draw_frame()")

        bass, mid, high = self._advance(fft, beat)
        self._ensure_shader(r)
        self._set_uniforms(bass, mid, high, beat)

        # Reuse cached FBO for this resolution
        key = (width, height)
        if key not in self._fbo_cache:
            self._fbo_cache[key] = r.offscreen(width, height)
        fbo = self._fbo_cache[key]

        r.render(self._vao, fbo)
        return r.read_pixels(fbo)
