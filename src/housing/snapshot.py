"""Manual monthly observation notes, separate from experimental signal snapshots."""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .catalog import SERIES
from .db import latest
from .read_model import monthly


def _reference_month(series_id, source_period):
    """Observation month, independent of the later date a release became public."""
    details = SERIES[series_id]
    if details[5] != "annual":
        return source_period[:7]
    # Annual observations refer to a particular month, not the whole year.
    # Unknown annual definitions use year-end rather than assuming January.
    month = {"October survey": "10", "July 1 estimate": "07"}.get(details[6], "12")
    return f"{source_period}-{month}"


def build(db, period):
    values = monthly(db)
    if period not in values:
        raise ValueError(f"No observations for {period}")
    today = datetime.now(ZoneInfo("America/Toronto"))
    if period >= today.strftime("%Y-%m"):
        raise ValueError("The selected month is not complete")
    references = {}
    missing = []
    not_current = []
    for series_id, details in SERIES.items():
        rows = latest(db, series_id)
        selected = [r for r in rows if _reference_month(series_id, r["period"]) <= period]
        if not selected:
            missing.append(series_id)
            continue
        source_period = selected[-1]["period"]
        source_month = source_period if details[5] == "annual" else source_period[:7]
        if source_month != (period[:4] if details[5] == "annual" else period):
            not_current.append(series_id)
        if details[5] == "daily" and series_id == "goc_5y_yield":
            used = [r for r in selected if r["period"][:7] == source_month]
        else:
            used = [selected[-1]]
        references[series_id] = {
            "source_period": source_period,
            "reference_month": _reference_month(series_id, source_period),
            "source_frequency": details[5],
            "ids": [r["id"] for r in used],
            "versions": [r["version"] for r in used],
            "raw_sha256": sorted(set(r["raw_sha256"] for r in used)),
            "value": selected[-1]["value"] if details[5] == "annual" else values.get(source_month, {}).get(series_id),
        }
    return {
        "kind": "monthly_observation",
        "period": period,
        "saved_at": today.isoformat(timespec="seconds"),
        "values_for_period": values[period],
        "inputs": references,
        "missing_series": missing,
        "no_new_value_for_selected_month": not_current,
        "note": "Observation record only; no recovery score or prediction. Source months can differ. Latest stored revisions are used; this is not a reconstruction of information available at the selected historic date.",
    }

def save(db, period, folder):
    snapshot = build(db, period)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(ZoneInfo("America/Toronto")).strftime("%Y%m%dT%H%M%S%f")
    target = folder / f"observation-{period}-{stamp}.json"
    with target.open("x") as output:
        json.dump(snapshot, output, ensure_ascii=False, indent=2)
    return target

def open_snapshot(path):
    value = json.loads(Path(path).read_text())
    if value.get("kind") != "monthly_observation":
        raise ValueError("Not a monthly observation record")
    return value
