"""Cairn — unified bariatric + GLP-1 + general health tracker.

Renamed 2026-05-22 from life-os-bridge. PERS-006. Flask + PWA app reachable
via Tailscale from phone. Submits weight, body measurements, blood pressure,
medication events, clinical events, validated mental-health scales (owner-
gated), and activity confirmations. Scheduler (separate process) fires ntfy
prompts. Phase 2 will add the brief's five-table fact data architecture and
segmented projection model. See c:/life-os/meta/plans/2026-05-22-cairn-
unified-tracker-plan.md.
"""

import json
from datetime import date, datetime
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, send_from_directory, url_for

from src import scales, storage
from src.activities import load_activities
from src.config import load as load_config
from src import food_log_writer

# Optional life-os integration: the author runs Cairn alongside a personal
# task system called life-os. If config.yaml sets `integrations.life_os_scripts_path`
# (or the env var CAIRN_LIFEOS_PATH is set), /today can pull plan blocks and
# priority tasks from those shared modules. Without it, /today degrades to
# scale + body data only. This entire block is optional.
import os
import sys
_lifeos_path = os.environ.get("CAIRN_LIFEOS_PATH")
if not _lifeos_path:
    try:
        _lifeos_path = (load_config().get("integrations") or {}).get("life_os_scripts_path")
    except Exception:
        _lifeos_path = None
build_today = None
if _lifeos_path and os.path.isdir(_lifeos_path):
    sys.path.insert(0, _lifeos_path)
    try:
        from today_data import build_today  # type: ignore  # noqa: E402
    except ImportError:
        build_today = None

app = Flask(__name__)


def _format_weight_last() -> str | None:
    """Build the 'last weight' display string from the canonical source
    (health-log.md), not from the SQLite submissions table. The bridge's
    SQLite only captures weights submitted THROUGH the /weight endpoint;
    weights typed directly into the markdown via Obsidian, terminal-Claude,
    or voice would otherwise be invisible here.
    """
    recent = storage.read_recent_weights(limit=2)
    if not recent:
        return None
    date_iso, weight = recent[0]
    base = f"last: {weight} lb on {date_iso}"
    if len(recent) >= 2:
        delta = weight - recent[1][1]
        if abs(delta) >= 0.05:  # ignore identical-to-1-decimal noise
            sign = "+" if delta > 0 else ""
            base += f" ({sign}{delta:.1f} from {recent[1][0]})"
    return base


@app.route("/")
def index():
    cfg = load_config()
    scale_defs = scales.list_scales()
    cadence = storage.screen_cadence([s["id"] for s in scale_defs])
    cadence_by_id = {c["scale_id"]: c for c in cadence}
    # Decorate scale_defs with cadence info so the template can render countdown + flag
    for s in scale_defs:
        s["cadence"] = cadence_by_id.get(s["id"])
    any_due = any(c["status"] in ("due", "never") for c in cadence)
    return render_template(
        "index.html",
        scales=scale_defs,
        weight_last_display=_format_weight_last(),
        today=date.today().isoformat(),
        activities_count=len(load_activities()),
        quiet_hours=cfg["quiet_hours"],
        any_screens_due=any_due,
    )


# ---- Weight ----

@app.route("/weight", methods=["GET", "POST"])
def weight():
    if request.method == "POST":
        try:
            value = float(request.form["weight"])
        except (KeyError, ValueError):
            abort(400, "weight must be a number")
        note = request.form.get("note", "").strip()
        sub_id = storage.save_submission("weight", {"weight_lb": value, "note": note})
        storage.save_daily_observation({
            "date": date.today().isoformat(),
            "weight_lb": value,
            "weight_observed": True,
            "weight_source": "manual",
            "notes": note or None,
            "source": "manual_form",
            "source_record_id": f"sub:{sub_id}",
        })
        storage.upsert_health_log_field("Weight", str(value))
        if note:
            storage.upsert_health_log_field("Note", note)
        return redirect(url_for("submitted", kind="weight"))
    return render_template("weight.html", today=date.today().isoformat())


# ---- Daily health log (objective-only, schema rev 2026-05-09) ----

