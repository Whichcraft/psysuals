"""Persist user settings to ~/.config/psysuals/settings.json."""

import json
import os

_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "psysuals")
_SETTINGS_FILE = os.path.join(_CONFIG_DIR, "settings.json")

_DEFAULTS = {
    "active_dev": None,
    "mode_idx": 0,
    "effect_gain": 1.0,
    "show_hud": True,
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
