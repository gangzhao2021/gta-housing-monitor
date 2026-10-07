"""Per-series publication cadence and freshness assessment.

Period lag is measured against the latest completed Toronto calendar month;
it is not the elapsed number of days since the source file was downloaded.
"""
from dataclasses import dataclass
from datetime import date

from .catalog import SERIES
from .db import latest


@dataclass(frozen=True)
class FreshnessRule:
    cadence: str
    release_rule: str
    schedule: str


RULES = {
    "boc_policy_rate": FreshnessRule("monthly_view", "month_end", "每日公布；只按最近完整月判断"),
    "goc_5y_yield": FreshnessRule("monthly_view", "month_end", "交易日公布；只按最近完整月判断"),
    "mortgage_uninsured_fixed_5plus": FreshnessRule("monthly", "day_21", "通常在所属月后次月第三周发布；按次月 21 日作保守截止"),
    "toronto_unemployment_rate": FreshnessRule("monthly", "lfs_calendar", "按 Statistics Canada 劳动力调查年度发布日期表"),
    "toronto_employment_rate": FreshnessRule("monthly", "lfs_calendar", "按 Statistics Canada 劳动力调查年度发布日期表"),
    "toronto_participation_rate": FreshnessRule("monthly", "lfs_calendar", "按 Statistics Canada 劳动力调查年度发布日期表"),
    "trreb_sales": FreshnessRule("monthly", "day_15", "每月报告；次月 15 日作保守检查日，不是官方保证"),
    "trreb_new_listings": FreshnessRule("monthly", "day_15", "每月报告；次月 15 日作保守检查日，不是官方保证"),
    "trreb_active_listings": FreshnessRule("monthly", "day_15", "每月报告；次月 15 日作保守检查日，不是官方保证"),
    "trreb_hpi_composite": FreshnessRule("monthly", "day_15", "每月报告；次月 15 日作保守检查日，不是官方保证"),
    "trreb_hpi_benchmark": FreshnessRule("monthly", "day_15", "每月报告；次月 15 日作保守检查日，不是官方保证"),
    "toronto_cma_2011_starts": FreshnessRule("monthly", "cmhc_day_11", "每月第 11 个工作日；按次月 18 日保守检查"),
    "toronto_cma_2011_completions": FreshnessRule("monthly", "cmhc_day_11", "每月第 11 个工作日；按次月 18 日保守检查"),
    "toronto_cma_2011_under_construction": FreshnessRule("monthly", "cmhc_day_11", "每月第 11 个工作日；按次月 18 日保守检查"),
    "toronto_cma_2021_population": FreshnessRule("annual", "jan_31", "年度 7 月 1 日估计；次年 1 月内保守等待"),
    "wti_cushing_spot_price": FreshnessRule("monthly", "day_15", "EIA 月度均价；次月 15 日为本地检查日，非官方保证"),
    "usd_cad_monthly": FreshnessRule("monthly", "month_end", "BoC 月均汇率通常于当月最后营业日公布"),
    "boc_energy_price_index": FreshnessRule("monthly", "next_month_end", "BoC 月度能源指数；次月底为本地检查日，历史值可能修订"),
    "toronto_residential_construction_cost_index": FreshnessRule("quarterly", "quarter_plus_45", "StatsCan 季度建筑造价；季度结束后 45 日为本地检查日，非官方保证"),
    "ontario_net_interprovincial_migration": FreshnessRule("quarterly", "quarter_plus_90", "StatsCan 季度人口估计；季度结束后 90 日为保守检查日，非官方发布保证"),
    "ontario_net_international_migration": FreshnessRule("quarterly", "quarter_plus_90", "StatsCan 季度人口估计；季度结束后 90 日为保守检查日，非官方发布保证"),
}

RULES.update({series_id: FreshnessRule("annual", "jan_31", "CMHC 年度 10 月租赁调查；保守等待至次年 1 月底")
              for series_id, definition in SERIES.items() if definition[1] == "CMHC"})

LFS_RELEASES = {
    "2025-12": date(2026, 1, 9), "2026-01": date(2026, 2, 6),
    "2026-02": date(2026, 3, 13), "2026-03": date(2026, 4, 10),
    "2026-04": date(2026, 5, 8), "2026-05": date(2026, 6, 5),
    "2026-06": date(2026, 7, 10), "2026-07": date(2026, 8, 7),
    "2026-08": date(2026, 9, 4), "2026-09": date(2026, 10, 9),
    "2026-10": date(2026, 11, 6), "2026-11": date(2026, 12, 4),
    "2026-12": date(2027, 1, 8), "2027-01": date(2027, 2, 5),
    "2027-02": date(2027, 3, 12),
}


def _month_index(period):
    year, month = map(int, period.split("-"))
    return year * 12 + month - 1


def _month_string(index):
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def _due_date(rule, period):
    if rule == "jan_31":
        return date(int(period) + 1, 1, 31)
    if rule in ("quarter_plus_45", "quarter_plus_90"):
        from calendar import monthrange
        from datetime import timedelta
        year, month = map(int, period.split("-"))
        end_month = month + 2
        return date(year, end_month, monthrange(year, end_month)[1]) + timedelta(days=45 if rule == "quarter_plus_45" else 90)
    year, month = map(int, period.split("-"))
    if rule == "month_end":
        from calendar import monthrange
        return date(year, month, monthrange(year, month)[1])
    if rule == 'two_months_end':
        from calendar import monthrange
        target = year * 12 + month - 1 + 2
        y, m = target // 12, target % 12 + 1
        return date(y, m, monthrange(y, m)[1])
    year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    if rule == "next_month_end":
        from calendar import monthrange
        return date(year, month, monthrange(year, month)[1])
    if rule == "lfs_calendar":
        return LFS_RELEASES.get(period, date(year, month, 15))
    day = {"day_15": 15, "day_21": 21, "cmhc_day_11": 18}[rule]
    return date(year, month, day)


