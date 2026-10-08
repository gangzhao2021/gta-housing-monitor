"""Source-backed Toronto housing dashboard with explicit time and market scopes."""
from pathlib import Path
import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as native_st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from housing.i18n import st, english
from housing.catalog import SERIES, SERIES_URLS
from housing.db import connect, latest
from housing.freshness import assess, RULES, STATUS_LABELS
from housing.read_model import monthly
from housing.snapshot import save, open_snapshot
from housing.affordability import monthly_payment, historical_payment_rows
from housing.presentation import annual_data, available_periods, metric_at, scoped_rows, period_label
from housing.dashboard import css, cards, label, unit, formatted, line_chart, bar_chart, rental_table, sales_heatmap, note, hpi_indexed_chart, snlr_rolling_chart, TEAL, BLUE
from housing.breakdowns import construction_breakdown, trreb_hpi_breakdown, trreb_hpi_for_observation
from housing.ingest import parse_cmhc_rental_details

st.set_page_config(page_title="GTA Housing Monitor", layout="wide")
if os.environ.get("HOUSING_REQUIRE_OWNER_AUTH") != "0":
    from housing.owner_auth import owner_gate
    owner_gate(st)
css()
db_path = ROOT / "data/housing.sqlite3"
if not db_path.exists():
    st.info("尚未导入数据。请按使用指南运行数据导入命令。")
    st.stop()
db = connect(db_path)
today = datetime.now(ZoneInfo("America/Toronto")).date()
data = {p: v for p, v in monthly(db).items() if p < today.strftime("%Y-%m")}
resale_fields = ["trreb_sales", "trreb_new_listings", "trreb_active_listings", "moi_raw", "snlr_raw", "trreb_hpi_composite", "trreb_hpi_benchmark"]
resale_periods = available_periods(data, resale_fields)
if not resale_periods:
    db.close()
    st.info("尚无完整月份的转售数据，请先导入 TRREB 月报。")
    st.stop()


@st.cache_data(show_spinner=False)
def file_details(kind, path, modified):
    return {"rental": parse_cmhc_rental_details, "construction": construction_breakdown, "hpi": trreb_hpi_breakdown}[kind](path)


def source_path(field, period):
    row = db.execute("SELECT r.path FROM observations o JOIN raw_files r ON o.raw_sha256=r.sha256 WHERE o.series_id=? AND o.period=? ORDER BY o.version DESC LIMIT 1", (field, period)).fetchone()
    return ROOT / row["path"] if row else None


def month_controls(fields, key, targets=None):
    periods = available_periods(data, fields)
    left, right = targets or st.columns([2, 1])
    with left:
        end = st.selectbox("观察月份", list(reversed(periods)), format_func=period_label, key=f"{key}-month")
    with right:
        window = st.selectbox("趋势范围", ["近 24 个月", "近 12 个月", "近 36 个月", "全部历史"], key=f"{key}-window")
    count = {"近 12 个月": 12, "近 24 个月": 24, "近 36 个月": 36}.get(window)
    if count:
        year, month = map(int, end.split("-"))
        index = year * 12 + month - count
        start = max(periods[0], f"{index // 12:04d}-{index % 12 + 1:02d}")
    else:
        start = periods[0]
    return start, end


def source_rows(fields, start, end, key, month_key=None):
    with st.expander("查看与下载本节数据"):
        frame = pd.DataFrame(scoped_rows(data, fields, start, end)).rename(columns={"period": "所属月份", **{f: f"{label(f)} ({unit(f)})" for f in fields}})
        if month_key and not frame.empty:
            # The row index belongs to this exact slice. A new month/window
            # gets a new widget key so a stale index cannot highlight another row.
            table_key = f"source-table-{key}-{start}-{end}"

            def select_month():
                rows = st.session_state[table_key].selection.rows
                if rows:
                    st.session_state[month_key] = frame.iloc[rows[0]]["所属月份"]

            st.dataframe(frame, hide_index=True, width="stretch", key=table_key,
                         on_select=select_month, selection_mode="single-row")
        else:
            st.dataframe(frame, hide_index=True, width="stretch")
        st.download_button("下载 CSV", frame.to_csv(index=False).encode("utf-8-sig"), f"{key}-{start}-{end}.csv", "text/csv", key=f"download-{key}")
        st.caption("空白表示没有观测。")


