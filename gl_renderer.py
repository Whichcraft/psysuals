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

from pathlib import Path

import numpy as np
import pygame

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
    _SHADER_DIR = Path(__file__).resolve().parent / "effects" / "shaders"

    def __init__(self, width: int, height: int, ctx: "moderngl.Context | None" = None):
        if not HAS_MODERNGL:
            raise RuntimeError("moderngl not installed — pip install moderngl")
        self.width  = width
        self.height = height
        self.ctx    = ctx if ctx is not None else moderngl.create_context()
        self._vbo   = self.ctx.buffer(self._QUAD.tobytes())
        self._program_cache: dict[tuple[str, str], tuple] = {}
        self._blit_tex: moderngl.Texture | None = None
        self._blit_prog: moderngl.Program | None = None
        self._blit_vao: moderngl.VertexArray | None = None

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

    def shader_asset(self, name: str) -> str:
        """Load a tracked GLSL asset from effects/shaders/."""
        path = self._SHADER_DIR / name
        return path.read_text(encoding="utf-8")

    def asset_program(self, vert_name: str, frag_name: str) -> tuple:
        """Compile and cache a shader program from tracked asset files."""
        key = (vert_name, frag_name)
        if key not in self._program_cache:
            self._program_cache[key] = self.program(
                self.shader_asset(vert_name),
                self.shader_asset(frag_name),
            )
        return self._program_cache[key]

    def line_program(self) -> tuple:
        """Return the shared line shader pair from effects/shaders/."""
        return self.asset_program("line.vert", "line.frag")

    def rect_program(self) -> tuple:
        """Return the shared rect shader pair from effects/shaders/."""
        return self.asset_program("rect.vert", "rect.frag")

    def blit_program(self) -> tuple:
        """Return a simple texture-blitting shader program."""
        vert = """
        #version 330
        in vec2 in_vert;
        out vec2 v_uv;
        void main() {
            v_uv = in_vert * 0.5 + 0.5;
            v_uv.y = 1.0 - v_uv.y;
            gl_Position = vec4(in_vert, 0.0, 1.0);
        }
        """
        frag = """
        #version 330
        uniform sampler2D u_tex;
        in vec2 v_uv;
        out vec4 fragColor;
        void main() {
            fragColor = texture(u_tex, v_uv);
        }
        """
        return self.program(vert, frag)

    # ── Render helpers ────────────────────────────────────────────────────────

    def render(self, vao, fbo=None) -> None:
        """
        Draw a fullscreen quad.
        *fbo*=None → renders to the pygame/GLFW window (screen framebuffer).
        *fbo*=<Framebuffer> → renders offscreen.
        """
        target = fbo if fbo is not None else self.ctx.screen
        target.use()
        # self.ctx.clear(0.0, 0.0, 0.0, 1.0) # Removed clear to allow layering
        vao.render(moderngl.TRIANGLE_STRIP)

    def blit(self, surface: "pygame.Surface") -> None:
        """Upload *surface* to a texture and render it as a fullscreen quad."""
        if self._blit_prog is None:
            self._blit_prog, self._blit_vao = self.blit_program()
        
        size = surface.get_size()
        if self._blit_tex is None or self._blit_tex.size != size:
            if self._blit_tex:
                self._blit_tex.release()
            self._blit_tex = self.ctx.texture(size, 4)
            
        rgba = pygame.image.tostring(surface, "RGBA")
        self._blit_tex.write(rgba)
        self._blit_tex.use(0)
        self._blit_prog["u_tex"] = 0
        
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        self.render(self._blit_vao)

    def release(self):
        """Release all GL resources."""
        if self._blit_tex:
            self._blit_tex.release()
        self._vbo.release()
        for prog, vao in self._program_cache.values():
            prog.release()
            # VAO is implicitly released when prog or buffers are? 
            # Actually, VAO should be released too.
            vao.release()
        if self._blit_vao:
            self._blit_vao.release()
        if self._blit_prog:
            self._blit_prog.release()

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
