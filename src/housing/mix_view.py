"""Shared owner/viewer price-band mix: 100% stacked columns linked to the page's observation month."""
from html import escape

from .i18n import english, st

BANDS = ("under_500k", "500k_800k", "800k_1m", "1m_1_5m", "1_5m_2m", "2m_plus")
LABELS = {"under_500k": ("50 万以下", "Under $500K"), "500k_800k": ("50–80 万", "$500K–$800K"),
          "800k_1m": ("80–100 万", "$800K–$1M"), "1m_1_5m": ("100–150 万", "$1M–$1.5M"),
          "1_5m_2m": ("150–200 万", "$1.5M–$2M"), "2m_plus": ("200 万以上", "$2M and over")}
COLORS = ("#9ad0d3", "#4fb0b6", "#007f86", "#2855d9", "#1b3a99", "#0f1f55")


def shares(series, period):
    counts = [series[band].get(period) for band in BANDS]
    if any(c is None for c in counts) or not sum(counts):
        return None
    total = sum(counts)
    return [c / total * 100 for c in counts]


def _shift(period, months):
    index = int(period[:4]) * 12 + int(period[5:7]) - 1 + months
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def render(get_series, end, month_key=None, selectable=()):
    """get_series(field) -> {period: value}. Clicking a column moves `month_key` to that month."""
    import altair as alt
    import pandas as pd
    import streamlit as native_st
    en = english()
    i = 1 if en else 0
    series = {band: get_series(f"trreb_sales_band_{band}") or {} for band in BANDS}
    periods = sorted(p for p in set().union(*series.values()) if shares(series, p))
    if not periods or not shares(series, end):
        return
    window = [p for p in periods if p <= max(end, periods[-1])][-25:]
    if end < window[0]:
        window = [p for p in periods if p <= end][-25:]
    names = [LABELS[b][i] for b in BANDS]
    rows = [{"period": p, "band": names[k], "order": k, "share": v}
            for p in window for k, v in enumerate(shares(series, p))]
    native_st.subheader("Sales by price band" if en else "成交价格段构成")
    left, right = native_st.columns([1.7, 1], gap="large")
    column = alt.selection_point(fields=["period"], name="column")
    focus = alt.selection_point(fields=["band"], bind="legend", name="focus")
    chart = alt.Chart(pd.DataFrame(rows)).mark_bar().encode(
        x=alt.X("period:O", title=None, axis=alt.Axis(labelAngle=0, labelExpr="slice(datum.value, 2, 4) + '/' + slice(datum.value, 5)",
                                                      values=window[::6] + ([window[-1]] if (len(window) - 1) % 6 else []))),
        y=alt.Y("share:Q", title=None, stack="normalize", axis=alt.Axis(format="%")),
        color=alt.Color("band:N", sort=names, scale=alt.Scale(domain=names, range=list(COLORS)),
                        legend=alt.Legend(title=None, orient="top", columns=6)),
        order=alt.Order("order:Q"),
        opacity=alt.condition(focus, alt.value(1), alt.value(0.22)),
        stroke=alt.condition(alt.datum.period == end, alt.value("#171717"), alt.value(None)),
        strokeWidth=alt.condition(alt.datum.period == end, alt.value(1.5), alt.value(0)),
        tooltip=[alt.Tooltip("period:O", title="Month" if en else "月份"), alt.Tooltip("band:N", title="Band" if en else "价格段"),
                 alt.Tooltip("share:Q", format=".1f", title="Share (%)" if en else "占比（%）")],
    ).add_params(column, focus).properties(height=260)
    options = set(selectable)

    def jump():
        picked = (native_st.session_state.get(f"bands-{month_key}") or {}).get("selection", {}).get("column") or []
        period = picked[0].get("period") if picked else None
        if period in options:
            native_st.session_state[month_key] = period

    with left:
        if month_key and options:
            native_st.altair_chart(chart, use_container_width=True, on_select=jump, selection_mode="column", key=f"bands-{month_key}")
        else:
            native_st.altair_chart(chart, use_container_width=True)
    now, before = shares(series, end), shares(series, _shift(end, -12))
    first, last = shares(series, window[0]), shares(series, window[-1])
    change = [b - a for a, b in zip(first, last)]
    up, down = change.index(max(change)), change.index(min(change))
    month = end if en else f"{end[:4]} 年 {int(end[5:7])} 月"
    rows_html = "".join(
        f'<div class="mix-row"><span><i style="background:{COLORS[k]}"></i>{escape(names[k])}</span><b>{now[k]:.1f}%</b>'
        f'<small>{"—" if before is None else format(now[k] - before[k], "+.1f").replace("-", "−")}</small></div>'
        for k in range(len(BANDS)))
    with right:
        native_st.markdown(
            f"From {window[0]} to {window[-1]}, {names[up]} went from {first[up]:.1f}% to {last[up]:.1f}% of sales; {names[down]} from {first[down]:.1f}% to {last[down]:.1f}%."
            if en else f"{window[0]} 到 {window[-1]}，{names[up]}的占比从 {first[up]:.1f}% 变为 {last[up]:.1f}%，{names[down]}从 {first[down]:.1f}% 变为 {last[down]:.1f}%。")
        st.html(f'<div class="mix-detail"><strong>{escape(month)}{" · change vs a year earlier (pp)" if en else " · 较上年同月（个百分点）"}</strong>{rows_html}</div>')
        native_st.caption("Select a column to change the month; select a legend item to focus on one band. Reflects the sales mix, not a price index."
                          if en else "点柱子切换观察月份；点图例只看一个价格段。反映成交构成，不是房价指数。")