with st.container(key="masthead"):
    brand, language = st.columns([5, 1], vertical_alignment="center")
    with brand:
        st.html('<div class="brand">GTA HOUSING MONITOR</div>')
    with language:
        native_st.radio("语言 / Language", ["中文", "English"], key="language", horizontal=True, label_visibility="collapsed", format_func=lambda v: "EN" if v == "English" else "中文")
with st.container(key="main-nav"):
    page = st.radio("导航", ["市场总览", "租赁市场", "经济与供给", "月供情景", "数据与记录"], horizontal=True, label_visibility="collapsed", key="navigation")
st.title(page)
st.caption(f"大多伦多住房市场观察  /  月度转售更新至 {period_label(resale_periods[-1])}" if page == "市场总览" else {
    "租赁市场": "挂牌报价与年度存量租金 · 按来源和地区分别比较",
    "经济与供给": "利率、就业、住宅建设与人口 · 各指标保留独立口径",
    "月供情景": "调整贷款假设，比较每月本息",
    "数据与记录": "检查来源、观测覆盖与历史版本",
}[page])

if page == "市场总览":
    from housing.layout_view import SECTIONS, anchor, section_nav
    section_nav([SECTIONS[0], SECTIONS[1], SECTIONS[3], SECTIONS[2], SECTIONS[4]])  # this page shows price bands before supply
    anchor("sec-price")
    with st.container(key="market-story"):
        context, plot = st.columns([1, 3.4], gap="large")
        with context:
            price = st.container(key="hero-price")
            period = st.container()
        with plot:
            with st.container(key="price-chart-heading"):
                heading, range_control = st.columns([2, 1], vertical_alignment="center")
            with heading:
                st.subheader("房价走势")
        start, end = month_controls(resale_fields, "market", targets=(period, range_control))
        with price:
            cards(data, ["trreb_hpi_benchmark"], end, {"trreb_hpi_benchmark": "HPI 标准化住宅价格"})
        with context:
            st.caption("MLS HPI 基准价，不是成交均价")
        with plot:
            teranet = available_periods(data, ["teranet_toronto_index_sa"])
            span = native_st.radio("时间跨度", ["recent", "long"], horizontal=True, label_visibility="collapsed", key="owner-price-span",
                                   format_func=lambda v: ("2 years · HPI" if english() else "近 2 年 · HPI") if v == "recent" else ("Since 1998 · Teranet" if english() else "1998 年起 · Teranet")) if teranet else "recent"
            if span == "long":
                line_chart(data, ["teranet_toronto_index_sa"], teranet[0], teranet[-1], height=330)
                native_st.caption("Teranet–National Bank Toronto repeat-sales index (seasonally adjusted), dated at registration; a different measure from the HPI." if english() else
                                  "Teranet–National Bank 多伦多重复交易指数（季调），按产权登记日期；与 HPI 口径不同。")
            else:
                line_chart(data, ["trreb_hpi_benchmark"], start, end, height=330)
    temperature_csv = ROOT / "data/research/trreb-history.csv"
    if temperature_csv.is_file():
        from housing.market_temperature import build as build_temperature
        from housing.temperature_view import render as render_temperature
        render_temperature(build_temperature(temperature_csv, db), end, "market-month", available_periods(data, resale_fields))
        from housing.mix_view import render as render_bands
        anchor("sec-mix")
        render_bands(lambda field: {row["period"]: row["value"] for row in latest(db, field)}, end, "market-month", available_periods(data, resale_fields))
    anchor("sec-supply")
    cards(data, ["trreb_sales", "trreb_active_listings", "moi_raw"], end,
          {"moi_raw": "月末有效挂牌 ÷ 当月成交"})
    st.subheader("成交与新增挂牌")
    cards(data, ["trreb_new_listings", "snlr_raw"], end,
          {"snlr_raw": "当月成交 ÷ 新增挂牌 × 100"})
    line_chart(data, ["trreb_sales", "trreb_new_listings"], start, end, height=300)
    st.subheader("成交季节分布")
    st.caption("颜色越深成交越多；灰格为缺失月份。")
    sales_heatmap(data, start, end)
    supply, turnover = st.columns(2, gap="large")
    with supply:
        st.subheader("库存月数走势")
        line_chart(data, ["moi_raw"], start, end, height=240)
    with turnover:
        st.subheader("成交／新挂牌比走势")
        line_chart(data, ["snlr_raw"], start, end, height=240)
    with st.expander("月末有效挂牌走势"):
        line_chart(data, ["trreb_active_listings"], start, end, height=220)
    with st.expander("查看三个月平滑趋势"):
        st.caption("连续三个月的平均，帮助看短期走势；不是季节调整。")
        snlr_rolling_chart(data, start, end)
    st.caption("TRREB 公布的同比以修订后的上年同月为分母，可能与原发布值自算的同比相差 1 个百分点以上。")
    source_rows(resale_fields, start, end, "trreb", "market-month")
    st.divider()
    st.subheader("各房型基准价")
    st.caption(f"{period_label(end)} · All TRREB Areas · HPI 房型分类")
    try:
        details = trreb_hpi_for_observation(db, end, ROOT)
        benchmark = pd.DataFrame([r for r in details if r["metric"] == "benchmark" and r["type_id"] != "composite"])
        bar_chart(benchmark, "type_label", "value", "基准房价（加元）", benchmark["type_label"].tolist())
        st.subheader("各房型基准价累计变化")
        hpi_indexed_chart(db, ROOT, [p for p in resale_periods if start <= p <= end])
        with st.expander("房型数值与来源"):
            frame = pd.DataFrame(details).pivot(index=["type_label", "source_type"], columns="metric", values="value").reset_index().rename(columns={"type_label": "房型", "source_type": "原始分类", "benchmark": "基准价（加元）", "index": "HPI 指数", "source_yoy": "原报告同比（%）"})
            st.dataframe(frame, hide_index=True, width="stretch")
            source_file, source_page = Path(details[0]['source_path']).name, details[0]['source_page']
            native_st.caption(f"Source: TRREB report {source_file}, page {source_page}." if english() else
                              f"来源：TRREB 月报 {source_file} 第 {source_page} 页。")
            st.download_button("下载 HPI 房型数据与来源", pd.DataFrame(details).to_csv(index=False).encode("utf-8-sig"), f"hpi-types-{end}.csv", "text/csv")
    except (ValueError, FileNotFoundError) as exc:
        st.warning(f"该月房型原表未通过来源检查：{exc}")

    anchor("sec-areas")
    from housing.districts import display_rows
    from housing.district_view import render as render_districts
    render_districts(display_rows(db))