@app.route("/daily", methods=["GET", "POST"])
def daily():
    """Full daily entry. All fields optional. Subjective ratings (Sleep /10,
    Mood /10, Moved Y/N) intentionally removed — see personal/health/health-log.md
    schema header for the rationale."""
    if request.method == "POST":
        f = request.form
        # Pills (4-slot schema as of 2026-05-17)
        wake = (f.get("wake") or "").strip().upper()
        breakfast = (f.get("breakfast") or "").strip().upper()
        lunch = (f.get("lunch") or "").strip().upper()
        bedtime = (f.get("bedtime") or "").strip().upper()
        # Body
        weight = (f.get("weight") or "").strip()
        bp_sys = (f.get("bp_sys") or "").strip()
        bp_dia = (f.get("bp_dia") or "").strip()
        bp_pulse = (f.get("bp_pulse") or "").strip()
        # Wearable
        sleep_h = (f.get("sleep_h") or "").strip()
        sleep_m = (f.get("sleep_m") or "").strip()
        sleep_score = (f.get("sleep_score") or "").strip()
        resting_hr = (f.get("resting_hr") or "").strip()
        spo2_low = (f.get("spo2_low") or "").strip()
        steps_prev = (f.get("steps_prev") or "").strip()
        # Body checks
        bm = (f.get("bm") or "").strip().upper()
        edema = (f.get("edema") or "").strip().upper()
        # Note
        note = (f.get("note") or "").strip()

        # Compose composite fields
        bp = ""
        if bp_sys and bp_dia:
            bp = f"{bp_sys}/{bp_dia}"
            if bp_pulse:
                bp += f", {bp_pulse} bpm"

        sleep_wearable = ""
        if sleep_h or sleep_m:
            parts = []
            if sleep_h:
                parts.append(f"{sleep_h}h")
            if sleep_m:
                parts.append(f"{sleep_m}m")
            sleep_wearable = " ".join(parts)
            if sleep_score:
                sleep_wearable += f", score {sleep_score}/100"

        # Persist raw fields to SQLite (legacy submissions blob)
        sub_id = storage.save_submission("daily_health", {
            "wake": wake, "breakfast": breakfast, "lunch": lunch, "bedtime": bedtime,
            "weight": weight, "bp": bp,
            "sleep_wearable": sleep_wearable,
            "resting_hr": resting_hr, "spo2_low": spo2_low, "steps_prev": steps_prev,
            "bm": bm, "edema": edema,
            "note": note,
        })

        # Mirror-write into the v1 daily_observations fact table.
        obs_row: dict = {
            "date": date.today().isoformat(),
            "source": "manual_form",
            "source_record_id": f"sub:{sub_id}",
        }
        if weight:
            try:
                obs_row["weight_lb"] = float(weight)
                obs_row["weight_observed"] = True
                obs_row["weight_source"] = "manual"
            except ValueError:
                pass
        if bp_sys and bp_dia:
            try:
                obs_row["systolic"] = int(bp_sys)
                obs_row["diastolic"] = int(bp_dia)
            except ValueError:
                pass
            if bp_pulse:
                try:
                    obs_row["pulse_from_bp_device"] = int(bp_pulse)
                except ValueError:
                    pass
        if resting_hr:
            try:
                obs_row["resting_hr"] = int(resting_hr)
            except ValueError:
                pass
        if steps_prev:
            try:
                obs_row["steps"] = int(steps_prev)
                obs_row["steps_observed"] = True
            except ValueError:
                pass
        if sleep_h or sleep_m:
            try:
                h = float(sleep_h) if sleep_h else 0.0
                m = float(sleep_m) if sleep_m else 0.0
                obs_row["sleep_hours"] = h + m / 60.0
            except ValueError:
                pass
        # spo2_low has no dedicated column yet (planned for v0.2); fall through to notes.
        notes_parts: list[str] = []
        for label, v in (("wake", wake), ("breakfast", breakfast), ("lunch", lunch),
                         ("bedtime", bedtime), ("bm", bm), ("edema", edema)):
            if v:
                notes_parts.append(f"{label}={v}")
        if spo2_low:
            notes_parts.append(f"spo2_low={spo2_low}")
        if note:
            notes_parts.append(note)
        if notes_parts:
            obs_row["notes"] = "; ".join(notes_parts)
        # Only insert if at least one measurement or note field was populated
        if set(obs_row.keys()) - {"date", "source", "source_record_id"}:
            storage.save_daily_observation(obs_row)

        # Mirror to health-log.md, only writing fields that have a value
        writes = [
            ("Wake", wake), ("Breakfast", breakfast), ("Lunch", lunch), ("Bedtime", bedtime),
            ("Weight", weight),
            ("BP", bp + (f" #cardio" if bp else "")),
            ("Sleep (wearable)", sleep_wearable + (" #psych #pulm" if sleep_wearable else "")),
            ("Resting HR", (f"{resting_hr} bpm #cardio" if resting_hr else "")),
            ("SpO2 (overnight low)", (f"{spo2_low}% #pulm" if spo2_low else "")),
            ("Steps (prev day)", (f"{steps_prev} #bariatric #cardio" if steps_prev else "")),
            ("BM", (f"{bm} #bariatric #dietician" if bm else "")),
            ("Edema", (f"{edema} #cardio" if edema else "")),
            ("Note", note),
        ]
        for field_name, value in writes:
            if value:
                storage.upsert_health_log_field(field_name, value)

        return redirect(url_for("submitted", kind="daily"))

    cfg = load_config()
    pill_labels = cfg.get("pill_labels") or {}
    return render_template("daily.html", today=date.today().isoformat(), pill_labels=pill_labels)


