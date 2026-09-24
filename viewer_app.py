"""Read-only presentation surface; accepts only a vetted numerical snapshot."""
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as native_st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from housing.i18n import st, english
from housing.catalog import SERIES_URLS
from housing.dashboard import css, cards, line_chart, label, note
from housing.presentation import available_periods, period_label
from housing.publication import load_display_snapshot, monthly_display

st.set_page_config(page_title="GTA Housing Monitor", layout="wide")
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
native_st.caption((f"Read-only display · Snapshot created {snapshot['created_at']} · Visitors can read chart values"
                   if english() else f"只读展示 · 资料快照生成于 {snapshot['created_at']} · 图表数值可被访问者读取"))


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
        st.subheader("房价走势")
        line_chart(data, ["trreb_hpi_benchmark"], start, end, height=330)
        st.subheader("成交与新增挂牌")
        line_chart(data, ["trreb_sales", "trreb_new_listings"], start, end)
        st.subheader("库存月数与成交／新挂牌比")
        a, b = st.columns(2)
        with a:
            line_chart(data, ["moi_raw"], start, end)
        with b:
            line_chart(data, ["snlr_raw"], start, end)
        st.caption("TRREB 全市场月度资料。价格为 HPI 基准价，非平均成交价；历史序列为当前所存版本。")
elif page == "租赁市场":
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
        fields = sorted(field for field in snapshot["observations"] if field.startswith("regional_asking_") and field.endswith("_total"))
        chosen = st.multiselect("比较地区（最多三个）", fields, default=fields[:2], max_selections=3, format_func=label)
        scope = period_control(chosen, "viewer-region-period") if chosen else None
        if scope:
            line_chart(data, chosen, *scope, height=340)
            st.caption("仅比较同一月度挂牌口径。地区无值即缺失，不以总体均值代替。")
elif page == "经济与供给":
    groups = [
        ("利率与融资", ["boc_policy_rate", "goc_5y_yield", "mortgage_uninsured_fixed_5plus"]),
        ("就业", ["toronto_unemployment_rate", "toronto_employment_rate", "toronto_participation_rate"]),
        ("住宅建设", ["toronto_cma_2011_starts", "toronto_cma_2011_completions", "toronto_cma_2011_under_construction"]),
    ]
    for title, fields in groups:
        st.subheader(title)
        scope = period_control(fields, f"viewer-{title}")
        if scope:
            line_chart(data, fields, *scope, height=290)
    st.caption("利率为加拿大背景；就业为 Toronto CMA 2021 边界；建设为 CMA 2011 边界。不同总体不计算交叉比率。")
else:
    from housing.affordability import monthly_payment
    st.subheader("固定本金的月供情景")
    principal = st.number_input("贷款本金（加元）", min_value=0, value=500000, step=10000)
    years = st.number_input("摊还年限", min_value=1, max_value=40, value=25)
    rate = st.number_input("名义年利率（%）", min_value=0.0, max_value=30.0, value=5.0, step=0.1)
    st.metric("每月本息", f"${monthly_payment(principal, rate, years):,.0f}")
    st.caption("仅为固定假设的计算情景，不代表贷款批准、实际家庭负担能力或利率预测。")

st.caption("公开数据研究工具 · 非实时行情 · 领先信号尚未验证")