elif page == "租赁市场":
    from housing.rental_view import latest_observations, measure_fields, render_measures
    render_measures(latest_observations(db, measure_fields()), "rent-measure-room", (("asking-room", ("total", "compare", "1br", "2br", "3br")),))
    with st.container(key="rental-view-nav"):
        view = st.radio("租金数据口径", ["月度挂牌租金", "年度存量租金（CMHC）", "地区租金对比"],
                        format_func=lambda v: {"月度挂牌租金": "月度挂牌", "年度存量租金（CMHC）": "年度存量", "地区租金对比": "地区对比"}[v],
                        horizontal=True, label_visibility="collapsed", key="rental-view")
    if view == "月度挂牌租金":
        from housing.rental_view import render_monthly
        render_monthly(db, data, today, month_controls)
    elif view == "地区租金对比":
        from housing.regional_view import render_regions
        render_regions(db, data, today)
    else:
        rental_fields = [field for field in SERIES if field.startswith(("toronto_pbr_", "toronto_condo_"))]
        rental = annual_data(db, rental_fields)
        if not rental:
            st.info("尚未导入 CMHC 租赁调查。")
        else:
            with st.container(key="annual-story"):
                context, plot = st.columns([1, 3.4], gap="large")
                with context:
                    year = st.selectbox("租赁调查年份", list(reversed(rental)), format_func=lambda y: f"{y} 年 10 月", key="rental-year")
                    bedrooms = {"studio": "开间", "1br": "一卧", "2br": "两卧", "3plus": "三卧及以上", "total": "公寓全部卧室类型"}
                    markets = {"pbr": "专建出租公寓", "condo": "业主出租 condo"}
                    trend_room = st.selectbox("趋势房型", list(bedrooms), index=4, format_func=bedrooms.get, key="rental-trend-room")
                    st.caption("Toronto CMA · 2021 边界\n\n本页按年度调查选择，不受其他页面的月份控制。")
                trend_fields = [f"toronto_{market}_rent_{trend_room}" for market in markets]
                with plot:
                    st.subheader("租金年度走势")
                    line_chart(rental, trend_fields, min(rental), year, height=330,
                               names={f: markets[f.split('_')[1]] for f in trend_fields})
                    st.caption("每个点代表一次 10 月年度调查，连线仅用于比较年度变化；没有月度插值。年份菜单来自已导入且通过地区口径核验的观测，所选年份也是趋势截止年。")
            note("CMHC 平均租金包含现有租约；用于比较出租住房存量，不代表今天的 MLS 挂牌租金或新租客报价。")
            st.caption("均值变化受样本与住房构成影响，不等于同样本租金涨幅。历史来源及调查质量等级可在下方展开查看。")
            with st.expander("租金趋势数据与来源"):
                history = []
                for period in sorted(p for p in rental if p <= year):
                    for market, market_label in markets.items():
                        field = f"toronto_{market}_rent_{trend_room}"
                        path = source_path(field, period)
                        meta = next((r for r in file_details("rental", str(path), path.stat().st_mtime_ns)
                                     if r["series_id"] == field and r["period"] == period), {}) if path and path.exists() else {}
                        history.append({"调查年份": period, "房型": bedrooms[trend_room], "市场": market_label,
                                        "月租金": rental[period].get(field), "质量等级": meta.get("quality"),
                                        "来源文件": path.name if path else None, "来源表": meta.get("sheet"), "单元格": meta.get("cell")})
                history_frame = pd.DataFrame(history)
                st.dataframe(history_frame, hide_index=True, width="stretch")
                st.download_button("下载租金年度走势", history_frame.to_csv(index=False).encode("utf-8-sig"), f"rental-trend-{trend_room}-{year}.csv", "text/csv")
            st.divider()
            st.subheader("不同房型，租金相差多少")
            st.caption("专建出租公寓与业主出租 condo 分列；公寓全部卧室类型为 CMHC 直接发布的总体均值，不含 house。")
            table, chart, evidence = [], [], []
            field_paths = {f: source_path(f, year) for f in rental_fields if rental[year].get(f) is not None}
            paths = set(field_paths.values())
            for path in paths:
                if path and path.exists():
                    try:
                        evidence.extend({**r, "source_file": path.name} for r in file_details("rental", str(path), path.stat().st_mtime_ns) if r["period"] == year and field_paths.get(r["series_id"]) == path)
                    except ValueError as exc:
                        st.warning(f"租赁来源质量标记无法读取：{exc}")
                else:
                    st.warning("部分租赁原始文件不可用，无法核对相应质量标记。")
            metadata = {(r["series_id"], r["period"]): r for r in evidence}
            for bedroom, bedroom_label in bedrooms.items():
                row = {"房型": bedroom_label}
                for market, market_label in markets.items():
                    field = f"toronto_{market}_rent_{bedroom}"
                    metric = metric_at(rental, field, year)
                    value = metric["value"]
                    row[f"{market_label}（加元/月）"] = value
                    row[f"{market_label}均值较上年"] = f"{metric['delta']:+.1f}%" if metric["delta"] is not None else ("本期无观测" if value is None else "无上年可比值")
                    quality = metadata.get((field, year), {}).get("quality")
                    if value is not None:
                        chart.append({"房型": bedroom_label, "市场": market_label, "月租金": value, "质量等级": quality or "未读取"})
                table.append(row)
            if chart:
                frame = pd.DataFrame(chart)
                bars = alt.Chart(frame).mark_bar(cornerRadiusEnd=0).encode(
                    x=alt.X("月租金:Q", title="平均月租金（加元）", scale=alt.Scale(zero=True), axis=alt.Axis(format=",.0f", tickCount=5)),
                    y=alt.Y("房型:N", sort=list(bedrooms.values()), title=None, axis=alt.Axis(labelLimit=100)),
                    yOffset="市场:N", color=alt.Color("市场:N", scale=alt.Scale(domain=list(markets.values()), range=[TEAL, BLUE]), legend=alt.Legend(title=None, orient="top", labelExpr="datum.label === '专建出租公寓' ? '专建出租' : '出租 condo'")),
                    tooltip=["房型:N", "市场:N", alt.Tooltip("月租金:Q", format=",.0f", title="加元/月"), "质量等级:N"],
                ).properties(height=330).configure_view(stroke=None).configure_axis(domain=False, gridColor="#ededed", labelColor="#666666", titleFontWeight="normal")
                st.altair_chart(bars, use_container_width=True)
            rental_frame = pd.DataFrame(table)
            rental_table(table, markets.values())
            st.caption("均值较上年 = 本期平均租金 ÷ 上年平均租金 − 1；受样本及住房构成变化影响，不等于同一批住房的租金涨幅。")
            cautious = [r for r in evidence if "_rent_" in r["series_id"] and r["quality"] in ("c", "d")]
            if cautious:
                st.caption("调查精度提示：" + "；".join(f"{label(r['series_id'])}为 {r['quality']} 级" for r in cautious) + "。质量等级越后，估计精度越低。")
            condo_changes = [r for r in evidence if r["series_id"].startswith("toronto_condo_rent_")]
            if condo_changes and all(r["significance"] in ("-", "–") for r in condo_changes):
                st.caption(f"CMHC 标记：{year} 年 condo 各房型租金同比变化均未达到统计显著性。")
            export_rows = []
            for bedroom, room_label in bedrooms.items():
                for market, market_label in markets.items():
                    field = f"toronto_{market}_rent_{bedroom}"
                    meta = metadata.get((field, year), {})
                    value = rental[year].get(field)
                    export_rows.append({"调查年份": year, "调查月份": 10, "地区": "Toronto CMA 2021 boundary",
                                        "房型": room_label, "市场": market_label, "月租金": value,
                                        "质量等级": meta.get("quality"), "状态": meta.get("status", "no_observation" if value is None else "quality_unavailable"),
                                        "显著性标记": meta.get("significance"), "来源文件": meta.get("source_file"),
                                        "来源表": meta.get("sheet"), "单元格": meta.get("cell"),
                                        "变化口径": "均值差异受样本构成影响，非同样本租金涨幅"})
            export = pd.DataFrame(export_rows)
            st.download_button("下载房型租金对照", export.to_csv(index=False).encode("utf-8-sig"), f"toronto-rental-{year}.csv", "text/csv")
            st.divider()
            st.subheader("空置情况")
            cards(rental, ["toronto_pbr_vacancy_rate", "toronto_condo_vacancy_rate"], year,
                  {f: f"{year}年10月 · 全房型" for f in ["toronto_pbr_vacancy_rate", "toronto_condo_vacancy_rate"]})
            line_chart(rental, ["toronto_pbr_vacancy_rate", "toronto_condo_vacancy_rate"], min(rental), year, height=240,
                       names={"toronto_pbr_vacancy_rate": "专建出租公寓", "toronto_condo_vacancy_rate": "业主出租 condo"})
            with st.expander("按房型查看专建出租空置率"):
                rows = [{"房型": text, "专建出租空置率（%）": rental[year].get(f"toronto_pbr_vacancy_{bedroom}" if bedroom != "total" else "toronto_pbr_vacancy_rate")} for bedroom, text in bedrooms.items()]
                st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
                st.caption("该工作簿的 condo 空置率仅提供总体值，不能按房型套用同一个数值。")
            with st.expander("年度变化与调查口径"):
                st.dataframe(rental_frame, hide_index=True, width="stretch", column_config={f"{name}（加元/月）": st.column_config.NumberColumn(format="$%d") for name in markets.values()})
                st.write("专建出租：私人出租公寓楼（3 套及以上）。业主出租 condo：公寓产权房中的次级出租市场。当前页范围为公寓；原工作簿还包含 Townhouse 等独立表，未混入本页。")
                st.markdown(f"[查看 CMHC 原始调查表]({SERIES_URLS['toronto_pbr_rent_2br']})")
                if evidence:
                    st.dataframe(pd.DataFrame(evidence).rename(columns={"series_id": "系列", "quality": "质量等级", "significance": "显著性标记", "sheet": "来源表", "cell": "单元格"}), hide_index=True, width="stretch")
                    st.download_button("下载租赁质量与来源", pd.DataFrame(evidence).to_csv(index=False).encode("utf-8-sig"), f"rental-evidence-{year}.csv", "text/csv")

