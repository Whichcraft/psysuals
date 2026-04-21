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
    with open(_SETTINGS_FILE, "w") as f:
        json.dump(d, f, indent=2)


# ── Presets ───────────────────────────────────────────────────────────────────

def load_presets() -> list:
    """Return list of saved preset dicts (each has at least a 'name' key)."""
    try:
        with open(_PRESETS_FILE) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_preset(name: str, data: dict) -> None:
    """Upsert a preset by name."""
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    presets = load_presets()
    entry = {"name": name, **data}
    for i, p in enumerate(presets):
        if p.get("name") == name:
            presets[i] = entry
            break
    else:
        presets.append(entry)
    with open(_PRESETS_FILE, "w") as f:
        json.dump(presets, f, indent=2)


def delete_preset(name: str) -> None:
    """Remove a preset by name (no-op if not found)."""
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    presets = [p for p in load_presets() if p.get("name") != name]
    with open(_PRESETS_FILE, "w") as f:
        json.dump(presets, f, indent=2)
