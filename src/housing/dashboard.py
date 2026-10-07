"""Shared, calendar-aware Streamlit presentation components."""
from html import escape
from pathlib import Path
import altair as alt
import pandas as pd
from .i18n import st
from .catalog import SERIES
from .metric_help import help_label
from .presentation import calendar_periods, chart_rows, metric_at, period_label

TEAL, BLUE, ORANGE = "#007f86", "#2855d9", "#bf6517"


def series_color(field):
    """Keep each series' color stable when switching between combined and single views."""
    if field.startswith(("regional_asking_", "regional_cmhc_")):
        for region, color in [("north_york", TEAL), ("scarborough", ORANGE), ("markham", "#7952be"),
                              ("vaughan", "#aa4570"), ("mississauga", "#47689c"), ("oakville", "#648234"),
                              ("richmond_vaughan_king", "#aa4570"), ("aurora_newmarket_whit", "#7952be")]:
            if field.startswith(("regional_asking_" + region + "_", "regional_cmhc_" + region + "_")):
                return color
    if field.startswith("toronto_pbr_"):
        return TEAL
    if field.startswith("toronto_condo_"):
        return BLUE
    return {
        "toronto_asking_rent_1br": TEAL, "toronto_asking_rent_2br": BLUE,
        "toronto_asking_rent_3br": "#7952be",
        "trreb_hpi_benchmark": BLUE, "trreb_hpi_composite": BLUE,
        "trreb_sales": TEAL, "trreb_new_listings": ORANGE,
        "trreb_active_listings": ORANGE, "moi_raw": "#7952be", "snlr_raw": TEAL,
        "boc_policy_rate": BLUE, "goc_5y_yield": TEAL,
        "mortgage_uninsured_fixed_5plus": ORANGE,
        "toronto_unemployment_rate": ORANGE,
        "toronto_employment_rate": BLUE,
        "toronto_participation_rate": TEAL,
        "toronto_cma_2011_starts": BLUE,
        "toronto_cma_2011_completions": TEAL,
        "toronto_cma_2011_under_construction": ORANGE,
    }.get(field, BLUE)

LABELS = {
    "trreb_sales": "成交量", "trreb_new_listings": "新增挂牌", "trreb_active_listings": "月末有效挂牌",
    "moi_raw": "库存月数", "snlr_raw": "成交／新挂牌比", "trreb_hpi_composite": "HPI 综合指数",
    "trreb_hpi_benchmark": "HPI 综合基准房价", "boc_policy_rate": "央行政策利率",
    "goc_5y_yield": "五年国债收益率", "mortgage_uninsured_fixed_5plus": "新增固定按揭利率",
    "toronto_unemployment_rate": "失业率", "toronto_employment_rate": "就业率",
    "toronto_participation_rate": "劳动参与率", "toronto_cma_2011_starts": "住宅开工",
    "toronto_cma_2011_completions": "住宅竣工", "toronto_cma_2011_under_construction": "在建住宅",
    "toronto_cma_2021_population": "人口估计", "toronto_pbr_vacancy_rate": "专建出租 · 总空置率",
    "toronto_condo_vacancy_rate": "业主出租 condo · 总空置率",
}
UNITS = {"sales": "笔", "listings": "套", "CAD": "加元", "index": "指数", "units": "套", "persons": "人", "CAD/month": "加元 / 月"}


def label(field):
    return LABELS.get(field, SERIES[field][0] if field in SERIES else field)


def unit(field):
    return {"moi_raw": "月", "snlr_raw": "%"}.get(field, SERIES[field][4] if field in SERIES else "")


def formatted(value, field):
    if value is None:
        return "暂无数据"
    raw_unit = unit(field)
    digits = 2 if field in ("moi_raw", "boc_policy_rate", "goc_5y_yield", "mortgage_uninsured_fixed_5plus") else 1 if raw_unit in ("%", "index") else 0
    return ("$" if raw_unit in ("CAD", "CAD/month") else "") + f"{value:,.{digits}f}" + ("%" if raw_unit == "%" else "")


