import random
import re
from pathlib import Path

from .config import load


def load_activities() -> list[dict]:
    """Parse personal/health/activities.md into a list of {category, text} dicts.

    Format: H2 = category; bullet list under each H2 = activity items.
    Blank lines and comments (lines starting with >) are ignored.
    """
    path = Path(load()["activities"]["path"])
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    activities = []
    current_category = "General"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            current_category = stripped[3:].strip()
        elif stripped.startswith("- "):
            item = stripped[2:].strip()
            if item:
                activities.append({"category": current_category, "text": item})
    return activities


def pick_random() -> dict | None:
    items = load_activities()
    if not items:
        return None
    return random.choice(items)