# ---- BP quick entry (single-purpose, fast) ----

@app.route("/wearable", methods=["POST"])
def wearable():
    """JSON-only endpoint for the Android Health Connect bridge.

    Body shape:
        {
          "date": "2026-05-11",            (optional; defaults to today)
          "sleep_total_min": 387,          (optional)
          "sleep_score": 72,               (optional; 0-100 Samsung sleep score)
          "resting_hr_bpm": 58,            (optional)
          "spo2_overnight_low_pct": 92,    (optional)
          "steps_prev_day": 4823,          (optional)
          "bp_systolic": 116,              (optional; mmHg; requires bp_diastolic too)
          "bp_diastolic": 81,              (optional; mmHg; requires bp_systolic too)
          "bp_pulse": 79                   (optional; bpm; correlated to BP reading time)
        }

    Any field can be omitted; only present fields are written. Each field
    formats to its canonical health-log shape with appropriate doctor tags
    before being upserted into today's health-log section.

    Returns JSON {"ok": true, "fields_written": [...]} on success.
    """
    if not request.is_json:
        abort(400, "Content-Type must be application/json")

    payload = request.get_json(silent=True) or {}

    # Date stored on the submission row; the markdown upsert uses today's
    # header regardless because health-log.md is a daily journal, not a
    # multi-date archive. (Backfill is a separate manual workflow.)
    sub_date = payload.get("date") or date.today().isoformat()

    fields_written: list[str] = []

    sleep_min = payload.get("sleep_total_min")
    sleep_score = payload.get("sleep_score")
    if sleep_min is not None or sleep_score is not None:
        parts = []
        if sleep_min is not None:
            try:
                m = int(sleep_min)
                parts.append(f"{m // 60}h {m % 60}m")
            except (TypeError, ValueError):
                pass
        if sleep_score is not None:
            try:
                parts.append(f"score {int(sleep_score)}/100")
            except (TypeError, ValueError):
                pass
        if parts:
            storage.upsert_health_log_field("Sleep (wearable)", f"{', '.join(parts)} #psych #pulm")
            fields_written.append("Sleep (wearable)")

    rhr = payload.get("resting_hr_bpm")
    if rhr is not None:
        try:
            storage.upsert_health_log_field("Resting HR", f"{int(rhr)} bpm #cardio")
            fields_written.append("Resting HR")
        except (TypeError, ValueError):
            pass

    spo2 = payload.get("spo2_overnight_low_pct")
    if spo2 is not None:
        try:
            storage.upsert_health_log_field("SpO2 (overnight low)", f"{int(spo2)}% #pulm")
            fields_written.append("SpO2 (overnight low)")
        except (TypeError, ValueError):
            pass

    steps = payload.get("steps_prev_day")
    if steps is not None:
        try:
            storage.upsert_health_log_field("Steps (prev day)", f"{int(steps)} #bariatric #cardio")
            fields_written.append("Steps (prev day)")
        except (TypeError, ValueError):
            pass

    bp_sys = payload.get("bp_systolic")
    bp_dia = payload.get("bp_diastolic")
    bp_pulse = payload.get("bp_pulse")
    if bp_sys is not None and bp_dia is not None:
        try:
            sys_i, dia_i = int(bp_sys), int(bp_dia)
            bp_value = f"{sys_i}/{dia_i}"
            if bp_pulse is not None:
                try:
                    bp_value += f", {int(bp_pulse)} bpm"
                except (TypeError, ValueError):
                    pass
            storage.upsert_health_log_field("BP", f"{bp_value} #cardio")
            fields_written.append("BP")
        except (TypeError, ValueError):
            pass

    if not fields_written:
        abort(400, "no recognized fields in payload")

    storage.save_submission(
        "wearable",
        {**payload, "fields_written": fields_written},
        subkind=sub_date,
    )

    return {"ok": True, "fields_written": fields_written}


