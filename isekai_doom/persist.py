"""persist.py — tiny JSON save file for user settings + high scores.

We keep a single `isekai_save.json` in the project root. Everything degrades
gracefully: if the file is missing or corrupt, we fall back to defaults so the
game always launches.
"""

import os                 # File path handling.
import json               # Reading/writing the save file.
from . import config      # DEFAULT_SETTINGS.

# The save file lives in the project root (one level above this package).
SAVE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "isekai_save.json")


def _load_all():
    """Load the whole save dict, or return a fresh default structure."""
    try:
        with open(SAVE_PATH, "r") as f:          # Open the save file.
            data = json.load(f)                  # Parse the JSON.
        if not isinstance(data, dict):           # Guard against weird contents.
            raise ValueError
        return data
    except Exception:
        # Missing/corrupt file -> start fresh.
        return {"settings": {}, "highscores": []}


def _save_all(data):
    """Write the whole save dict back to disk (best effort)."""
    try:
        with open(SAVE_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        # On a read-only filesystem we simply skip saving.
        pass


def load_settings():
    """Return user settings merged over the defaults (so new keys appear)."""
    data = _load_all()                           # Read the save file.
    settings = dict(config.DEFAULT_SETTINGS)     # Start from defaults.
    settings.update(data.get("settings", {}))    # Overlay saved values.
    return settings


def save_settings(settings):
    """Persist the given settings dict."""
    data = _load_all()                           # Keep existing high scores.
    data["settings"] = settings                  # Replace the settings block.
    _save_all(data)


def load_highscores():
    """Return the saved high-score list (newest/best first), capped at 10."""
    data = _load_all()
    scores = data.get("highscores", [])
    return scores[:10]


def add_highscore(name, score, difficulty):
    """Insert a new score, keep the top 10 by score, and persist."""
    data = _load_all()
    scores = data.get("highscores", [])
    scores.append({"name": name, "score": int(score), "difficulty": difficulty})
    # Sort highest score first and keep only the top ten.
    scores.sort(key=lambda s: s["score"], reverse=True)
    data["highscores"] = scores[:10]
    _save_all(data)
    return data["highscores"]