def css():
    st.html("<style>" + Path(__file__).with_suffix(".css").read_text() + "</style>")


def note(text):
    st.html(f'<div class="page-note">{escape(text)}</div>')


def rental_table(rows, markets):
    body = []
    for row in rows:
        cells = [f'<td>{escape(row["房型"])}</td>']
        for name in markets:
            value = row[f"{name}（加元/月）"]
            shown = f"${value:,.0f}" if value is not None else "暂无数据"
            change = row[f"{name}均值较上年"]
            if change.endswith("%"):
                change += " 较上年"
            cells.append(f'<td><strong>{shown}</strong><span>{escape(change)}</span></td>')
        body.append("<tr>" + "".join(cells) + "</tr>")
    st.html('<table class="rental-table" aria-label="各房型平均月租金，单位加元"><thead><tr><th>房型</th><th>专建出租</th><th>出租 condo</th></tr></thead><tbody>' + "".join(body) + "</tbody></table>")


def cards(data, fields, period, notes=None):
    items = []
    for field in fields:
        metric = metric_at(data, field, period, unit(field))
        delta = metric["delta"]
        change = f"较上年同期 {delta:+.1f}{metric['delta_unit']}" if delta is not None else "暂无上年同期对照"
        published = data.get(period, {}).get(f"{field}_yoy_published")
        if published is not None and delta is not None:
            # TRREB divides by a revised prior-year figure; show both so neither is mistaken for the other.
            change = f"较上年同期 {delta:+.1f}%（原发布值自算） · TRREB 公布 {published:+.1f}%"
        if metric["value"] is None:
            change = f"{period_label(period)}尚无观测"
        raw_unit = unit(field)
        display_unit = "" if raw_unit in ("%", "index") else UNITS.get(raw_unit, raw_unit)
        extra = (notes or {}).get(field, "")
        items.append(f'<div class="metric-card" style="--series-color:{series_color(field)}"><div class="metric-label">{help_label(field, label(field))}</div>'
                     f'<div class="metric-value">{escape(formatted(metric["value"], field))}<span class="metric-unit">{escape(display_unit)}</span></div>'
                     f'<div class="metric-change">{escape(change)}</div><div class="metric-note">{escape(extra)}</div></div>')
    st.html(f'<div class="metric-grid" style="--cards:{len(fields)}">{"".join(items)}</div>')


def indicator_legend(fields):
    """Compact chart legend with the same explanatory disclosure as metric cards."""
    items = ''.join(
        f'<div class="help-legend-item" style="--series-color:{series_color(field)}">'
        f'<span class="help-legend-line" aria-hidden="true"></span>{help_label(field, label(field))}</div>'
        for field in fields
    )
    st.html(f'<div class="help-legend">{items}</div>')