elif page == "经济与供给":
    from housing.scenario_view import render_readings
    render_readings(lambda field: {row["period"]: row["value"] for row in latest(db, field)})
    st.html('<nav class="section-jump" aria-label="主题导航"><a href="#rates">利率与融资</a><a href="#employment">就业</a><a href="#construction">住宅建设</a><a href="#population">人口</a></nav>')
    topics = [("利率与融资", "rates"), ("就业", "employment"), ("住宅建设", "construction"), ("人口", "population")]
    for topic, anchor in topics:
        st.html(f'<div id="{anchor}" class="section-anchor"></div>')
        with st.container(key=f"economic-{anchor}"):
            st.subheader(topic)
            context, plot = st.columns([1, 3.4], gap="large")
            if topic == "人口":
                field = "toronto_cma_2021_population"
                population = annual_data(db, [field])
                if population:
                    with context:
                        year = st.selectbox("人口估计年份", list(reversed(population)), format_func=period_label, key="population-year")
                    st.caption(f"Toronto CMA · 2021 边界 · {year} 年 7 月 1 日估计 · 独立年度范围")
                    with context:
                        cards(population, [field], year)
                    with plot:
                        st.subheader("人口长期变化")
                        line_chart(population, [field], min(population), year, height=350)
                else:
                    st.info("尚无人口年度观测。")
                continue
            fields, subtitle = {
                "利率与融资": (["boc_policy_rate", "goc_5y_yield", "mortgage_uninsured_fixed_5plus"], "加拿大 · 政策利率取月末值；国债收益率取有效日均值；按揭为月度加权均值"),
                "就业": (["toronto_unemployment_rate", "toronto_employment_rate", "toronto_participation_rate"], "Toronto CMA · 2021 边界 · 单月季调估计"),
                "住宅建设": (["toronto_cma_2011_starts", "toronto_cma_2011_completions", "toronto_cma_2011_under_construction"], "Toronto CMA · 2011 边界 · 全部住宅类型 · 实际单位数，非年化率"),
            }[topic]
            start, end = month_controls(fields, "context-" + anchor, targets=(context, context))
            st.caption(subtitle)
            cards(data, fields, end)
            for field in fields:
                if data.get(end, {}).get(field) is None:
                    earlier = [p for p in data if p < end and data[p].get(field) is not None]
                    if earlier:
                        last = earlier[-1]
                        st.warning(f"{period_label(end)}的{label(field)}暂无观测。最近较早值：{period_label(last)}，{formatted(data[last][field], field)}。")
            with plot:
                if topic == "住宅建设":
                    st.caption("开工、竣工为当月数量；在建为月末总量。")
                    for construction_field in fields:
                        st.subheader(label(construction_field))
                        line_chart(data, [construction_field], start, end, height=185)
                else:
                    options = ["all", *fields] if topic == "利率与融资" else fields
                    field = st.selectbox("趋势指标", options, format_func=lambda f: "利率对照" if f == "all" else label(f), key=f"trend-field-{anchor}")
                    line_chart(data, fields if field == "all" else [field], start, end, height=340)
            if topic == "住宅建设":
                st.subheader("按住宅类型比较")
                metric = st.selectbox("建设指标", ["starts", "completions", "under_construction"], format_func={"starts": "开工", "completions": "竣工", "under_construction": "在建"}.get, key="construction-metric")
                path = source_path("toronto_cma_2011_" + metric, end)
                if path and path.exists():
                    try:
                        details = [r for r in file_details("construction", str(path), path.stat().st_mtime_ns) if r["period"] == end and r["metric"] == metric]
                        frame = pd.DataFrame([r for r in details if r["type_id"] != "total"])
                        if not frame.empty:
                            bar_chart(frame, "type_label", "value", "住宅单位（套）", frame["type_label"].tolist())
                            if any(r["reconciliation_ok"] is not True for r in details):
                                st.warning("该期原表分项与总数无法核对一致；保留各项原始值，不重算总量。")
                            with st.expander("建设房型数据与来源"):
                                st.dataframe(pd.DataFrame(details)[["type_label", "value", "quality_note"]].rename(columns={"type_label": "房型", "value": "套数", "quality_note": "原表质量"}), hide_index=True, width="stretch")
                                st.download_button("下载建设房型数据与来源", pd.DataFrame(details).to_csv(index=False).encode("utf-8-sig"), f"construction-types-{end}-{metric}.csv", "text/csv")
                    except ValueError as exc:
                        st.warning(f"建设房型原表未通过检查：{exc}")
            source_rows(fields, start, end, "context-" + anchor, "context-" + anchor + "-month")