@app.route("/wearable/bulk", methods=["POST"])
def wearable_bulk():
    """Batch ingest endpoint for the Capacitor-wrapped Android app.

    Body shape:
      {"records": [ {record_type, hc_record_uid, ...type-specific fields}, ... ]}

    For each record:
      - Look up record_type in the insert dispatcher.
      - If known, INSERT OR IGNORE (idempotent by hc_record_uid).
      - If unknown, append to skipped_types but do not fail the batch.

    After inserts, collect the unique dates touched by any record's
    time / start_time, run summarize_date for each, return counts.
    """
    from datetime import date as _date

    from src import wearable_summary
    from src.storage import connect as storage_connect, insert_hc_record

    if not request.is_json:
        abort(400, "Content-Type must be application/json")
    payload = request.get_json(silent=True) or {}
    records = payload.get("records") or []
    if not isinstance(records, list):
        abort(400, "records must be a list")

    counts: dict[str, int] = {}
    skipped_types: list[str] = []
    dates_touched: set[str] = set()

    with storage_connect() as conn:
        for rec in records:
            rtype = rec.get("record_type")
            if rtype is None:
                continue
            try:
                inserted = insert_hc_record(rec, conn=conn)
            except ValueError:
                if rtype not in skipped_types:
                    skipped_types.append(rtype)
                continue
            counts[rtype] = counts.get(rtype, 0) + (1 if inserted else 0)

            time_value = rec.get("time") or rec.get("start_time") or rec.get("end_time")
            if time_value:
                dates_touched.add(time_value[:10])

    dates_summarized = sorted(dates_touched)
    for d_str in dates_summarized:
        wearable_summary.summarize_date(_date.fromisoformat(d_str))

    return {
        "ok": True,
        "counts": counts,
        "skipped_types": skipped_types,
        "dates_summarized": dates_summarized,
    }


@app.route("/bp", methods=["GET", "POST"])
def bp():
    """Single-purpose BP entry. Meant to be opened from the phone right after
    Breakfast meds. Three numbers, one tap."""
    if request.method == "POST":
        f = request.form
        bp_sys = (f.get("bp_sys") or "").strip()
        bp_dia = (f.get("bp_dia") or "").strip()
        bp_pulse = (f.get("bp_pulse") or "").strip()
        if not (bp_sys and bp_dia):
            abort(400, "systolic and diastolic both required")
        bp_value = f"{bp_sys}/{bp_dia}"
        if bp_pulse:
            bp_value += f", {bp_pulse} bpm"
        sub_id = storage.save_submission("bp", {
            "systolic": bp_sys, "diastolic": bp_dia, "pulse": bp_pulse,
        })
        storage.save_daily_observation({
            "date": date.today().isoformat(),
            "systolic": int(bp_sys),
            "diastolic": int(bp_dia),
            "pulse_from_bp_device": int(bp_pulse) if bp_pulse else None,
            "source": "manual_form",
            "source_record_id": f"sub:{sub_id}",
        })
        storage.upsert_health_log_field("BP", f"{bp_value} #cardio")
        return redirect(url_for("submitted", kind="bp"))
    return render_template("bp.html", today=date.today().isoformat())


# ---- Body measurements (waist / hips / neck / upper arm / thigh) ----

