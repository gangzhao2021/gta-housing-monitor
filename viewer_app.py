"""Read-only presentation surface; accepts only a vetted numerical snapshot."""
import os
import sys
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as native_st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from housing.i18n import st, english
from housing.catalog import SERIES, SERIES_URLS
from housing.dashboard import css, cards, indicator_legend, line_chart, label, note
from housing.presentation import available_periods, period_label
from housing.publication import load_display_snapshot, monthly_display, CONTEXT_SERIES
from housing.regions import MONTHLY_REGIONS, CMHC_REGIONS, asking_id, cmhc_id
from housing.metric_help import help_label

st.set_page_config(page_title="GTA Housing Monitor", layout="wide")
if os.environ.get("HOUSING_REQUIRE_OWNER_AUTH") != "0":
    from housing.owner_auth import owner_gate
    owner_gate(st, title="展示端登录", logout_label="退出展示端")
css()
snapshot_path = Path(os.environ.get("HOUSING_DISPLAY_SNAPSHOT", ROOT / "data/display_snapshot.json"))
if not snapshot_path.is_file():
    st.error("展示数据尚未发布。")
    st.stop()
try:
    snapshot = load_display_snapshot(snapshot_path)
except (ValueError, OSError) as exc:
    st.error(f"展示数据未通过检查：{exc}")
    st.stop()
today = datetime.now(ZoneInfo("America/Toronto")).date()
data = {period: values for period, values in monthly_display(snapshot).items() if period < today.strftime("%Y-%m")}

with st.container(key="masthead"):
    brand, language = st.columns([5, 1], vertical_alignment="center")
    with brand:
        st.html('<div class="brand">GTA HOUSING MONITOR</div>')
    with language:
        native_st.radio("语言 / Language", ["中文", "English"], key="language", horizontal=True,
                        label_visibility="collapsed", format_func=lambda value: "EN" if value == "English" else "中文")
with st.container(key="main-nav"):
    page = st.radio("导航", ["市场总览", "租赁市场", "经济与供给", "月供情景"],
                    horizontal=True, label_visibility="collapsed", key="navigation")
st.title(page)
_created = datetime.fromisoformat(snapshot["created_at"]).astimezone(ZoneInfo("America/Toronto")).strftime("%Y-%m-%d %H:%M")
native_st.caption(f"Data updated {_created} (Toronto time)" if english() else f"数据更新于 {_created}（多伦多时间）")


def period_control(fields, key):
    periods = available_periods(data, fields)
    if not periods:
        st.info("该范围暂无可展示观测。")
        return None
    end = st.selectbox("观察月份", list(reversed(periods)), format_func=period_label, key=key)
    return max(periods[0], f"{int(end[:4])-2:04d}-{end[5:]}"), end


if page == "市场总览":
    scope = period_control(["trreb_hpi_benchmark"], "viewer-market-period")
    if scope:
        start, end = scope
        cards(data, ["trreb_hpi_benchmark", "trreb_sales", "moi_raw"], end)
        from housing.temperature_view import render as render_temperature
        render_temperature(snapshot.get("market_temperature"), end)
        st.subheader("房价走势")
        line_chart(data, ["trreb_hpi_benchmark"], start, end, height=330)
        st.subheader("成交与新增挂牌")
        indicator_legend(["trreb_sales", "trreb_new_listings"])
        line_chart(data, ["trreb_sales", "trreb_new_listings"], start, end, external_legend=True)
        st.subheader("库存月数与成交／新挂牌比")
        a, b = st.columns(2)
        with a:
            indicator_legend(["moi_raw"])
            line_chart(data, ["moi_raw"], start, end, external_legend=True)
        with b:
            indicator_legend(["snlr_raw"])
            line_chart(data, ["snlr_raw"], start, end, external_legend=True)
        st.caption("价格为 HPI 基准价，不是成交均价。")
    from housing.district_view import render as render_districts
    render_districts(snapshot.get('districts', []))