elif page == "月供情景":
    from housing.scenario_view import render_scenario
    observations = latest(db, "mortgage_uninsured_fixed_5plus")
    default = observations[-1] if observations else None
    hpi_rows = latest(db, "trreb_hpi_benchmark")
    hpi = hpi_rows[-1] if hpi_rows else None
    st.caption("Monthly principal and interest from a home price · CAD · compounded semi-annually (Canadian convention)" if english() else "从房价出发估算每月本息 · 加元 · 半年复利（加拿大惯例）")
    chosen = render_scenario(float(hpi["value"]) if hpi else 1_000_000, hpi["period"] if hpi else None,
                             float(default["value"]) if default else 5.0, default["period"] if default else None, "owner-scenario")
    if chosen is None:
        db.close()
        st.stop()
    principal, amortization = chosen["loan"], chosen["years"]
    history = historical_payment_rows(observations, principal, amortization)
    if history:
        st.subheader("固定条件下的历史月供")
        st.caption("按各月利率重算同一笔贷款的月供，不是当时借款人的实际月供。")
        frame = pd.DataFrame(history)
        history_chart = alt.Chart(frame).mark_line(color=BLUE, strokeWidth=2.3, point=alt.OverlayMarkDef(filled=True, size=42)).encode(
            x=alt.X("日期:T", title=None, scale=alt.Scale(type="utc"), axis=alt.Axis(format="%y/%m", grid=False)),
            y=alt.Y("估算月供（加元）:Q", title="每月本息（加元）", scale=alt.Scale(zero=False), axis=alt.Axis(format=",.0f")),
            detail="segment:N",
            tooltip=["所属月份:N", alt.Tooltip("按揭利率（%）:Q", format=".2f"), alt.Tooltip("估算月供（加元）:Q", format=",.2f")],
        ).properties(height=275).configure_view(stroke=None).configure_axis(domain=False, gridColor="#ededed")
        st.altair_chart(history_chart, use_container_width=True)
        st.download_button("下载历史月供情景", frame.drop(columns="segment").to_csv(index=False).encode("utf-8-sig"),
                           f"mortgage-payment-{history[0]['所属月份']}-{history[-1]['所属月份']}.csv", "text/csv")
    note("月供仅包含本金和利息；未计税、保险、管理费及其他住房开支。结果不代表银行报价或获批额度。")
    with st.expander("计算方法"):
        st.write("加拿大名义年利率按半年复利换算为等效月利率，再按固定本金、摊还年限和月付频率计算本息。")