def line_chart(data, fields, start, end, height=270, names=None, points=False, zero_y=False, external_legend=False):
    rows = []
    annual = len(start) == 4
    for field in fields:
        for row in chart_rows(data, field, start, end):
            rows.append({**row, "date": row["period"] + ("-01-01" if annual else "-01"), "指标": (names or {}).get(field, label(field))})
    frame = pd.DataFrame(rows)
    if frame.empty or not frame["value"].notna().any():
        st.info("所选期间没有可用观测。")
        return
    display_unit = "数量（笔 / 套）" if len({unit(f) for f in fields}) > 1 else UNITS.get(unit(fields[0]), unit(fields[0]))
    series_names = [(names or {}).get(field, label(field)) for field in fields]
    legend = alt.Legend(title=None, orient="top", columns=1, labelLimit=280, symbolSize=900, symbolStrokeWidth=2.4) if len(fields) > 1 and not external_legend else None
    year_ticks = [f"{y}-01-01" for y in range(int(start), int(end) + 1)] if annual and int(end) - int(start) <= 5 else alt.Undefined
    chart = alt.Chart(frame).mark_line(strokeWidth=2.4, point=alt.OverlayMarkDef(filled=True, size=65) if annual or points else False).encode(
        x=alt.X("date:T", title=None, scale=alt.Scale(type="utc", domain=[start + ("-01-01" if annual else "-01"), end + ("-12-31" if annual and start == end else "-01-01" if annual else "-01")]), axis=alt.Axis(format="%Y" if annual else "%y/%m", values=year_ticks, tickCount=5, labelAngle=0, labelOverlap=True, labelSeparation=18, grid=False)),
        y=alt.Y("value:Q", title=display_unit, scale=alt.Scale(zero=zero_y), axis=alt.Axis(tickCount=5, format=",.1f" if unit(fields[0]) == "%" else "~s")),
        color=alt.Color("指标:N", scale=alt.Scale(domain=series_names, range=[series_color(f) for f in fields]), legend=legend),
        detail="segment:N", tooltip=[alt.Tooltip("period:N", title="所属期"), "指标:N", alt.Tooltip("value:Q", title=display_unit, format=",.2f")],
    ).properties(height=height).configure_view(stroke=None).configure_axis(gridColor="#ededed", labelColor="#666666", titleColor="#666666", domain=False, labelFontSize=11, titleFontWeight="normal")
    st.altair_chart(chart, use_container_width=True)


def snlr_rolling_rows(data, start, end):
    """Arithmetic mean of three consecutive raw monthly ratios; gaps reset it."""
    periods = calendar_periods(start, end)
    raw = [data.get(period, {}).get('snlr_raw') for period in periods]
    rows = []
    for series in ('原始月度比值', '连续三个月均线'):
        segment = 0
        for index, period in enumerate(periods):
            values = raw[index - 2:index + 1] if index >= 2 else []
            value = raw[index] if series == '原始月度比值' else sum(values) / 3 if len(values) == 3 and all(v is not None for v in values) else None
            if value is None:
                segment += 1
            month = data.get(period, {})
            rows.append({'所属月份': period, '日期': period + '-01', '系列': series,
                         '比例（%）': value, '当月成交': month.get('trreb_sales'),
                         '当月新挂牌': month.get('trreb_new_listings'),
                         '当月原始比值': raw[index], 'segment': segment})
    return rows


def snlr_rolling_chart(data, start, end):
    frame = pd.DataFrame(snlr_rolling_rows(data, start, end))
    chart = alt.Chart(frame).mark_line(strokeWidth=2.2, point=alt.OverlayMarkDef(filled=True, size=36)).encode(
        x=alt.X('日期:T', title=None, scale=alt.Scale(type='utc'), axis=alt.Axis(format='%y/%m', grid=False)),
        y=alt.Y('比例（%）:Q', title='成交／新挂牌比（%）', scale=alt.Scale(zero=False)),
        color=alt.Color('系列:N', scale=alt.Scale(domain=['原始月度比值', '连续三个月均线'], range=[TEAL, BLUE]), legend=alt.Legend(title=None, orient='top', symbolSize=900, symbolStrokeWidth=2.2)),
        detail='segment:N',
        tooltip=['所属月份:N', '系列:N', alt.Tooltip('比例（%）:Q', format=',.1f'),
                 alt.Tooltip('当月成交:Q', format=',.0f'), alt.Tooltip('当月新挂牌:Q', format=',.0f'),
                 alt.Tooltip('当月原始比值:Q', format=',.1f')],
    ).properties(height=255).configure_view(stroke=None).configure_axis(domain=False, gridColor='#ededed')
    st.altair_chart(chart, use_container_width=True)


