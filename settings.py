"""Persist user settings and presets to ~/.config/psysuals/."""

import json
import os

_CONFIG_DIR    = os.path.join(os.path.expanduser("~"), ".config", "psysuals")
_SETTINGS_FILE = os.path.join(_CONFIG_DIR, "settings.json")
_PRESETS_FILE  = os.path.join(_CONFIG_DIR, "presets.json")

_DEFAULTS = {
    "active_dev": None,
    "mode_idx": 0,
    "display_idx": 0,
    "show_hud": True,
    "hud_level": 2,
    "auto_gain": False,
    "bg_on": False,
    "bg_mode_i": 0,
    "bg_alpha": 102,
    "cf_frames": 45,
    "effect_gain": 0.7,
}


def load() -> dict:
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    try:
        with open(_SETTINGS_FILE) as f:
            data = json.load(f)
        return {**_DEFAULTS, **data}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_DEFAULTS)


def save(d: dict) -> None:
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    tmp = _SETTINGS_FILE + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(d, f, indent=2)
        os.replace(tmp, _SETTINGS_FILE)
    except (PermissionError, OSError):
        # write-protected config dir — silently skip persistence
        pass


# ── Presets ───────────────────────────────────────────────────────────────────

def load_presets() -> list:
    """Return list of saved preset dicts (each has at least a 'name' key)."""
    try:
        with open(_PRESETS_FILE) as f:
            data = json.load(f)
        if isinstance(data, dict):
            return [{"name": k, **v} for k, v in data.items()]
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _write_presets(presets: list) -> None:
    """Atomically write presets list to disk."""
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    tmp = _PRESETS_FILE + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(presets, f, indent=2)
        os.replace(tmp, _PRESETS_FILE)
    except (PermissionError, OSError):
        pass


def save_preset(name: str, data: dict) -> None:
    """Append a preset entry. Always adds a new entry (append-only)."""
    presets = load_presets()
    presets.append({"name": name, **data})
    _write_presets(presets)


def delete_preset(name: str) -> None:
    """Remove a preset by name (no-op if not found)."""
    presets = [p for p in load_presets() if p.get("name") != name]
    _write_presets(presets)
