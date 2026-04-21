#!/usr/bin/env python3
"""
Music Visualizer — real-time audio -> visuals.

Controls:
  SPACE / click   Switch to next mode
  1-9             Jump to modes 1-9
  Left/Right      Cycle modes (or adjust pane slider when pane is open)
  Up/Down         Adjust intensity (or navigate pane sliders when pane is open)
  Tab             Toggle real-time settings pane
  P               Save current state as a preset
  Shift+P         Cycle through saved presets
  A               Toggle auto-gain (or cycle child mode backward in span mode)
  B               Toggle background layer
  Shift+B         Cycle background effect
  M               Tap tempo (tap 2+ times to lock BPM for 8s)
  Shift+M         Toggle span mode (multi-monitor extension)
  D               Open device picker (or cycle child mode forward in span mode)
  F               Toggle fullscreen
  H               Toggle HUD visibility
  Shift+H         Cycle HUD detail level
  Q / ESC         Quit
"""

from __future__ import annotations

__version__ = "3.1.0"

import argparse
import atexit
import os
import sys
import time as _time
import signal
import subprocess
from collections import deque

import numpy as np
import pygame

try:
    import moderngl
except ImportError:
    moderngl = None

import config
import settings as sett
from core.audio_engine import AudioEngine
from core.display_manager import DisplayManager
from core.ui_manager import UIManager
from effects import MODES
from effects.palette import palette

_CROSSFADE_FRAMES = 45
_BG_MODES = 9

