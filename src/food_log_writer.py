"""Food log writer — parses the nutrition library, computes scaled macros,
and appends meal rows to C:/life-os/personal/health/food-log.md.

The library lives at the bottom of food-log.md under a `# Nutrition Library`
heading. Each product is its own `## Product Name` section with bullet
fields like `- **Serving:** 1 scoop (30g)` and `- **Calories:** 120`.

Append model: the Flask form posts meal + items to `/food-log/<meal>`, we
look up each item by name (case-insensitive substring), parse the qty the
user typed ("1.5 scoops", "16 oz"), compute the multiplier against the
library's serving size, scale the macros, and write a new markdown table
row under today's meal section. If today's section doesn't exist, we
create it; if the meal's table doesn't exist, we create that too.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

FOOD_LOG_PATH = Path(r"C:\life-os\personal\health\food-log.md")

MEAL_ORDER = ["Breakfast", "Lunch", "Dinner", "Snacks"]
MEAL_TABLE_HEADER = (
    "| Item | Qty | Cal | Protein | Fat | Carbs | Fluid |\n"
    "|---|---|---|---|---|---|---|"
)


@dataclass
class Product:
    name: str
    serving_qty: float       # e.g., 1 for "1 scoop", 1 for "1 cup", 30 for "30g"
    serving_unit: str        # canonical unit, e.g., "scoop", "cup", "g"
    unit_aliases: dict[str, float]  # secondary-unit ratio against canonical, e.g. {"oz": 0.125, "ml": 1/240.0}
    calories: float
    protein_g: float
    fat_g: float
    carbs_g: float
    fluid_oz: float = 0.0    # per one canonical serving; water bottle = 32


def load_library() -> list[Product]:
    if not FOOD_LOG_PATH.exists():
        return []
    text = FOOD_LOG_PATH.read_text(encoding="utf-8")
    lib_match = re.search(r"#\s+Nutrition Library\s*\n(.+?)\Z", text, re.DOTALL)
    if not lib_match:
        return []
    body = lib_match.group(1)
    products: list[Product] = []
    for m in re.finditer(r"^##\s+(.+?)\n(.*?)(?=^##\s+|\Z)", body, re.MULTILINE | re.DOTALL):
        name = m.group(1).strip()
        block = m.group(2)
        p = _parse_product(name, block)
        if p:
            products.append(p)
    return products


def _parse_product(name: str, block: str) -> Optional[Product]:
    def grab(label: str) -> Optional[str]:
        m = re.search(rf"\*\*{re.escape(label)}:?\*\*\s*(.+?)(?:\n|$)", block)
        return m.group(1).strip() if m else None

    serving_str = grab("Serving")
    cal_str = grab("Calories")
    prot_str = grab("Protein")
    fat_str = grab("Fat")
    carb_str = grab("Carbs")
    fluid_str = grab("Fluid")
    if not serving_str:
        return None

    qty, unit, aliases = _parse_serving(serving_str)
    return Product(
        name=name,
        serving_qty=qty,
        serving_unit=unit,
        unit_aliases=aliases,
        calories=_num(cal_str),
        protein_g=_num(prot_str),
        fat_g=_num(fat_str),
        carbs_g=_num(carb_str),
        fluid_oz=_num(fluid_str),
    )


def _parse_serving(s: str) -> tuple[float, str, dict[str, float]]:
    """`1 scoop (30g)` → (1, "scoop", {"g": 30.0}).
    `1 cup (240ml / 8 oz)` → (1, "cup", {"ml": 240.0, "oz": 8.0}).
    `5g` → (5, "g", {}).

    Returned aliases map alias_unit → how many alias_units equal one canonical
    unit. So to scale "16 oz" of a cup-based product: 16 / 8 cups-per-oz-alias = 2 cups.
    """
    s = s.strip()
    m = re.match(r"^\s*([\d.]+)\s*([^\s(]+)\s*(?:\(([^)]*)\))?\s*$", s)
    if not m:
        # Single-word like "5g"
        m2 = re.match(r"^([\d.]+)\s*(\w+)\s*$", s)
        if m2:
            return float(m2.group(1)), m2.group(2), {}
        return 1.0, "unit", {}
    qty = float(m.group(1))
    unit = m.group(2).rstrip("s").lower()
    aliases: dict[str, float] = {}
    if m.group(3):
        # e.g., "30g" or "240ml / 8 oz"
        for part in re.split(r"[/,]", m.group(3)):
            am = re.match(r"\s*([\d.]+)\s*(\w+)", part.strip())
            if am:
                aliases[am.group(2).rstrip("s").lower()] = float(am.group(1))
    return qty, unit, aliases


def _num(s: Optional[str]) -> float:
    if not s:
        return 0.0
    m = re.search(r"([\d.]+)", s)
    return float(m.group(1)) if m else 0.0


# ---- qty parse + scale ----

def parse_qty(text: str) -> tuple[float, str]:
    """`1.5 scoops` → (1.5, "scoop"). `16 oz` → (16.0, "oz"). `2` → (2.0, "").
    Returns canonical (singular, lowercase) unit.
    """
    t = text.strip().lower()
    m = re.match(r"^\s*([\d.]+)\s*(\w+)?", t)
    if not m:
        return 0.0, ""
    qty = float(m.group(1))
    unit = (m.group(2) or "").rstrip("s")
    return qty, unit


def scale_macros(p: Product, qty: float, unit: str) -> Optional[dict]:
    """Compute calories/protein/fat/carbs for `qty unit` of product p.
    Returns None if we can't determine a multiplier.
    """
    canonical = p.serving_unit
    mult: Optional[float] = None
    if not unit or unit == canonical:
        mult = qty / p.serving_qty
    elif unit in p.unit_aliases:
        # aliases[unit] = how many alias-units per one canonical-serving-unit.
        # So N alias-units == N / aliases[unit] canonical-units.
        canonical_units = qty / p.unit_aliases[unit]
        mult = canonical_units / p.serving_qty
    if mult is None:
        return None
    return {
        "calories": p.calories * mult,
        "protein_g": p.protein_g * mult,
        "fat_g": p.fat_g * mult,
        "carbs_g": p.carbs_g * mult,
        "fluid_oz": p.fluid_oz * mult,
    }


def find_product(name_query: str, products: list[Product]) -> Optional[Product]:
    """Case-insensitive: prefer exact, then prefix, then substring."""
    q = name_query.strip().lower()
    if not q:
        return None
    exact = [p for p in products if p.name.lower() == q]
    if exact:
        return exact[0]
    prefix = [p for p in products if p.name.lower().startswith(q)]
    if prefix:
        return prefix[0]
    subs = [p for p in products if q in p.name.lower()]
    if subs:
        return subs[0]
    return None


# ---- Append to food-log.md ----

def _today_header() -> str:
    d = date.today()
    return f"## {d.isoformat()} ({d.strftime('%a')})"


def _fmt(val: float) -> str:
    if abs(val - round(val)) < 0.05:
        return str(int(round(val)))
    return f"{val:.1f}"


def _format_row(item: str, qty_text: str, macros: Optional[dict]) -> str:
    if macros:
        fluid = macros.get("fluid_oz", 0) or 0
        return (
            f"| {item} | {qty_text} | "
            f"{_fmt(macros['calories'])} | {_fmt(macros['protein_g'])}g | "
            f"{_fmt(macros['fat_g'])}g | {_fmt(macros['carbs_g'])}g | "
            f"{_fmt(fluid)} oz |"
        )
    return f"| {item} | {qty_text} | TBD | TBD | TBD | TBD | TBD |"


def append_meal_items(meal: str, items: list[dict]) -> list[dict]:
    """Append one or more rows under today's {meal} section of food-log.md.

    `items` is a list of {"item": str, "qty": str}. Each row is scaled via
    the nutrition library if the product is found + the unit is compatible;
    otherwise macros are written as "TBD" and the user can fix later.

    Returns a list of dicts describing what happened (resolved vs. missing).
    """
    if FOOD_LOG_PATH.parent.exists() is False:
        FOOD_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = FOOD_LOG_PATH.read_text(encoding="utf-8") if FOOD_LOG_PATH.exists() else ""

    products = load_library()
    meal_cap = meal.capitalize()
    today_hdr = _today_header()

    # Compute each row
    results = []
    rows = []
    for it in items:
        name = (it.get("item") or "").strip()
        qty = (it.get("qty") or "").strip()
        if not name or not qty:
            continue
        product = find_product(name, products)
        macros = None
        if product:
            q, u = parse_qty(qty)
            macros = scale_macros(product, q, u)
        rows.append(_format_row(name, qty, macros))
        results.append({
            "item": name,
            "qty": qty,
            "matched": product.name if product else None,
            "scaled": bool(macros),
            "macros": macros,
        })

    if not rows:
        return results

    text = _splice_meal_rows(text, today_hdr, meal_cap, rows)
    FOOD_LOG_PATH.write_text(text, encoding="utf-8")
    return results


def _splice_meal_rows(text: str, today_hdr: str, meal_cap: str, rows: list[str]) -> str:
    """Insert `rows` under the {meal_cap} table of today's section. Create
    the day section, meal header, and table if missing. Preserves the
    `# Nutrition Library` footer — we only touch the daily-log area.
    """
    library_start = text.find("# Nutrition Library")
    if library_start == -1:
        daily_text = text
        library_text = ""
    else:
        daily_text = text[:library_start].rstrip() + "\n"
        library_text = text[library_start:]

    # Does today's section exist?
    day_pat = re.compile(rf"(^{re.escape(today_hdr)}\s*$)", re.MULTILINE)
    if not day_pat.search(daily_text):
        daily_text = daily_text.rstrip() + "\n\n" + today_hdr + "\n"

    # Locate today's section (between today_hdr and next "\n## " or end-of-daily)
    day_start = daily_text.index(today_hdr)
    next_day = daily_text.find("\n## ", day_start + len(today_hdr))
    section_end = next_day if next_day != -1 else len(daily_text)
    section = daily_text[day_start:section_end]

    # Does the meal heading exist in this section?
    meal_pat = re.compile(rf"^###\s+{re.escape(meal_cap)}\b.*$", re.MULTILINE)
    if not meal_pat.search(section):
        insert_body = f"\n### {meal_cap}\n{MEAL_TABLE_HEADER}\n"
        section = section.rstrip() + "\n" + insert_body
    # Locate the meal's table (header + separator)
    meal_match = meal_pat.search(section)
    meal_head_end = meal_match.end()
    # Find table header below the meal heading
    after = section[meal_head_end:]
    tbl_hdr_m = re.search(r"\n\|\s*Item\s*\|.*\n\|[-| ]+\|", after)
    if not tbl_hdr_m:
        # Insert a table header
        section = section[:meal_head_end] + "\n" + MEAL_TABLE_HEADER + "\n" + section[meal_head_end:]
        after = section[meal_head_end:]
        tbl_hdr_m = re.search(r"\n\|\s*Item\s*\|.*\n\|[-| ]+\|", after)
    tbl_body_start = meal_head_end + tbl_hdr_m.end()
    # Walk existing body rows (non-total) to insert before any totals row
    body_after = section[tbl_body_start:]
    row_end = 0
    for line_m in re.finditer(r"\n(\|.*?\|)", body_after):
        # Totals row if bold "total" inside the first cell
        if re.match(r"\n\|\s*\*\*.*?total", line_m.group(0), re.IGNORECASE):
            break
        row_end = line_m.end()
    insert_at = tbl_body_start + row_end
    addition = "\n" + "\n".join(rows)
    section = section[:insert_at] + addition + section[insert_at:]

    daily_text = daily_text[:day_start] + section + daily_text[section_end:]
    return (daily_text.rstrip() + "\n\n" + library_text) if library_text else daily_text


def product_names() -> list[str]:
    """For the Flask form's <datalist>."""
    return [p.name for p in load_library()]
