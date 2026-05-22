from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent


def load() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_busy_blocks() -> list[dict]:
    path = ROOT / load()["calendar"]["recurring_busy_file"]
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("blocks") or []