class VisualizerApp:
    def __init__(self):
        self._setup_signals()
        self.args = self._parse_args()
        self.settings = sett.load()
        
        self.display = DisplayManager(self.args)
        self.audio = AudioEngine()
        
        self._init_display()
        self.ui = UIManager()
        self._init_audio()
        
        self.mode_idx = min(self.settings.get("mode_idx", 0), len(MODES) - 1)
        if self.args.mode is not None:
            self.mode_idx = self.args.mode % len(MODES)
        
        self.name, self.VisCls = MODES[self.mode_idx]
        self.vis = self.VisCls(renderer=self.display.renderer)
        
        self.bg_on = self.settings.get("bg_on", False)
        self.bg_mode_i = self.settings.get("bg_mode_i", 0) % _BG_MODES
        self.bg_name, self.bg_cls = MODES[self.bg_mode_i]
        self.bg_vis = self.bg_cls(renderer=self.display.renderer)
        self.bg_surf = pygame.Surface((config.WIDTH, config.HEIGHT))
        self.bg_alpha = self.settings.get("bg_alpha", 102)
        
        self.prev_surf = None
        self.crossfade_frame = 0
        self.cf_frames = self.settings.get("cf_frames", _CROSSFADE_FRAMES)
        
        self.tick = 0
        self.energy_hist = deque(maxlen=40)
        self.energy_sum = 0.0
        self.beat_decay = 0.0
        self.effect_gain = self.settings.get("effect_gain", config.DEFAULT_EFFECT_GAIN)
        self.current_genre = "detecting..."
        
        self.hud_level = self.settings.get("hud_level", 2)
        self.show_hud = self.hud_level > 0
        
        self.auto_gain = self.settings.get("auto_gain", False)
        self.rms_buf = deque(maxlen=30)
        self.target_rms = 0.05
        
        self.tap_times = deque(maxlen=4)
        self.tap_bpm = 0.0
        self.tap_bpm_expiry = 0.0
        self.tap_flash_end = 0.0
        
        self.span_vis2_idx = (self.mode_idx + 1) % len(MODES)
        self.span_mode = len(self.display.xmonitors) >= 2 and not self.args.span_child
        if self.span_mode:
            self.display.spawn_span_children(self.span_vis2_idx, os.path.abspath(__file__))
            
        self.presets = sett.load_presets()
        self.active_preset = -1
        self.dev_name_cache = {}
        
        self.clock = pygame.time.Clock()
        self.fade_alpha = 28
        self.fade = self._make_fade(self.fade_alpha)
        
        atexit.register(self.display.kill_children)

    def _setup_signals(self):
        def _sig_handler(sig, frame):
            self._quit()
        signal.signal(signal.SIGINT, _sig_handler)
        signal.signal(signal.SIGTERM, _sig_handler)

    def _parse_args(self):
        desc = "psysuals — The Ultimate Psychedelic Music Visualizer v" + __version__ + "\n\n"
        desc += "Controls:\n"
        desc += "  Space / Click   Cycle modes\n"
        desc += "  1-9             Jump to mode\n"
        desc += "  Arrows          Intensity / Settings / Modes\n"
        desc += "  Tab             Toggle settings pane\n"
        desc += "  F               Toggle fullscreen\n"
        desc += "  H / Shift+H     HUD visibility / Detail\n"
        desc += "  M / Shift+M     Tap Tempo / Span Mode\n"
        desc += "  D               Device picker / Span cycle\n"
        desc += "  Q / Esc         Quit"
        
        parser = argparse.ArgumentParser(
            description=desc,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        parser.add_argument("-d", "--display", type=int, default=None, help="Target display index (e.g. 0, 1)")
        parser.add_argument("-m", "--mode", type=int, default=None, help="Starting mode index (0-17)")
        parser.add_argument("-g", "--gl", action="store_true", help="Enable ModernGL hardware acceleration")
        parser.add_argument("--span-child", action="store_true", help=argparse.SUPPRESS)
        return parser.parse_args()

    def _init_display(self):
        requested_display = (self.settings.get("display_idx", 0) 
                           if self.args.display is None else self.args.display)
        display_idx = max(0, min(requested_display, self.display.num_displays - 1))
        pygame.init()
        self.display.open_display(display_idx, True)
        pygame.display.set_caption(f"psysuals v{__version__}")

    def _init_audio(self):
        active_dev = self.settings.get("active_dev")
        devices = self.audio.input_devices()
        if active_dev is not None and active_dev not in [d[0] for d in devices]:
            active_dev = None
        self.audio.open_input_stream(active_dev, None)

    def _make_fade(self, alpha: int):
        # Use SRCALPHA for the UI layer surface to allow layering over GL
        surf = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        surf.fill((0, 0, 0, alpha))
        return surf

    def _quit(self):
        self.display.kill_children()
        if self.display.renderer:
            self.display.renderer.release()
        try:
            pygame.display.set_mode((1, 1))
        except Exception:
            pass
        self.audio.stop_input_stream()
        pygame.quit()
        sys.exit(0)

    def _save_settings(self):
        if self.args.span_child:
            return
        sett.save({
            "active_dev": self.audio.active_dev,
            "mode_idx": self.mode_idx,
            "show_hud": self.show_hud,
            "auto_gain": self.auto_gain,
            "bg_on": self.bg_on,
            "bg_mode_i": self.bg_mode_i,
            "display_idx": self.display.display_idx,
            "bg_alpha": self.bg_alpha,
            "cf_frames": self.cf_frames,
            "hud_level": self.hud_level,
            "effect_gain": self.effect_gain,
        })

    def _switch_mode(self, new_idx: int):
        if hasattr(self.vis, "release") and callable(self.vis.release):
            self.vis.release()
        self.prev_surf = self.display.target.copy()
        self.crossfade_frame = 0
        self.mode_idx = new_idx % len(MODES)
        self.name, self.VisCls = MODES[self.mode_idx]
        self.vis = self.VisCls(renderer=self.display.renderer)
        self.effect_gain = config.DEFAULT_EFFECT_GAIN

    def _rebuild_effects(self):
        if hasattr(self.vis, "release") and callable(self.vis.release):
            self.vis.release()
        if hasattr(self.bg_vis, "release") and callable(self.bg_vis.release):
            self.bg_vis.release()
        self.vis = self.VisCls(renderer=self.display.renderer)
        self.bg_name, self.bg_cls = MODES[self.bg_mode_i]
        self.bg_vis = self.bg_cls(renderer=self.display.renderer)
        self.bg_surf = pygame.Surface((config.WIDTH, config.HEIGHT))

    def run(self):
        while True:
            self._handle_events()
            self._update()
            
            # Clear GL screen at start of frame
            if self.args.gl and self.display.renderer:
                self.display.renderer.ctx.screen.use()
                self.display.renderer.ctx.clear(0.0, 0.0, 0.0, 1.0)
                self.display.renderer.ctx.disable(moderngl.BLEND)

            self._render()
            
            if self.args.gl and self.display.renderer:
                self.display.renderer.blit(self.display.target)
                self.display.target.fill((0, 0, 0, 0))
                
            pygame.display.flip()
            self.clock.tick(config.FPS)
            self.tick += 1

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._save_settings()
                self._quit()
            
            elif event.type == pygame.KEYDOWN:
                if self.ui.picking:
                    if event.key == pygame.K_UP:
                        self.ui.pick_sel = (self.ui.pick_sel - 1) % max(1, len(self.audio.input_devices()))
                    elif event.key == pygame.K_DOWN:
                        self.ui.pick_sel = (self.ui.pick_sel + 1) % max(1, len(self.audio.input_devices()))
                    elif event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                        if event.key == pygame.K_RETURN:
                            devs = self.audio.input_devices()
                            if 0 <= self.ui.pick_sel < len(devs):
                                self.audio.start_input_stream(devs[self.ui.pick_sel][0])
                        self.ui.picking = False
                    continue

                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    self._save_settings()
                    self._quit()
                elif event.key == pygame.K_f:
                    self.display.toggle_fullscreen()
                    self._rebuild_effects()
                    self.fade = self._make_fade(self.fade_alpha)
                elif event.key == pygame.K_h:
                    if event.mod & pygame.KMOD_SHIFT:
                        self.hud_level = (self.hud_level + 1) % 3
                        self.show_hud = self.hud_level > 0
                    else:
                        self.show_hud = not self.show_hud
                elif event.key == pygame.K_TAB:
                    self.ui.pane_open = not self.ui.pane_open
                elif event.key == pygame.K_m:
                    if event.mod & pygame.KMOD_SHIFT:
                        if self.span_mode:
                            self.display.kill_children()
                            self.span_mode = False
                        elif not self.args.span_child:
                            self.display.spawn_span_children(self.span_vis2_idx, os.path.abspath(__file__))
                            self.span_mode = True
                    else:
                        t = _time.monotonic()
                        self.tap_times.append(t)
                        if len(self.tap_times) >= 2:
                            self.tap_bpm = 60.0 / np.median(np.diff(list(self.tap_times)))
                            self.tap_bpm_expiry = t + 8.0
                            self.tap_flash_end = t + 0.5
                elif event.key == pygame.K_a:
                    if self.span_mode:
                        self.span_vis2_idx = (self.span_vis2_idx - 1) % len(MODES)
                        self.display.spawn_span_children(self.span_vis2_idx, os.path.abspath(__file__))
                    else:
                        self.auto_gain = not self.auto_gain
                elif event.key == pygame.K_d:
                    if self.span_mode:
                        self.span_vis2_idx = (self.span_vis2_idx + 1) % len(MODES)
                        self.display.spawn_span_children(self.span_vis2_idx, os.path.abspath(__file__))
                    else:
                        self.ui.picking = True
                        devs = self.audio.input_devices()
                        self.ui.pick_sel = next((i for i, d in enumerate(devs) if d[0] == self.audio.active_dev), 0)
                elif event.key == pygame.K_b:
                    if event.mod & pygame.KMOD_SHIFT:
                        self.bg_mode_i = (self.bg_mode_i + 1) % _BG_MODES
                        self.bg_name, self.bg_cls = MODES[self.bg_mode_i]
                        self.bg_vis = self.bg_cls(renderer=self.display.renderer)
                    else:
                        self.bg_on = not self.bg_on
                elif event.key == pygame.K_p:
                    if event.mod & pygame.KMOD_SHIFT:
                        self.active_preset = (self.active_preset + 1) % max(1, len(self.presets))
                        if self.presets:
                            p = list(self.presets.values())[self.active_preset]
                            self._switch_mode(p["mode_idx"])
                            self.effect_gain = p.get("intensity", 0.7)
                            self.bg_on = p.get("bg_on", False)
                            self.bg_mode_i = p.get("bg_mode_i", 0)
                            self.bg_name, self.bg_cls = MODES[self.bg_mode_i]
                            self.bg_vis = self.bg_cls(renderer=self.display.renderer)
                    else:
                        preset_name = f"Preset {len(self.presets) + 1}"
                        sett.save_preset(preset_name, {
                            "mode_idx": self.mode_idx,
                            "intensity": self.effect_gain,
                            "bg_on": self.bg_on,
                            "bg_mode_i": self.bg_mode_i,
                        })
                        self.presets = sett.load_presets()
                        self.active_preset = len(self.presets) - 1
                elif event.key == pygame.K_RIGHT:
                    if self.ui.pane_open:
                        self._pane_adjust(1)
                    else:
                        self._switch_mode(self.mode_idx + 1)
                elif event.key == pygame.K_LEFT:
                    if self.ui.pane_open:
                        self._pane_adjust(-1)
                    else:
                        self._switch_mode(self.mode_idx - 1)
                elif event.key == pygame.K_UP:
                    if self.ui.pane_open:
                        self.ui.pane_sel = (self.ui.pane_sel - 1) % 3
                    else:
                        self.effect_gain = min(2.0, round(self.effect_gain + 0.1, 1))
                elif event.key == pygame.K_DOWN:
                    if self.ui.pane_open:
                        self.ui.pane_sel = (self.ui.pane_sel + 1) % 3
                    else:
                        self.effect_gain = max(0.0, round(self.effect_gain - 0.1, 1))
                elif pygame.K_1 <= event.key <= pygame.K_9:
                    self._switch_mode(event.key - pygame.K_1)
            
            elif event.type == pygame.MOUSEBUTTONDOWN and not self.ui.picking:
                self._switch_mode(self.mode_idx + 1)

    def _pane_adjust(self, delta: int):
        if self.ui.pane_sel == 0:
            self.effect_gain = min(2.0, max(0.0, round(self.effect_gain + delta * 0.1, 1)))
        elif self.ui.pane_sel == 1:
            self.bg_alpha = min(255, max(0, self.bg_alpha + delta * 5))
        elif self.ui.pane_sel == 2:
            self.cf_frames = min(90, max(0, self.cf_frames + delta * 5))

    def _update(self):
        detected = self.audio.detect_genre()
        if detected:
            self.current_genre = detected
            self.audio.apply_genre_weights(detected)
            palette.set_genre(detected)
            
        self.waveform, self.fft, raw_beat, mid_e, treble_e, bpm, audio_time = self.audio.get_audio()
        if self.audio.beat_tracker.enabled:
            bpm = self.audio.beat_tracker.analyze(fallback_bpm=bpm)
            raw_beat = self.audio.beat_tracker.refine_beat(raw_beat, audio_time)
            
        config.MID_ENERGY = mid_e
        config.TREBLE_ENERGY = treble_e
        config.EFFECT_GAIN = self.effect_gain
        
        if self.tap_bpm > 0 and _time.monotonic() < self.tap_bpm_expiry:
            config.BPM = self.tap_bpm
            self.bpm = self.tap_bpm
            self.using_tap = True
        else:
            config.BPM = bpm
            self.bpm = bpm
            self.using_tap = False
            
        if len(self.energy_hist) == self.energy_hist.maxlen:
            self.energy_sum -= self.energy_hist[0]
        self.energy_hist.append(raw_beat)
        self.energy_sum += raw_beat
        avg = self.energy_sum / len(self.energy_hist) if self.energy_hist else 1e-6
        impulse = max(0.0, min(raw_beat / (avg + 1e-6) - 1.0, 3.0))
        self.beat_decay = max(impulse, self.beat_decay * 0.90)
        self.beat = self.beat_decay
        
        self.rms_buf.append(float(np.sqrt(np.mean(self.waveform ** 2))))
        if self.auto_gain and self.rms_buf:
            cur_rms = float(np.mean(self.rms_buf)) + 1e-9
            auto_scale = max(0.5, min(self.target_rms / cur_rms, 2.0))
            self.draw_beat = self.beat * auto_scale
        else:
            self.draw_beat = self.beat * self.effect_gain
            
        palette.update(self.beat, mid_e, treble_e, self.tick)
        
        self.display.reposition_window_fix(self.tick)

        # Unified exit: if any child window is closed/ESC'd, parent quits too
        if self.span_mode:
            for child in self.display.span_children.values():
                if child.poll() is not None:
                    self._save_settings()
                    self._quit()

    def _render(self):
        target = self.display.target
        
        genre_alpha = palette.trail_alpha if self.current_genre != "detecting..." else None
        new_alpha = genre_alpha if genre_alpha is not None else getattr(self.vis, "TRAIL_ALPHA", 28)
        if new_alpha != self.fade_alpha:
            self.fade_alpha = new_alpha
            self.fade = self._make_fade(self.fade_alpha)
            
        # In GL mode, we ONLY apply the fade if NOT using a pure GL effect.
        # Otherwise, the fade (black blit) will hide the GL rendering.
        if not (self.args.gl and self.vis.IS_GL):
            target.blit(self.fade, (0, 0))
        
        if self.bg_on:
            self.bg_surf.fill((0, 0, 0))
            self.bg_vis.draw(self.bg_surf, self.waveform, self.fft, self.draw_beat, self.tick)
            self.bg_surf.set_alpha(self.bg_alpha)
            target.blit(self.bg_surf, (0, 0))
            
        self.vis.draw(target, self.waveform, self.fft, self.draw_beat, self.tick)
        
        if self.prev_surf:
            frames = max(1, int(self.cf_frames))
            t = self.crossfade_frame / frames
            ease = t * t * (3.0 - 2.0 * t)
            self.prev_surf.set_alpha(int(255 * (1.0 - ease)))
            target.blit(self.prev_surf, (0, 0))
            self.crossfade_frame += 1
            if self.crossfade_frame >= frames:
                self.prev_surf = None
                
        now = _time.monotonic()
        if self.tap_bpm > 0 and now < self.tap_flash_end:
            self.ui.draw_tap_flash(target, self.tap_bpm, int(180 * min(self.tap_flash_end - now, 1.0)))
            
        if self.show_hud:
            self._render_hud(target)
            
        if self.ui.pane_open:
            self.ui.draw_pane(target, self.effect_gain, self.bg_alpha, self.cf_frames)
            
        if self.ui.picking:
            self.ui.draw_device_picker(target, self.audio.input_devices(), self.audio.active_dev)

    def _render_hud(self, target):
        self.ui.draw_multiband_bars(target, self.beat, config.MID_ENERGY, config.TREBLE_ENERGY)
        
        if self.audio.stream is None:
            dev_name = "no input"
        elif self.audio.active_dev is None:
            dev_name = "default"
        else:
            if self.audio.active_dev not in self.dev_name_cache:
                devs = self.audio.input_devices()
                self.dev_name_cache[self.audio.active_dev] = next((d[1] for d in devs if d[0] == self.audio.active_dev), "unknown")
            dev_name = self.dev_name_cache[self.audio.active_dev]
            
        fps = self.clock.get_fps()
        gl_tag = " | GL" if self.args.gl else ""
        title = f"psysuals v{__version__}  [{fps:.0f} fps{gl_tag}]"
        
        y0 = 6
        target.blit(self.ui.font.render(title, True, (220, 220, 220)), (6, y0))
        
        mode_text = f"Mode {self.mode_idx+1}: {self.name} ({self.effect_gain:.1f})"
        if self.bg_on:
            mode_text += f" + BG: {self.bg_name}"
        target.blit(self.ui.font.render(mode_text, True, (200, 200, 100)), (6, y0 + 20))
        
        if self.hud_level > 1:
            info = f"BPM: {self.bpm:.1f} ({self.current_genre})"
            if self.using_tap: info += " [TAP]"
            if self.auto_gain: info += " [AUTO]"
            target.blit(self.ui.font_s.render(info, True, (160, 160, 160)), (6, y0 + 42))
            target.blit(self.ui.font_s.render(f"Input: {dev_name}", True, (130, 130, 130)), (6, y0 + 58))
            
            if self.active_preset >= 0 and self.presets:
                pname = list(self.presets.keys())[self.active_preset]
                target.blit(self.ui.font_s.render(f"Preset: {pname}", True, (100, 200, 255)), (6, y0 + 74))

if __name__ == "__main__":
    try:
        app = VisualizerApp()
        app.run()
    except KeyboardInterrupt:
        pygame.quit()
        sys.exit(130)
