"""Deliberately small, path-free data contract for the display application."""
import json
import hashlib
import fcntl
import os
import shutil
import sqlite3
import math
import re
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
CONTEXT_SERIES = frozenset({
    "wti_cushing_spot_price", "usd_cad_monthly", "boc_energy_price_index",
    "toronto_residential_construction_cost_index",
})
from .background_series import CONFIG as BACKGROUND_CONFIG
CONTEXT_SERIES |= frozenset(c['id'] for c in BACKGROUND_CONFIG.values() if not c.get('archived'))


def build_display_snapshot(db, *, created_at=None):
    """Only latest numerical observations; never provenance paths or credentials."""
    observations = {}
    for key in sorted(DISPLAY_SERIES):
        rows = latest(db, key)
        if rows:
            observations[key] = {row["period"]: row["value"] for row in rows}
    context = {}
    for key in sorted(CONTEXT_SERIES):
        rows = latest(db, key)
        if rows:
            row = rows[-1]
            context[key] = {"period": row["period"], "value": row["value"]}
    from .districts import display_rows
    from .freshness import assess
    return {
        "schema_version": 2,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "observations": observations,
        "context": context,
        "districts": display_rows(db),
        "freshness": {key: assess(db, key) for key in sorted(DISPLAY_SERIES | CONTEXT_SERIES)},
    }


def validate_display_snapshot(value):
    if set(value) - {'schema_version', 'created_at', 'observations', 'context', 'districts', 'freshness'}:
        raise ValueError('Unexpected display snapshot fields')
    from .districts import FIELDS, TYPES
    seen = set()
    for row in value.get('districts', []):
        if set(row) != {'ym', 'house_type', 'region', *FIELDS}:
            raise ValueError('Unexpected district display fields')
        if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', row['ym']) or row['house_type'] not in TYPES:
            raise ValueError('Invalid district period or type')
        if not isinstance(row['region'], str) or not re.fullmatch(r"[A-Za-z0-9 ./'()&-]{1,100}", row['region']):
            raise ValueError('Invalid district region')
        key = (row['ym'], row['house_type'], row['region'])
        if key in seen:
            raise ValueError('Duplicate district display row')
        seen.add(key)
        if any(row[k] is not None and (not isinstance(row[k], (int, float)) or isinstance(row[k], bool)
                                      or not math.isfinite(row[k]) or row[k] < 0) for k in FIELDS):
            raise ValueError('Invalid district display value')
    for key, state in value.get('freshness', {}).items():
        if key not in DISPLAY_SERIES | CONTEXT_SERIES or set(state) - {'status', 'latest_period', 'expected_period', 'lag', 'missing_periods', 'internal_gaps'}:
            raise ValueError('Invalid display freshness metadata')
        if state.get('status') not in {'current', 'pending', 'overdue', 'missing', 'unknown', 'archived'}:
            raise ValueError('Invalid freshness status')
        for field in ('latest_period', 'expected_period'):
            period = state.get(field)
            if period is not None and (not isinstance(period, str) or not re.fullmatch(r'\d{4}(-(?:0[1-9]|1[0-2]))?', period)):
                raise ValueError('Invalid freshness period')
        for field in ('missing_periods', 'internal_gaps'):
            if not isinstance(state.get(field, []), list) or any(not isinstance(p, str) or not re.fullmatch(r'\d{4}(-(?:0[1-9]|1[0-2]))?', p) for p in state.get(field, [])):
                raise ValueError('Invalid freshness gaps')
        if state.get('lag') is not None and (not isinstance(state['lag'], int) or isinstance(state['lag'], bool)):
            raise ValueError('Invalid freshness lag')
    if value.get("schema_version") not in (1, 2) or not isinstance(value.get("observations"), dict):
        raise ValueError("Unsupported display snapshot")
    if value["schema_version"] == 2:
        context = value.get("context")
        if not isinstance(context, dict) or set(context) - CONTEXT_SERIES:
            raise ValueError("Display snapshot contains invalid context")
        for series, item in context.items():
            if not isinstance(item, dict) or set(item) != {"period", "value"}:
                raise ValueError(f"Invalid display context for {series}")
            pattern = r"\d{4}-(?:01|04|07|10)" if series == "toronto_residential_construction_cost_index" else r"\d{4}-(?:0[1-9]|1[0-2])"
            if (not isinstance(item["period"], str) or not re.fullmatch(pattern, item["period"])
                    or not isinstance(item["value"], (int, float)) or isinstance(item["value"], bool)
                    or not math.isfinite(item["value"])):
                raise ValueError(f"Invalid display context value for {series}")
    if set(value["observations"]) - DISPLAY_SERIES:
        raise ValueError("Display snapshot contains a non-approved series")
    for series, periods in value["observations"].items():
        if not isinstance(periods, dict):
            raise ValueError(f"Invalid periods for {series}")
        for period, number in periods.items():
            if not isinstance(period, str) or not isinstance(number, (int, float)) or isinstance(number, bool):
                raise ValueError(f"Invalid display observation for {series}")
            if not math.isfinite(number):
                raise ValueError('Non-finite display value')
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
    output.parent.chmod(0o700)
    history = output.parent / "display_history"
    history.mkdir(mode=0o700, exist_ok=True)
    history.chmod(0o700)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(snapshot, stream, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        lock_path = output.with_name(f".{output.name}.lock")
        with lock_path.open("a+b") as lock:
            lock_path.chmod(0o600)
            fcntl.flock(lock, fcntl.LOCK_EX)
            _archive_current(output, history)
            temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def _archive_current(output, history):
    if not output.is_file():
        return None
    try:
        load_display_snapshot(output)
    except (ValueError, OSError, json.JSONDecodeError):
        return None
    sha = hashlib.sha256(output.read_bytes()).hexdigest()
    archived = history / f"{sha}.json"
    if not archived.exists():
        os.link(output, archived)
    return archived


def restore_display_snapshot(output, sha):
    """Restore a previously validated snapshot without touching the database."""
    if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
        raise ValueError("Expected a full lowercase SHA-256 snapshot id")
    output = Path(output)
    history = output.parent / "display_history"
    archived = history / f"{sha}.json"
    if hashlib.sha256(archived.read_bytes()).hexdigest() != sha:
        raise ValueError("Archived snapshot hash differs")
    load_display_snapshot(archived)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.restore.tmp")
    try:
        lock_path = output.with_name(f".{output.name}.lock")
        with lock_path.open("a+b") as lock:
            lock_path.chmod(0o600)
            fcntl.flock(lock, fcntl.LOCK_EX)
            _archive_current(output, history)
            with archived.open("rb") as source, temporary.open("xb") as target:
                shutil.copyfileobj(source, target)
            temporary.chmod(0o600)
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