elif page == "租赁市场":
    from housing.rental_view import render_measures
    render_measures(snapshot["observations"], "viewer-rent-measure-room")
    mode = st.radio("租金口径", ["月度挂牌", "年度存量", "地区对比"], horizontal=True)
    if mode == "月度挂牌":
        room = st.selectbox("房型", ["total", "1br", "2br", "3br"], format_func={"total": "公寓全部卧室类型", "1br": "一卧", "2br": "两卧", "3br": "三卧"}.get)
        field = f"toronto_asking_rent_{room}"
        scope = period_control([field], "viewer-rent-period")
        if scope:
            start, end = scope
            cards(data, [field], end)
            line_chart(data, [field], start, end, height=330)
            note("挂牌均值涵盖专建出租公寓与 condo；不等于成交租金或全部出租物业。")
    elif mode == "年度存量":
        room = st.selectbox("房型", ["total", "studio", "1br", "2br", "3plus"], format_func={"total": "全部卧室类型", "studio": "开间", "1br": "一卧", "2br": "两卧", "3plus": "三卧及以上"}.get)
        fields = [f"toronto_pbr_rent_{room}", f"toronto_condo_rent_{room}"]
        annual = {year: {field: periods[year] for field in fields if year in (periods := snapshot["observations"].get(field, {}))}
                  for year in sorted({period for field in fields for period in snapshot["observations"].get(field, {})})}
        if annual:
            end = st.selectbox("调查年份", list(reversed(annual)), key="viewer-rent-year")
            cards(annual, fields, end)
            line_chart(annual, fields, min(annual), end, height=330)
            note("CMHC 年度存量租金，与月度挂牌不同；均值变化并非同一套住房租金涨幅。")
    else:
        frequency = st.radio("地区资料频率", ["月度挂牌", "年度 CMHC"], horizontal=True)
        annual = frequency == "年度 CMHC"
        regions = CMHC_REGIONS if annual else MONTHLY_REGIONS
        chosen = st.multiselect("比较地区（最多三个）", list(regions), default=list(regions)[:2],
                                max_selections=3, format_func=regions.get)
        rooms = ["total", "studio", "1br", "2br", "3plus"] if annual else ["total", "1br", "2br", "3br"]
        room = st.selectbox("地区房型", rooms, format_func={"total": "全部卧室类型", "studio": "开间", "1br": "一卧", "2br": "两卧", "3br": "三卧", "3plus": "三卧及以上"}.get)
        measure = st.selectbox("地区指标", ["rent", "vacancy"], format_func={"rent": "平均租金", "vacancy": "空置率"}.get) if annual else "rent"
        fields = [cmhc_id(region, measure, room) if annual else asking_id(region, room) for region in chosen]
        present = [field for field in fields if snapshot["observations"].get(field)]
        for region, field in zip(chosen, fields):
            if field not in present:
                st.info(f"{regions[region]} · {room}：该口径没有可展示观测；不以其他地区或房型替代。")
        if present:
            if annual:
                annual_data = {period: {field: snapshot["observations"].get(field, {}).get(period) for field in present}
                               for period in sorted({period for field in present for period in snapshot["observations"][field]})}
                end = st.selectbox("地区调查年份", list(reversed(annual_data)), key="viewer-region-year")
                line_chart(annual_data, present, min(annual_data), end, height=340,
                           names={field: regions[region] for region, field in zip(chosen, fields) if field in present})
                st.caption("CMHC 年度专建出租公寓调查区；组合调查区不能拆成单一城市。缺值可能是来源抑制，不填零。")
            else:
                scope = period_control(present, "viewer-region-period")
                if scope:
                    line_chart(data, present, *scope, height=340,
                               names={field: regions[region] for region, field in zip(chosen, fields) if field in present})
                    st.caption("仅比较同一月度挂牌口径。地区无值即缺失，不以总体均值代替。")