@app.route("/measurements", methods=["GET", "POST"])
def measurements():
    """Periodic tape-measure log. Any subset of fields may be filled."""
    if request.method == "POST":
        f = request.form

        def _opt_float(key):
            v = (f.get(key) or "").strip()
            if not v:
                return None
            try:
                return float(v)
            except ValueError:
                abort(400, f"{key} must be a number")

        row = {
            "date": (f.get("date") or date.today().isoformat()).strip(),
            "waist_in": _opt_float("waist_in"),
            "hips_in": _opt_float("hips_in"),
            "neck_in": _opt_float("neck_in"),
            "upper_arm_in": _opt_float("upper_arm_in"),
            "thigh_in": _opt_float("thigh_in"),
            "measurement_time": (f.get("measurement_time") or "").strip() or None,
            "measurement_method": (f.get("measurement_method") or "").strip() or None,
            "notes": (f.get("notes") or "").strip() or None,
            "source": "manual_form",
        }
        if not any(row[k] is not None for k in
                   ("waist_in", "hips_in", "neck_in", "upper_arm_in", "thigh_in")):
            abort(400, "at least one measurement must be filled")
        storage.save_body_measurement(row)
        return redirect(url_for("submitted", kind="measurements"))
    return render_template("measurements.html", today=date.today().isoformat())


# ---- Medication events (start / dose_change / pause / restart / stop / refill) ----

@app.route("/medications", methods=["GET", "POST"])
def medications():
    """Append-only ledger of medication events. The active dose for any
    medication is the most recent non-stop event for that medication."""
    if request.method == "POST":
        f = request.form
        name = (f.get("medication_name") or "").strip()
        event_type = (f.get("event_type") or "").strip()
        if not name:
            abort(400, "medication_name required")
        if not event_type:
            abort(400, "event_type required")

        dose = (f.get("dose") or "").strip() or None
        dose_numeric = None
        if dose:
            import re as _re
            m = _re.match(r"^\s*([\d.]+)", dose)
            if m:
                try:
                    dose_numeric = float(m.group(1))
                except ValueError:
                    dose_numeric = None

        row = {
            "date": (f.get("date") or date.today().isoformat()).strip(),
            "medication_name": name,
            "generic_name": (f.get("generic_name") or "").strip() or None,
            "dose": dose,
            "dose_numeric": dose_numeric,
            "dose_unit": (f.get("dose_unit") or "").strip() or None,
            "route": (f.get("route") or "").strip() or None,
            "frequency": (f.get("frequency") or "").strip() or None,
            "event_type": event_type,
            "reason": (f.get("reason") or "").strip() or None,
            "prescribing_context": (f.get("prescribing_context") or "").strip() or None,
            "notes": (f.get("notes") or "").strip() or None,
            "source": "manual_form",
        }
        storage.save_medication_event(row)
        return redirect(url_for("submitted", kind="medications"))
    return render_template("medications.html", today=date.today().isoformat())


# ---- Clinical events (surgery / follow-up / sleep study / academic markers) ----

@app.route("/events", methods=["GET", "POST"])
def events():
    """Discrete clinical or life events that anchor the projection model."""
    if request.method == "POST":
        f = request.form
        event_type = (f.get("event_type") or "").strip()
        category = (f.get("category") or "").strip()
        label = (f.get("label") or "").strip()
        if not (event_type and category and label):
            abort(400, "event_type, category, and label are required")

        def _opt_float(key):
            v = (f.get(key) or "").strip()
            if not v:
                return None
            try:
                return float(v)
            except ValueError:
                abort(400, f"{key} must be a number")

        row = {
            "date": (f.get("date") or date.today().isoformat()).strip(),
            "event_type": event_type,
            "category": category,
            "label": label,
            "certainty": (f.get("certainty") or "").strip() or None,
            "ahi": _opt_float("ahi"),
            "cpap_pressure": (f.get("cpap_pressure") or "").strip() or None,
            "cpap_hours": _opt_float("cpap_hours"),
            "mask_type": (f.get("mask_type") or "").strip() or None,
            "notes": (f.get("notes") or "").strip() or None,
            "source": "manual_form",
        }
        storage.save_clinical_event(row)
        return redirect(url_for("submitted", kind="events"))
    return render_template("events.html", today=date.today().isoformat())


# ---- Scales ----

