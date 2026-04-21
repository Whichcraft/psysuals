from __future__ import annotations
import os
import sys
import subprocess
import re as _re
import pygame
import config
from gl_renderer import GLRenderer, HAS_MODERNGL

class DisplayManager:
    def __init__(self, args):
        self.args = args
        self._x11_err_handler_ref = None
        self._libX11 = None
        self._xmove_target = None
        self.renderer: GLRenderer | None = None
        self.screen = None
        self.target = None
        self.fullscreen = True
        self.xmonitors = self._xrandr_monitors()
        self.num_displays = max(len(self.xmonitors), 1)
        self.display_idx = 0
        self.span_children: dict[int, subprocess.Popen] = {}
        self._install_x11_error_handler()

    def _install_x11_error_handler(self) -> None:
        """Suppress X11 RandR errors on some multi-monitor X11 setups."""
        try:
            import ctypes

            class _XErrorEvent(ctypes.Structure):
                _fields_ = [
                    ("type", ctypes.c_int),
                    ("display", ctypes.c_void_p),
                    ("resourceid", ctypes.c_ulong),
                    ("serial", ctypes.c_ulong),
                    ("error_code", ctypes.c_ubyte),
                    ("request_code", ctypes.c_ubyte),
                    ("minor_code", ctypes.c_ubyte),
                ]

            handler_type = ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_void_p,
                ctypes.POINTER(_XErrorEvent),
            )

            def _handler(display, event):
                return 0

            self._x11_err_handler_ref = handler_type(_handler)
            lib = ctypes.CDLL("libX11.so.6")
            lib.XSetErrorHandler(self._x11_err_handler_ref)
            lib.XMoveWindow.argtypes = [
                ctypes.c_void_p,
                ctypes.c_ulong,
                ctypes.c_int,
                ctypes.c_int,
            ]
            lib.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
            self._libX11 = lib
        except Exception:
            pass

    def _xrandr_monitors(self) -> list[tuple[int, int, int, int]]:
        """Return list of (x, y, w, h) for each physical monitor."""
        try:
            out = subprocess.check_output(
                ["xrandr", "--listmonitors"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            monitors = []
            for line in out.splitlines():
                match = _re.search(r"(\d+)/\d+x(\d+)/\d+\+(\d+)\+(\d+)", line)
                if match:
                    w, h, x, y = (int(match.group(i)) for i in range(1, 5))
                    monitors.append((x, y, w, h))
            monitors.sort(key=lambda mon: mon[0])
            return monitors
        except Exception:
            return []

    def open_display(self, idx: int, fullscreen: bool):
        self.display_idx = idx
        self.fullscreen = fullscreen
        self._xmove_target = None
        flags = 0
        if self.args.gl:
            flags |= pygame.OPENGL | pygame.DOUBLEBUF
        
        if fullscreen and idx < len(self.xmonitors):
            mx, my, mw, mh = self.xmonitors[idx]
            os.environ["SDL_VIDEO_WINDOW_POS"] = f"{mx},{my}"
            self.screen = pygame.display.set_mode((mw, mh), flags | pygame.NOFRAME)
            os.environ.pop("SDL_VIDEO_WINDOW_POS", None)
            if self._libX11:
                wm = pygame.display.get_wm_info()
                dpy = wm.get("display")
                win = wm.get("window")
                if isinstance(dpy, int) and dpy and win:
                    self._libX11.XMoveWindow(dpy, win, mx, my)
                    self._libX11.XSync(dpy, 0)
                    self._xmove_target = (dpy, win, mx, my)
            config.WIDTH = mw
            config.HEIGHT = mh
        elif fullscreen:
            self.screen = pygame.display.set_mode((0, 0), flags | pygame.FULLSCREEN)
            config.WIDTH, config.HEIGHT = self.screen.get_size()
        else:
            self.screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT), flags)
        
        if self.args.gl and HAS_MODERNGL:
            self.renderer = GLRenderer(config.WIDTH, config.HEIGHT)
        
        self.target = self.screen
        if self.args.gl:
            self.target = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
            
        return self.screen

    def toggle_fullscreen(self):
        return self.open_display(self.display_idx, not self.fullscreen)

    def reposition_window_fix(self, tick: int):
        if self._libX11 and self._xmove_target and tick < 60:
            dpy, win, mx, my = self._xmove_target
            self._libX11.XMoveWindow(dpy, win, mx, my)
            self._libX11.XSync(dpy, 0)

    def spawn_span_children(self, mode_i: int, entry_script: str):
        self.kill_children()
        for child_idx in range(self.num_displays):
            if child_idx == self.display_idx:
                continue
            cmd = [
                sys.executable,
                entry_script,
                "--display",
                str(child_idx),
                "--mode",
                str(mode_i),
                "--span-child",
            ]
            if self.args.gl:
                cmd.append("--gl")
            self.span_children[child_idx] = subprocess.Popen(cmd)

    def kill_children(self) -> None:
        for child in self.span_children.values():
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    child.kill()
        self.span_children = {}
