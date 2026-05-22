from pathlib import Path
import yaml

from .config import ROOT

SCALES_DIR = ROOT / "scales"


def load_scale(scale_id: str) -> dict:
    path = SCALES_DIR / f"{scale_id}.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_scales() -> list[dict]:
    return [load_scale(p.stem) for p in sorted(SCALES_DIR.glob("*.yaml"))]


def score(scale: dict, responses: list[int]) -> dict:
    formula = scale.get("scoring", "sum")
    if formula == "sum":
        total = sum(responses)
    elif formula == "sum_x4":
        total = sum(responses) * 4
    else:
        raise ValueError(f"Unknown scoring formula: {formula}")

    band = "Unknown"
    for low, high, label in scale.get("bands", []):
        if low <= total <= high:
            band = label
            break

    return {"score": total, "band": band}