@app.route("/scale/<scale_id>", methods=["GET", "POST"])
def scale(scale_id):
    try:
        scale_def = scales.load_scale(scale_id)
    except FileNotFoundError:
        abort(404)

    if request.method == "POST":
        responses = []
        for i in range(len(scale_def["items"])):
            raw = request.form.get(f"q{i}")
            if raw is None:
                abort(400, f"missing answer for item {i+1}")
            responses.append(int(raw))

        result = scales.score(scale_def, responses)
        storage.save_submission(
            "scale",
            {"responses": responses, "items": scale_def["items"]},
            subkind=scale_id,
            score=result["score"],
            band=result["band"],
        )
        _append_scale_markdown(scale_def, responses, result)
        return render_template("scale_result.html", scale=scale_def, result=result, responses=responses)

    return render_template("scale.html", scale=scale_def)


def _append_scale_markdown(scale_def: dict, responses: list[int], result: dict) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"## {scale_def['name']} — {ts}", "", f"- **Score:** {result['score']} ({result['band']})", ""]
    for i, (item, val) in enumerate(zip(scale_def["items"], responses)):
        lines.append(f"- ({val}) {item}")
    storage.append_mental_health_log("\n".join(lines))


# ---- Today dashboard ----

@app.route("/today")
def today():
    if build_today is None:
        abort(404, "The /today dashboard requires an external life-os integration "
                   "(see config.yaml integrations.life_os_scripts_path). Not configured.")
    data = build_today()
    resp = app.make_response(render_template("today.html", t=data))
    # Force no-cache — the dashboard must reflect live state on every load.
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


# ---- Food log ----

VALID_MEALS = {"breakfast", "lunch", "dinner", "snacks"}


@app.route("/food-log/<meal>", methods=["GET", "POST"])
def food_log(meal):
    meal_l = meal.lower()
    if meal_l not in VALID_MEALS:
        abort(404)

    if request.method == "POST":
        items = []
        for i in range(10):  # support up to 10 rows per post
            name = request.form.get(f"item_{i}", "").strip()
            qty = request.form.get(f"qty_{i}", "").strip()
            if name and qty:
                items.append({"item": name, "qty": qty})
        if not items:
            abort(400, "submit at least one item with a quantity")
        results = food_log_writer.append_meal_items(meal_l, items)
        storage.save_submission(
            "food_log",
            {"items": items, "results": [
                {k: v for k, v in r.items() if k != "macros"} for r in results
            ]},
            subkind=meal_l,
        )
        scaled = sum(1 for r in results if r["scaled"])
        missing = [r["item"] for r in results if not r["scaled"]]
        msg = f"{meal_l.capitalize()} logged. {scaled}/{len(results)} scaled from library."
        if missing:
            msg += f" Missing from library: {', '.join(missing)} — macros written as TBD."
        return render_template("submitted.html", kind="food-log", message=msg)

    return render_template(
        "food_log.html",
        meal=meal_l.capitalize(),
        today=date.today().isoformat(),
        products=food_log_writer.product_names(),
    )


# ---- Activity confirmation ----

@app.route("/activity/done", methods=["GET"])
def activity_done():
    text = request.args.get("text", "").strip()
    if not text:
        abort(400, "missing activity text")
    storage.save_submission("activity", {"text": text})
    storage.append_activity_log(text)
    return render_template("submitted.html", kind="activity", message=f"Logged: {text}")


@app.route("/activity-nudge-ack", methods=["GET", "POST"])
def activity_nudge_ack():
    """Called internally by scheduler to record that a nudge was *fired*."""
    storage.save_submission("activity_nudge", {"via": "scheduler"})
    return "ok", 200


# ---- Status / heartbeat ----

@app.route("/health-check")
def health_check():
    return {"status": "ok", "time": datetime.now().isoformat()}


@app.route("/submitted/<kind>")
def submitted(kind):
    return render_template("submitted.html", kind=kind, message=None)


# ---- PWA: service worker must be served from root scope ----

@app.route("/sw.js")
def service_worker():
    static_dir = Path(__file__).parent / "static"
    response = send_from_directory(static_dir, "sw.js", mimetype="application/javascript")
    # Allow root scope; required because the file is registered against '/'.
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


if __name__ == "__main__":
    cfg = load_config()["app"]
    app.run(host=cfg["host"], port=cfg["port"], debug=False)
