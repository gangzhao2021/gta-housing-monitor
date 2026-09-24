"""Deliberately small, path-free data contract for the display application."""
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .catalog import SERIES
from .db import latest

DISPLAY_SERIES = frozenset(
    key for key in SERIES if key.startswith((
        "trreb_", "toronto_asking_rent_", "regional_asking_", "toronto_pbr_",
        "toronto_condo_", "regional_cmhc_", "toronto_cma_2011_",
    )) or key in {
        "boc_policy_rate", "goc_5y_yield", "mortgage_uninsured_fixed_5plus",
        "toronto_unemployment_rate", "toronto_employment_rate",
        "toronto_participation_rate", "toronto_cma_2021_population",
    }
)


def build_display_snapshot(db, *, created_at=None):
    """Only latest numerical observations; never provenance paths or credentials."""
    observations = {}
    for key in sorted(DISPLAY_SERIES):
        rows = latest(db, key)
        if rows:
            observations[key] = {row["period"]: row["value"] for row in rows}
    return {
        "schema_version": 1,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "observations": observations,
    }


def validate_display_snapshot(value):
    if value.get("schema_version") != 1 or not isinstance(value.get("observations"), dict):
        raise ValueError("Unsupported display snapshot")
    if set(value["observations"]) - DISPLAY_SERIES:
        raise ValueError("Display snapshot contains a non-approved series")
    for series, periods in value["observations"].items():
        if not isinstance(periods, dict):
            raise ValueError(f"Invalid periods for {series}")
        for period, number in periods.items():
            if not isinstance(period, str) or not isinstance(number, (int, float)) or isinstance(number, bool):
                raise ValueError(f"Invalid display observation for {series}")
    return value


def publish(db_path, output):
    """Atomic replacement: a failed build leaves the last good snapshot intact."""
    db = sqlite3.connect(f"file:{Path(db_path).resolve()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        snapshot = validate_display_snapshot(build_display_snapshot(db))
    finally:
        db.close()
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(snapshot, stream, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def load_display_snapshot(path):
    return validate_display_snapshot(json.loads(Path(path).read_text(encoding="utf-8")))


def monthly_display(snapshot):
    """Transpose approved series to the existing chart model without private DB access."""
    from collections import defaultdict
    from statistics import mean

    from .metrics import resale_metrics, year_over_year

    result = defaultdict(dict)
    for series, periods in snapshot["observations"].items():
        if series == "goc_5y_yield":
            grouped = defaultdict(list)
            for period, value in periods.items():
                grouped[period[:7]].append(value)
            for period, values in grouped.items():
                result[period][series] = mean(values)
        else:
            for period, value in periods.items():
                result[period[:7] if series == "boc_policy_rate" else period][series] = value
    for period, values in result.items():
        if any(field in values for field in ("trreb_sales", "trreb_new_listings", "trreb_active_listings")):
            values.update(resale_metrics(values.get("trreb_sales"), values.get("trreb_new_listings"), values.get("trreb_active_listings")))
    for field in ("trreb_sales", "trreb_new_listings", "trreb_active_listings", "trreb_hpi_composite",
                  "toronto_cma_2011_starts", "toronto_cma_2011_completions", "toronto_cma_2011_under_construction"):
        source = {period: values[field] for period, values in result.items() if field in values}
        for period in source:
            result[period][field + "_yoy"] = year_over_year(source, period)
    return dict(sorted(result.items()))
