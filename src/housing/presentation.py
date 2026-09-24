"""Calendar-aware views shared by dashboard cards, charts, and downloads.

These views describe observation periods, not what was known at a historic date.
They deliberately do not fill missing observations with older values or zeros.
"""
from datetime import date
from math import isfinite

from .db import latest


def _period_parts(period):
    if len(period) == 4 and period.isdigit():
        date(int(period), 1, 1)
        return int(period), None
    if len(period) == 7 and period[4] == "-":
        year, month = map(int, period.split("-"))
        date(year, month, 1)
        return year, month
    raise ValueError(f"Expected YYYY or YYYY-MM observation period, got {period!r}")


def calendar_periods(start, end):
    """Return every annual or monthly period in the inclusive range."""
    start_year, start_month = _period_parts(start)
    end_year, end_month = _period_parts(end)
    if (start_month is None) != (end_month is None):
        raise ValueError("Start and end must have the same frequency")
    if start > end:
        raise ValueError("Start must not be after end")
    if start_month is None:
        return [f"{year:04d}" for year in range(start_year, end_year + 1)]
    first = start_year * 12 + start_month - 1
    last = end_year * 12 + end_month - 1
    return [f"{month // 12:04d}-{month % 12 + 1:02d}" for month in range(first, last + 1)]


def _number(value):
    return value if value is not None and isfinite(value) else None


def metric_at(data, field, period, unit=""):
    """Read the exact period and calendar YoY; rate changes use percentage points.

    A missing period or missing prior calendar year suppresses the comparison.
    A prior zero also suppresses relative growth, but remains valid for rate deltas.
    """
    year, month = _period_parts(period)
    previous_period = f"{year - 1:04d}" + (f"-{month:02d}" if month else "")
    value = _number(data.get(period, {}).get(field))
    previous = _number(data.get(previous_period, {}).get(field))
    delta = None
    delta_unit = "百分点" if unit == "%" else "月" if unit == "月" else "%"
    if value is not None and previous is not None:
        if unit in ("%", "月"):
            delta = value - previous
        elif previous != 0:
            delta = (value / previous - 1) * 100
    return {
        "period": period,
        "value": value,
        "previous_period": previous_period,
        "previous_value": previous,
        "delta": delta,
        "delta_unit": delta_unit,
    }


def available_periods(data, fields):
    """Periods having at least one observation from the section's own fields."""
    return sorted(period for period, values in data.items()
                  if any(_number(values.get(field)) is not None for field in fields))


def scoped_rows(data, fields, start, end):
    """Rows for the same selected scope used by displays and CSV downloads."""
    return [{"period": period,
             **{field: _number(data.get(period, {}).get(field)) for field in fields}}
            for period in calendar_periods(start, end)]


def chart_rows(data, field, start, end):
    """Return chart points with explicit segments so lines cannot bridge gaps.

    Use ``segment`` as the chart's grouping/detail field. Missing rows stay in the
    returned data for tooltips/tables; their value is None, never zero.
    """
    segment = 0
    result = []
    for row in scoped_rows(data, [field], start, end):
        value = row[field]
        if value is None:
            segment += 1
        result.append({"period": row["period"], "value": value, "segment": segment})
    return result


def annual_data(db, fields):
    """Read annual observations separately from the monthly calendar."""
    result = {}
    for field in fields:
        for row in latest(db, field):
            year, month = _period_parts(row["period"])
            if month is not None:
                raise ValueError(f"{field} contains monthly observations, not annual")
            result.setdefault(f"{year:04d}", {})[field] = row["value"]
    return dict(sorted(result.items()))


def period_label(period):
    """Human-readable Chinese period label without a misleading frequency suffix."""
    if len(period) == 10:
        value = date.fromisoformat(period)
        return f"{value.year}年{value.month}月{value.day}日"
    year, month = _period_parts(period)
    return f"{year}年{month}月" if month else f"{year}年"