def assess(db, series_id, today=None):
    """Return latest usable period, expected period, lag, and display status."""
    today = today or date.today()
    rule = RULES.get(series_id)
    if rule is None:
        return {"status": "unknown", "latest_period": None, "expected_period": None,
                "lag": None, "missing_periods": []}

    observations = latest(db, series_id)
    if rule.cadence == 'archived':
        return {'status': 'archived', 'latest_period': observations[-1]['period'] if observations else None,
                'expected_period': '2023-10', 'lag': None, 'missing_periods': [], 'internal_gaps': []}

    if rule.cadence == "annual":
        expected_period = str(today.year - 1)
        usable = [row for row in observations if row["period"] <= expected_period]
        latest_period = usable[-1]["period"] if usable else None
        missing_periods = [expected_period] if not latest_period or latest_period < expected_period else []
        if not latest_period:
            status = "missing"
        elif latest_period == expected_period:
            status = "current"
        else:
            status = "pending" if today < _due_date(rule.release_rule, expected_period) else "overdue"
        return {"status": status, "latest_period": latest_period,
                "expected_period": expected_period, "lag": (int(expected_period) - int(latest_period)) if latest_period else None,
                "missing_periods": missing_periods, "internal_gaps": []}

    if rule.cadence == "quarterly":
        current_quarter = (today.month - 1) // 3
        target_quarter = today.year * 4 + current_quarter - 1
        expected_period = f"{target_quarter // 4:04d}-{target_quarter % 4 * 3 + 1:02d}"
        usable = [row for row in observations if row["period"] <= expected_period]
        latest_period = usable[-1]["period"] if usable else None
        lag = (target_quarter - (int(latest_period[:4]) * 4 + (int(latest_period[5:]) - 1) // 3)
               if latest_period else None)
        missing_periods = [f"{q // 4:04d}-{q % 4 * 3 + 1:02d}"
                           for q in range(target_quarter - lag + 1, target_quarter + 1)] if lag else [expected_period] if latest_period is None else []
        status = ("missing" if latest_period is None else "current" if not lag else
                  "pending" if today < _due_date(rule.release_rule, missing_periods[0]) else "overdue")
        return {"status": status, "latest_period": latest_period,
                "expected_period": expected_period, "lag": lag,
                "missing_periods": missing_periods, "internal_gaps": []}

    target_index = today.year * 12 + today.month - 2  # last completed month
    expected_period = _month_string(target_index)
    # Daily series are represented monthly in the dashboard; ignore any partial current month.
    usable = [row for row in observations if row["period"][:7] <= expected_period]
    latest_period = usable[-1]["period"][:7] if usable else None
    if latest_period is None:
        lag = None
        missing_periods = [expected_period]
        status = "missing"
    else:
        lag = target_index - _month_index(latest_period)
        status = "current" if lag == 0 else "pending"
        missing_periods = []
        if rule.cadence in ("monthly", "monthly_view") and lag > 0:
            latest_index = _month_index(latest_period)
            missing_periods = [_month_string(i) for i in range(latest_index + 1, target_index + 1)]
            status = "pending" if today < _due_date(rule.release_rule, missing_periods[0]) else "overdue"

    # Detect holes inside the recent observed span separately from not-yet-released periods.
    internal_gaps = []
    if rule.cadence == "monthly" and latest_period:
        first_index = max(_month_index(latest_period) - 11, _month_index(observations[0]["period"][:7]))
        known = {row["period"][:7] for row in observations}
        internal_gaps = [_month_string(i) for i in range(first_index, _month_index(latest_period))
                         if _month_string(i) not in known]
    return {"status": status, "latest_period": latest_period,
            "expected_period": expected_period, "lag": lag,
            "missing_periods": missing_periods, "internal_gaps": internal_gaps}


STATUS_LABELS = {
    "current": "最近应发布期已到",
    "pending": "未到保守检查日，等待更新",
    "overdue": "超过保守检查日",
    "missing": "没有可用观测",
    "internal_gap": "历史序列内部缺月",
    "unknown": "未登记发布节奏",
}


RULES.update({series_id: FreshnessRule("monthly", "day_15", "每月报告；次月 15 日为本地检查日，不是官方承诺")
              for series_id in SERIES if series_id.startswith(("toronto_asking_rent_", "regional_asking_"))})


RULES.update({series_id: FreshnessRule("monthly", "day_15", "随 TRREB 月报公布；次月 15 日作保守检查日，不是官方保证")
              for series_id in SERIES if series_id.endswith("_yoy_published")})
RULES.update({series_id: FreshnessRule("quarterly", "quarter_plus_45", "TRREB 季度租赁报告；季度结束后 45 日为本地检查日，非官方保证")
              for series_id in SERIES if series_id.startswith("gta_condo_lease")})


from .background_series import CONFIG as BACKGROUND_CONFIG
STATUS_LABELS['archived'] = '来源已停更（历史表）'
for key, config in BACKGROUND_CONFIG.items():
    archived = config.get('archived', False)
    rule = 'month_end' if key.startswith('boc_') else 'two_months_end' if key == 'toronto_permits' else 'next_month_end'
    RULES[config['id']] = FreshnessRule('archived' if archived else 'monthly', rule,
        '历史表于 2023-10 停更' if archived else '本地保守检查日：报价当月底、价格指数次月底、建筑许可隔月底；不是官方保证')
