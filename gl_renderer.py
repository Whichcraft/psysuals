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
        self._feedback_tex: moderngl.Texture | None = None
        self._feedback_prog: moderngl.Program | None = None
        self._feedback_vao: moderngl.VertexArray | None = None
        self._offscreen_cache: dict[tuple[int, int], tuple[moderngl.Texture, moderngl.Framebuffer]] = {}

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
        #version 330 core
        in vec2 in_vert;
        out vec2 v_uv;
        void main() {
            v_uv = in_vert * 0.5 + 0.5;
            v_uv.y = 1.0 - v_uv.y;
            gl_Position = vec4(in_vert, 0.0, 1.0);
        }
        """
        frag = """
        #version 330 core
        uniform sampler2D u_tex;
        in vec2 v_uv;
        out vec4 fragColor;
        void main() {
            fragColor = texture(u_tex, v_uv);
        }
        """
        return self.program(vert, frag)

    def feedback_program(self) -> tuple:
        """Return a texture feedback shader with zoom/rotation sampling."""
        vert = """
        #version 330 core
        in vec2 in_vert;
        out vec2 v_uv;
        void main() {
            v_uv = in_vert * 0.5 + 0.5;
            gl_Position = vec4(in_vert, 0.0, 1.0);
        }
        """
        frag = """
        #version 330 core
        uniform sampler2D u_tex;
        uniform float u_zoom;
        uniform float u_rot;
        uniform vec2 u_center;
        in vec2 v_uv;
        out vec4 fragColor;
        void main() {
            vec2 p = v_uv - u_center;
            float c = cos(u_rot);
            float s = sin(u_rot);
            p = mat2(c, -s, s, c) * (p / max(u_zoom, 0.0001));
            vec2 uv = p + u_center;
            if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
                fragColor = vec4(0.0);
            } else {
                fragColor = texture(u_tex, uv);
            }
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
            
        if hasattr(pygame.image, "to_string"):
            rgba = pygame.image.to_string(surface, "RGBA")
        else:
            rgba = pygame.image.tostring(surface, "RGBA")
        self._blit_tex.write(rgba)
        self._blit_tex.use(0)
        self._blit_prog["u_tex"] = 0
        
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        self.render(self._blit_vao)

    def surface_texture(self, surface: "pygame.Surface") -> "moderngl.Texture":
        """Upload a pygame surface to a reusable texture."""
        size = surface.get_size()
        if self._feedback_tex is None or self._feedback_tex.size != size:
            if self._feedback_tex:
                self._feedback_tex.release()
            self._feedback_tex = self.ctx.texture(size, 4)
            self._feedback_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self._feedback_tex.repeat_x = False
            self._feedback_tex.repeat_y = False

        if hasattr(pygame.image, "to_string"):
            rgba = pygame.image.to_string(surface, "RGBA")
        else:
            rgba = pygame.image.tostring(surface, "RGBA")
        self._feedback_tex.write(rgba)
        self._feedback_tex.use(0)
        return self._feedback_tex

    def feedback_transform(self, surface: "pygame.Surface", fbo, zoom: float, rot: float) -> None:
        """Render *surface* through the feedback shader into *fbo*."""
        if self._feedback_prog is None:
            self._feedback_prog, self._feedback_vao = self.feedback_program()

        tex = self.surface_texture(surface)
        fbo.use()
        fbo.clear(0.0, 0.0, 0.0, 0.0)
        self.ctx.disable(moderngl.BLEND)
        tex.use(0)
        self._feedback_prog["u_tex"] = 0
        self._feedback_prog["u_zoom"] = float(zoom)
        self._feedback_prog["u_rot"] = float(rot)
        self._feedback_prog["u_center"] = (0.5, 0.5)
        self.render(self._feedback_vao, fbo)

    def release(self):
        """Release all GL resources."""
        if self._blit_tex:
            self._blit_tex.release()
        if self._feedback_tex:
            self._feedback_tex.release()
        self._vbo.release()
        for prog, vao in list(self._program_cache.values()):
            vao.release()
            prog.release()
        if self._blit_vao:
            self._blit_vao.release()
        if self._blit_prog:
            self._blit_prog.release()
        if self._feedback_vao:
            self._feedback_vao.release()
        if self._feedback_prog:
            self._feedback_prog.release()
        for tex, fbo in self._offscreen_cache.values():
            fbo.release()
            tex.release()
        self._offscreen_cache.clear()

    # ── Offscreen / Android ───────────────────────────────────────────────────

    def offscreen(self, width: int = 0, height: int = 0) -> "moderngl.Framebuffer":
        """Return a cached RGBA framebuffer for the requested size."""
        w = width  or self.width
        h = height or self.height
        key = (w, h)
        if key not in self._offscreen_cache:
            tex = self.ctx.texture((w, h), 4)
            fbo = self.ctx.framebuffer(color_attachments=[tex])
            self._offscreen_cache[key] = (tex, fbo)
        return self._offscreen_cache[key][1]

    def read_pixels(self, fbo: "moderngl.Framebuffer") -> np.ndarray:
        """
        Read *fbo* → (H, W, 4) RGBA uint8 numpy array.
        Flips Y because OpenGL's origin is bottom-left.
        """
        raw = fbo.read(components=4)
        arr = np.frombuffer(raw, dtype=np.uint8).reshape(fbo.height, fbo.width, 4)
        return arr[::-1].copy()