def sales_heatmap(data, start, end):
    """Raw monthly sales aligned by calendar month; never fill missing values with zero."""
    from .presentation import scoped_rows
    rows = [{"年份": p["period"][:4], "月份": p["period"][5:], "所属期": p["period"], "成交量": p["trreb_sales"]}
            for p in scoped_rows(data, ["trreb_sales"], start, end)]
    chart = alt.Chart(pd.DataFrame(rows)).mark_rect(stroke="white", strokeWidth=2).encode(
        x=alt.X("月份:O", scale=alt.Scale(domain=[f"{m:02d}" for m in range(1, 13)]), title=None, axis=alt.Axis(labelAngle=0, labelOverlap=False)),
        y=alt.Y("年份:O", sort="descending", title=None, axis=alt.Axis(labelOverlap=False)),
        color=alt.condition("isValid(datum['成交量'])", alt.Color("成交量:Q", scale=alt.Scale(scheme="blues", zero=True), legend=alt.Legend(orient="bottom", title="成交量")), alt.value("#eeeeee")),
        tooltip=["所属期:N", alt.Tooltip("成交量:Q", format=",.0f")],
    ).properties(height=max(230, len({r["年份"] for r in rows}) * 42 + 100)).configure_view(stroke=None)
    st.altair_chart(chart, use_container_width=True)


def bar_chart(frame, category, value, title, order=None, height=230):
    chart = alt.Chart(frame).mark_bar(color=TEAL, cornerRadiusEnd=0).encode(
        x=alt.X(f"{value}:Q", title=title, scale=alt.Scale(zero=True), axis=alt.Axis(format="~s", tickCount=5)),
        y=alt.Y(f"{category}:N", title=None, sort=order, axis=alt.Axis(labelLimit=160)),
        tooltip=[f"{category}:N", alt.Tooltip(f"{value}:Q", title=title, format=",.0f")],
    ).properties(height=height).configure_view(stroke=None).configure_axis(domain=False, gridColor="#ededed", labelColor="#666666", titleFontWeight="normal")
    st.altair_chart(chart, use_container_width=True)


def hpi_indexed_chart(db, root, periods):
    """Compare verified TRREB type prices from a shared first observation."""
    from .breakdowns import trreb_hpi_for_observation
    groups = ('detached', 'attached', 'townhouse', 'apartment')
    samples = []
    for period in periods:
        details = trreb_hpi_for_observation(db, period, root)
        values = {row['type_id']: row for row in details if row['metric'] == 'benchmark'}
        if all(group in values and values[group]['value'] > 0 for group in groups):
            samples.append((period, values))
    if len(samples) < 2:
        st.info('所选期间不足两个共同且已核验的房型基准价观测。')
        return
    first_period, baseline = samples[0]
    rows = [{'所属月份': period, '日期': period + '-01', '房型': values[group]['type_label'],
             '基准价（加元）': values[group]['value'],
             '基期指数': 100 * values[group]['value'] / baseline[group]['value']}
            for period, values in samples for group in groups]
    frame = pd.DataFrame(rows)
    domain = [baseline[group]['type_label'] for group in groups]
    chart = alt.Chart(frame).mark_line(strokeWidth=2.2).encode(
        x=alt.X('日期:T', title=None, scale=alt.Scale(type='utc'), axis=alt.Axis(format='%y/%m', grid=False)),
        y=alt.Y('基期指数:Q', title='共同起点 = 100', scale=alt.Scale(zero=False)),
        color=alt.Color('房型:N', scale=alt.Scale(domain=domain, range=[BLUE, TEAL, ORANGE, '#7952be']), legend=alt.Legend(orient='top', title=None)),
        tooltip=['所属月份:N', '房型:N', alt.Tooltip('基准价（加元）:Q', format=',.0f'), alt.Tooltip('基期指数:Q', format=',.1f')],
    ).properties(height=290).configure_view(stroke=None).configure_axis(gridColor='#ededed', domain=False)
    st.altair_chart(chart, use_container_width=True)
    st.caption(f'共同基期 {first_period}=100 · All TRREB Areas · HPI 房型基准价；基期之后各月仅使用核验通过的原报告。')