elif page == "经济与供给":
    st.subheader("利率与融资")
    rates = ["boc_policy_rate", "goc_5y_yield", "mortgage_uninsured_fixed_5plus"]
    scope = period_control(rates, "viewer-利率与融资")
    if scope:
        indicator_legend(rates)
        line_chart(data, rates, *scope, height=290, external_legend=True)
    st.subheader("就业")
    employment = ["toronto_unemployment_rate", "toronto_employment_rate", "toronto_participation_rate"]
    scope = period_control(employment, "viewer-就业")
    if scope:
        left, right = st.columns(2)
        with left:
            st.markdown("**失业率**")
            indicator_legend(employment[:1])
            line_chart(data, employment[:1], *scope, height=260, external_legend=True)
        with right:
            st.markdown("**就业率与劳动参与率**")
            indicator_legend(employment[1:])
            line_chart(data, employment[1:], *scope, height=260, external_legend=True)
    st.subheader("住宅建设")
    construction = ["toronto_cma_2011_starts", "toronto_cma_2011_completions", "toronto_cma_2011_under_construction"]
    scope = period_control(construction, "viewer-住宅建设")
    if scope:
        left, right = st.columns(2)
        with left:
            st.markdown("**当月开工与竣工**")
            indicator_legend(construction[:2])
            line_chart(data, construction[:2], *scope, height=260, zero_y=True, external_legend=True)
        with right:
            st.markdown("**月末在建住宅**")
            indicator_legend(construction[2:])
            line_chart(data, construction[2:], *scope, height=260, external_legend=True)
        st.caption("开工、竣工为当月数量；在建为月末总量。")
    st.subheader("人口")
    population = snapshot["observations"].get("toronto_cma_2021_population", {})
    if population:
        annual_population = {year: {"toronto_cma_2021_population": value} for year, value in sorted(population.items())}
        end = st.selectbox("人口估计年份", list(reversed(annual_population)), key="viewer-population-year")
        indicator_legend(["toronto_cma_2021_population"])
        line_chart(annual_population, ["toronto_cma_2021_population"], min(annual_population), end, height=290, external_legend=True)
    st.subheader("外部背景（研究中）")
    st.caption("各项的地区、频率与单位不同，不能直接相加或比较。")
    context_html_rows = []
    context_fields = sorted(CONTEXT_SERIES)
    for field in context_fields:
        item = snapshot.get("context", {}).get(field)
        decimals = 4 if field == "usd_cad_monthly" else 1 if field == "toronto_residential_construction_cost_index" else 2
        period = item["period"] if item else "—"
        if item and field == "toronto_residential_construction_cost_index":
            quarter = (int(period[5:]) - 1) // 3 + 1
            period = f"{period[:4]} Q{quarter}" if english() else f"{period[:4]}年第{quarter}季度"
        row = {"指标": SERIES[field][0],
               "最近值": f"{item['value']:,.{decimals}f}" if item else "—",
               "单位": SERIES[field][4], "资料期": period,
               "地区": SERIES[field][3]}
        context_html_rows.append(
            '<tr><th scope="row">' + help_label(field, row["指标"]) + '</th>'
            + ''.join(f'<td data-label="{escape(column)}">{escape(row[column])}</td>'
                      for column in ("最近值", "单位", "资料期", "地区")) + '</tr>')
    if context_html_rows:
        headings = ''.join(f'<th scope="col">{column}</th>' for column in ("指标", "最近值", "单位", "资料期", "地区"))
        st.html('<table class="context-table"><thead><tr>' + headings + '</tr></thead><tbody>'
                + ''.join(context_html_rows) + '</tbody></table>')
else:
    from housing.affordability import monthly_payment
    st.subheader("固定本金的月供情景")
    principal = st.number_input("贷款本金（加元）", min_value=0, value=500000, step=10000)
    years = st.number_input("摊还年限", min_value=1, max_value=40, value=25)
    rate = st.number_input("名义年利率（%）", min_value=0.0, max_value=30.0, value=5.0, step=0.1)
    st.metric("每月本息", f"${monthly_payment(principal, rate, years):,.0f}")
    st.caption("按固定假设计算，不代表贷款批准或利率预测。")

st.caption("公开数据研究工具 · 非实时行情 · 不构成投资建议")
