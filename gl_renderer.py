"""
gl_renderer.py — thin moderngl wrapper for psysuals.

Desktop path:
    Call GLRenderer(w, h) *after* pygame.display.set_mode(..., OPENGL | DOUBLEBUF).
    moderngl binds to pygame's active GL context automatically.

Android / headless path:
    Pass an externally-created moderngl.Context as ctx=.
    Use offscreen() + read_pixels() to get RGBA numpy arrays without a display.
"""

from __future__ import annotations

import numpy as np

try:
    import moderngl
    HAS_MODERNGL = True
except ImportError:
    HAS_MODERNGL = False


class GLRenderer:
    """
    Minimal moderngl context wrapper: compiles shader programs,
    owns a shared fullscreen-quad VBO, and manages offscreen FBOs.
    """

    # Two triangles as a strip covering clip space [-1,1]²
    _QUAD = np.array([-1, -1,  1, -1,  -1, 1,  1, 1], dtype="f4")

    def __init__(self, width: int, height: int, ctx: "moderngl.Context | None" = None):
        if not HAS_MODERNGL:
            raise RuntimeError("moderngl not installed — pip install moderngl")
        self.width  = width
        self.height = height
        self.ctx    = ctx if ctx is not None else moderngl.create_context()
        self._vbo   = self.ctx.buffer(self._QUAD.tobytes())

    # ── Shader helpers ────────────────────────────────────────────────────────

    def program(self, vert: str, frag: str) -> tuple:
        """
        Compile *vert* + *frag* GLSL sources into a fullscreen-quad program.
        Returns (Program, VAO) ready to pass to render().
        The vertex shader must declare:  in vec2 in_vert;
        """
        prog = self.ctx.program(vertex_shader=vert, fragment_shader=frag)
        vao  = self.ctx.vertex_array(prog, [(self._vbo, "2f", "in_vert")])
        return prog, vao

    # ── Render helpers ────────────────────────────────────────────────────────

    def render(self, vao, fbo=None) -> None:
        """
        Draw a fullscreen quad.
        *fbo*=None → renders to the pygame/GLFW window (screen framebuffer).
        *fbo*=<Framebuffer> → renders offscreen.
        """
        target = fbo if fbo is not None else self.ctx.screen
        target.use()
        self.ctx.clear(0.0, 0.0, 0.0, 1.0)
        vao.render(moderngl.TRIANGLE_STRIP)

    # ── Offscreen / Android ───────────────────────────────────────────────────

    def offscreen(self, width: int = 0, height: int = 0) -> "moderngl.Framebuffer":
        """Return a fresh RGBA framebuffer (allocates each call — cache if hot)."""
        w = width  or self.width
        h = height or self.height
        return self.ctx.framebuffer(
            color_attachments=[self.ctx.texture((w, h), 4)]
        )

    def read_pixels(self, fbo: "moderngl.Framebuffer") -> np.ndarray:
        """
        Read *fbo* → (H, W, 4) RGBA uint8 numpy array.
        Flips Y because OpenGL's origin is bottom-left.
        """
        raw = fbo.read(components=4)
        arr = np.frombuffer(raw, dtype=np.uint8).reshape(fbo.height, fbo.width, 4)
        return arr[::-1].copy()