else:
    st.subheader("来源覆盖与更新时间")
    st.caption(f"检查日期：{today.isoformat()} · 新鲜度按资料所属期和来源发布节奏判断。")
    from housing.regional_view import annual_publication_status
    publication_status = annual_publication_status(db)
    freshness_rows = []
    for field, definition in SERIES.items():
        state = assess(db, field, today)
        status_label = STATUS_LABELS[state["status"]]
        withheld = publication_status.get((field, state.get("expected_period"))) == "suppressed"
        if withheld and state["latest_period"] != state.get("expected_period"):
            status_label = "来源抑制发布"
        freshness_rows.append({"指标": definition[0], "来源": definition[1], "地区": definition[3], "最近所属期": state["latest_period"] or "无", "状态": status_label, "应有所属期": state.get("expected_period") or "—", "历史缺月": "、".join(state.get("internal_gaps", [])) or "—"})
    with st.container(key="source-summary"):
        for col, (name, count) in zip(st.columns(3), [("指标", len(freshness_rows)), ("来源", len({r["来源"] for r in freshness_rows})), ("地区", len({r["地区"] for r in freshness_rows}))]):
            with col:
                st.metric(name, str(count))
    st.dataframe(pd.DataFrame(freshness_rows), hide_index=True, width="stretch")
    st.subheader("外部因素背景（研究中）")
    st.caption("各项的地区、频率与单位不同，不能直接相加或比较。")
    factor_rows = []
    for field in ("wti_cushing_spot_price", "usd_cad_monthly", "boc_energy_price_index",
                  "toronto_residential_construction_cost_index"):
        observations = latest(db, field)
        item = observations[-1] if observations else None
        if item is None:
            value = "暂无数据"
        else:
            decimals = 4 if field == "usd_cad_monthly" else 1 if field == "toronto_residential_construction_cost_index" else 2
            value = f"{item['value']:,.{decimals}f}"
        factor_rows.append({"指标": SERIES[field][0], "数值": value,
                            "单位": SERIES[field][4],
                            "资料期": item["period"] if item else "—",
                            "地区": SERIES[field][3],
                            "来源": SERIES[field][1]})
    st.dataframe(pd.DataFrame(factor_rows), hide_index=True, width="stretch")
    with st.expander("指标定义与原始来源"):
        field = st.selectbox("指标", list(SERIES), format_func=label)
        details = SERIES[field]
        st.write(f"**{details[0]}** · {details[3]} · {details[4]}")
        st.write(details[8])
        st.caption(f"{details[1]} · {details[2]} · {details[5]} · {details[6]} · {RULES[field].schedule}")
        st.markdown(f"[打开数据来源]({SERIES_URLS[field]})")
    st.divider()
    st.subheader("月度观察记录")
    st.caption("保存本地观测及来源版本，便于日后对照；选历史月份不代表还原当时的信息集。")
    chosen = st.selectbox("记录月份", list(reversed(resale_periods)), format_func=period_label)
    if st.button("保存本地记录", type="primary"):
        location = save(db, chosen, ROOT / "data/observations")
        st.success(f"已保存 {location.name}")
    saved = sorted((ROOT / "data/observations").glob("observation-*.json"), reverse=True)
    if saved:
        selected = st.selectbox("打开既有记录", saved, format_func=lambda path: path.name)
        snapshot = open_snapshot(selected)
        st.caption(f"资料所属期：{period_label(snapshot['period'])} · 保存时间：{snapshot['saved_at']}")
        records = [{"指标": label(f), "数值": formatted(v, f)} for f, v in snapshot["values_for_period"].items() if f in SERIES or f in ("moi_raw", "snlr_raw")]
        st.dataframe(pd.DataFrame(records), hide_index=True, width="stretch")
        with st.expander("记录的完整版本与来源凭据"):
            st.json(snapshot, expanded=False)
        st.download_button("下载这份记录", selected.read_bytes(), selected.name, "application/json")
    with st.expander("最近导入运行"):
        st.caption("来源内容未变化表示已完成检查但没有新原件；不会推进数据所属期。新增、未变、修订三列仅统计实际解析入库的观测。")
        runs = pd.read_sql_query("SELECT source AS 来源,started_at AS 运行时间,status AS 状态,inserted AS 新增,unchanged AS 未变,revised AS 修订,error AS 错误 FROM ingestion_runs ORDER BY id DESC LIMIT 10", db)
        runs["状态"] = runs["状态"].replace({"success": "导入完成", "unchanged": "来源内容未变化", "failed": "失败"})
        st.dataframe(runs, hide_index=True, width="stretch")
    with st.expander("数据边界与预测验证状态"):
        st.write("TRREB 为全市场；就业、人口和租赁采用 Toronto CMA 2021 边界，建设为 CMA 2011 边界，利率为加拿大背景。不同地理总体不计算交叉比率。")
        st.write("TRREB 原报告还有地区及成交房型细分；当前界面提供全市场总量和 HPI 房型比较。租赁页范围为公寓，不覆盖全部出租住宅类型。")
        st.write("目前不提供复苏评分或预测。逐期发布日期、历史修订可用时点、季节比较规则与样本外验证尚未齐备。Condo 纯预售也没有纳入；建设公寓类别不能替代预售库存。")

st.caption("公开数据研究工具 · 非实时行情 · 不构成投资建议")
db.close()
