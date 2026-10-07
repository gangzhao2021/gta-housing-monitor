"""Market temperature: TRREB sales-to-new-listings ratio against its seasonal norm.

Supported by leading-indicator studies v3/v4 (docs/LEADING_STUDY_V4.md). This is a
descriptive reading of current market balance, not a forecast.

SNLR3(m) = 100 * sales(m-2..m) / new listings(m-2..m); the norm is the mean SNLR3 of
the same calendar month in all earlier years (at least three). Bands use +/-10
percentage points, chosen from the 2007+ distribution (roughly the outer quarter /
fifth of months) before display.
"""
import csv
import json
import math
from statistics import fmean

from .leading import shift
from .leading_v3 import HPI_SEGMENTS, moi3, snlr3, _norm

BAND = 10.0
ARCHIVE_END = '2022-08'


def _float(value):
    return float(value) if value not in (None, '') else None


def history(csv_path, db):
    """Archive months (2004..2022-08) from the research CSV, later months live from the database."""
    rows = {}
    with open(csv_path, newline='') as handle:
        for row in csv.DictReader(handle):
            if row['period'] <= ARCHIVE_END:
                rows[row['period']] = {k: _float(row[k]) for k in ('sales', 'new_listings', 'active_listings', 'hpi_index')}
    district = db.execute("""SELECT d.ym, d.values_json FROM district_observations d JOIN
        (SELECT ym, MAX(version) v FROM district_observations WHERE house_type='all_types' AND region='All TRREB Areas' GROUP BY ym) x
        ON d.ym=x.ym AND d.version=x.v WHERE d.house_type='all_types' AND d.region='All TRREB Areas'""").fetchall()
    hpi = dict(db.execute("""SELECT period, value FROM observations o WHERE series_id='trreb_hpi_composite'
        AND version=(SELECT MAX(version) FROM observations WHERE series_id=o.series_id AND period=o.period)""").fetchall())
    for ym, values in district:
        if ym > ARCHIVE_END:
            v = json.loads(values)
            rows[ym] = {'sales': v.get('sales'), 'new_listings': v.get('new_listings'),
                        'active_listings': v.get('active_listings'), 'hpi_index': hpi.get(ym)}
    return rows


def state(gap):
    return None if gap is None else 'cool' if gap <= -BAND else 'hot' if gap >= BAND else 'balanced'


def readings(rows):
    out = {}
    for m in sorted(rows):
        s, norm = snlr3(rows, m), _norm(snlr3, rows, m)
        if s is None or norm is None:
            continue
        moi, moi_norm = moi3(rows, m), _norm(lambda r, p: math.log(moi3(r, p)) if moi3(r, p) else None, rows, m)
        out[m] = {'snlr3': round(s, 2), 'snlr_norm': round(norm, 2), 'gap': round(s - norm, 2), 'state': state(s - norm),
                  'moi3': round(moi, 2) if moi else None,
                  'moi_norm': round(math.exp(moi_norm), 2) if moi_norm is not None else None}
    return out


def _segment(period):
    return next((i for i, (a, b) in enumerate(HPI_SEGMENTS) if a <= period <= b), None)


def outcomes(rows, by_month, horizon=12):
    """How deal-dated HPI moved over the following months after each state (descriptive, in-sample)."""
    result = {}
    for name in ('cool', 'balanced', 'hot'):
        changes = []
        for m, r in by_month.items():
            end = shift(m, horizon)
            a, b = rows.get(m, {}).get('hpi_index'), rows.get(end, {}).get('hpi_index')
            if r['state'] == name and a and b and _segment(m) is not None and _segment(m) == _segment(end):
                changes.append(100 * (b / a - 1))
        result[name] = {'n': len(changes), 'mean_change': round(fmean(changes), 1) if changes else None,
                        'share_up': round(sum(c > 0 for c in changes) / len(changes), 2) if changes else None}
    return result


def build(csv_path, db):
    rows = history(csv_path, db)
    by_month = readings(rows)
    return {'band_pp': BAND, 'months': by_month, 'outcomes_12m': outcomes(rows, by_month)}
