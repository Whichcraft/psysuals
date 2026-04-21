from __future__ import annotations
import pygame
import config

class UIManager:
    def __init__(self):
        self.font = pygame.font.SysFont("monospace", 16)
        self.font_s = pygame.font.SysFont("monospace", 14)
        self.font_big = pygame.font.SysFont("monospace", 72, bold=True)
        self.pane_open = False
        self.pane_sel = 0
        self.picking = False
        self.pick_sel = 0

    def draw_device_picker(self, target: pygame.Surface, devices: list[tuple[int, str]], active_idx: int | None) -> None:
        overlay = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        target.blit(overlay, (0, 0))

        title = self.font.render(
            "SELECT INPUT DEVICE   Up/Down navigate   Enter confirm   Esc cancel",
            True,
            (200, 200, 200),
        )
        target.blit(title, (40, 30))

        if not devices:
            empty = self.font.render("No input devices available", True, (180, 180, 180))
            target.blit(empty, (40, 80))
            return

        row_h = 28
        y0 = 80
        visible = min(len(devices), (config.HEIGHT - y0 - 20) // row_h)
        start = max(0, min(self.pick_sel - visible // 2, len(devices) - visible))

        for i, (dev_idx, name) in enumerate(devices[start : start + visible]):
            row = start + i
            y = y0 + i * row_h
            is_selected = row == self.pick_sel
            is_active = dev_idx == active_idx
            if is_selected:
                pygame.draw.rect(target, (40, 80, 140), (30, y - 2, config.WIDTH - 60, row_h - 2))
            marker = ">> " if is_active else "   "
            label = f"{marker}{dev_idx:3d}  {name}"
            color = (255, 255, 100) if is_selected else (140, 140, 140)
            target.blit(self.font.render(label, True, color), (40, y))

    def draw_pane(self, target: pygame.Surface, effect_gain: float, bg_alpha: int, cf_frames: float) -> None:
        panel_w, panel_h = 240, 160
        px = config.WIDTH - panel_w - 12
        py = 50
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 185))
        target.blit(panel, (px, py))
        pygame.draw.rect(target, (80, 80, 80), (px, py, panel_w, panel_h), 1)
        title = self.font_s.render("Settings  (Tab: close)", True, (120, 120, 120))
        target.blit(title, (px + 8, py + 6))
        items = [
            ("effect_gain", effect_gain, 2.0, f"{effect_gain:.1f}"),
            ("bg_alpha", bg_alpha, 255, f"{bg_alpha}"),
            ("crossfade", cf_frames, 90, f"{int(cf_frames)} fr"),
        ]
        for i, (label, value, max_value, value_str) in enumerate(items):
            y = py + 30 + i * 42
            selected = i == self.pane_sel
            color = (255, 255, 100) if selected else (150, 150, 150)
            marker = ">> " if selected else "   "
            target.blit(
                self.font_s.render(f"{marker}{label}: {value_str}", True, color),
                (px + 10, y),
            )
            bar_total = panel_w - 24
            bar_w = int(bar_total * max(0.0, min(value / max_value, 1.0)))
            pygame.draw.rect(target, (50, 50, 50), (px + 10, y + 16, bar_total, 6))
            if bar_w > 0:
                pygame.draw.rect(target, color, (px + 10, y + 16, bar_w, 6))

    def draw_multiband_bars(self, target: pygame.Surface, beat_val: float, mid_val: float, treble_val: float) -> None:
        bar_w = 8
        bar_max = 120
        gap = 3
        total_w = 3 * bar_w + 2 * gap
        bar_surf = pygame.Surface((total_w, bar_max), pygame.SRCALPHA)
        defs = [
            (beat_val, (180, 50, 50, 150)),
            (mid_val, (50, 180, 50, 150)),
            (treble_val, (130, 60, 200, 150)),
        ]
        for i, (value, color) in enumerate(defs):
            h = int(bar_max * max(0.0, min(value / 3.0, 1.0)))
            x = i * (bar_w + gap)
            if h > 0:
                pygame.draw.rect(bar_surf, color, (x, bar_max - h, bar_w, h))
        target.blit(bar_surf, (6, config.HEIGHT - bar_max - 6))

    def draw_tap_flash(self, target: pygame.Surface, tap_bpm: float, alpha: int) -> None:
        flash = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        flash.fill((255, 255, 255, alpha // 6))
        target.blit(flash, (0, 0))
        label = self.font_big.render(f"{tap_bpm:.0f} BPM", True, (255, 255, 255, alpha))
        target.blit(
            label,
            (
                config.WIDTH // 2 - label.get_width() // 2,
                config.HEIGHT // 2 - label.get_height() // 2,
            ),
        )
