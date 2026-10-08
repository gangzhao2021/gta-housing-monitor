"""Monthly asking rents remain separate from CMHC's annual occupied stock."""
from html import escape

import pandas as pd
from .catalog import ASKING_ROOMS
from .dashboard import cards, line_chart, bar_chart, note
from .freshness import assess
from .i18n import st, english
from .presentation import available_periods
from .rentals import PREFIX


def render_monthly(db, data, today, controls):
    total = PREFIX + "total"
    periods = available_periods(data, [total])
    if not periods:
        st.info("尚未导入月度挂牌租金。")
        return
    with st.container(key="asking-story"):
        context, plot = st.columns([1, 3.4], gap="large")
    with context:
        selection = st.selectbox("走势房型", ["total", "compare", "1br", "2br", "3br"],
                                 format_func=lambda r: "房型对比" if r == "compare" else ASKING_ROOMS[r], key="asking-room")
        fields = [PREFIX + r for r in ("1br", "2br", "3br")] if selection == "compare" else [PREFIX + selection]
        start, end = controls(fields, "asking", targets=(context, context))
    coverage = available_periods(data, fields)
    start = max(start, coverage[0])
    with plot:
        st.subheader("月度挂牌租金走势")
        line_chart(data, fields, start, end, height=380, names={f: ASKING_ROOMS[f.removeprefix(PREFIX)] for f in fields}, points=True)
    with context if len(fields) == 1 else plot:
        cards(data, fields, end)
    with plot:
        for field in fields:
            visible = [p for p in available_periods(data, [field]) if start <= p <= end]
            st.caption(f"{ASKING_ROOMS[field.removeprefix(PREFIX)]} · 所选期间实际观测：{len(visible)} 个")
            if 0 < len(visible) < 3:
                st.warning(f"{ASKING_ROOMS[field.removeprefix(PREFIX)]}：当前仅有 {len(visible)} 个观测点；连线只表示已知点之间的变化，不足以判断长期趋势。")
    st.caption(f"当前房型历史覆盖：{coverage[0]} — {coverage[-1]}；缺月保留空白。")
    st.caption("Toronto · Rentals.ca / Urbanation · 专建出租公寓与 condo · 加元/月 · 未季调")
    note("挂牌租金反映出租广告报价，不是已签租约租金。Toronto 沿用来源市场定义；不能直接与 CMA 年度调查或 TRREB 全市场拼接。")
    state = assess(db, total, today)
    if state["latest_period"] != state["expected_period"]:
        st.warning(f"已接入数据截至 {periods[-1]}；最近完整月为 {state['expected_period']}。缺少的月份未补值。")
    year, month = map(int, end.split("-"))
    idx = year * 12 + month - 2
    previous = f"{idx // 12:04d}-{idx % 12 + 1:02d}"
    for field in fields:
        prior = data.get(previous, {}).get(field)
        value = data.get(end, {}).get(field)
        if prior and value is not None:
            st.caption(f"{ASKING_ROOMS[field.removeprefix(PREFIX)]} · 较上月变化：{(value / prior - 1) * 100:+.2f}%")
    st.divider()
    st.subheader("所选月份的房型报价")
    st.caption("分房型数据历史较短；三卧不含四卧及以上。")
    rooms = [{"房型": name, "月租金": data.get(end, {}).get(PREFIX + room)}
             for room, name in ASKING_ROOMS.items() if room != "total"]
    frame = pd.DataFrame(rooms)
    if frame["月租金"].notna().any():
        bar_chart(frame.dropna(), "房型", "月租金", "月租金（加元）", frame["房型"].tolist())
        st.dataframe(frame, hide_index=True, width="stretch")
    else:
        st.info("该月尚无已接入的分房型报价；请勿用最新一期替代历史月份。")
    st.caption("均值变化可能来自挂牌房源构成变化，不等于同一套房的租金涨幅。")
    with st.expander("月度租金数据与来源"):
        records = [dict(row) for row in db.execute('''
            SELECT o.period AS period, o.series_id AS series_id, o.value AS rent_cad_per_month,
                   o.version AS version, r.source AS source, r.source_url AS source_url,
                   r.path AS source_file, r.sha256 AS sha256, r.method AS provenance
            FROM observations o JOIN raw_files r ON r.sha256=o.raw_sha256
            WHERE o.series_id LIKE 'toronto_asking_rent_%' AND o.period BETWEEN ? AND ?
              AND o.version=(SELECT MAX(v.version) FROM observations v
                             WHERE v.series_id=o.series_id AND v.period=o.period)
            ORDER BY o.period,o.series_id''', (start, end))]
        export = pd.DataFrame(records)
        st.dataframe(export, hide_index=True, width="stretch")
        st.download_button("下载月度租金与来源", export.to_csv(index=False).encode("utf-8-sig"),
                           f"asking-rents-{start}-{end}.csv", "text/csv")
        st.markdown("[Rentals.ca / Urbanation — 报告归档](https://rentals.ca/blog/canada-national-rent-reports)")


PLUS = {"3br": "3plus"}
# (field template by bedroom, colour, label, source, cadence, meaning); a None field means no such category.
MEASURES = {
    "apartment": (
        (lambda r: None if r == "studio" else f"toronto_asking_rent_{r}", "#2855d9", ("挂牌租金", "Asking rent"), "Rentals.ca", "month",
         ("房东开价。最快反映新租约行情，但不是成交价。", "What landlords ask. Fastest read on new leases, but not a signed rent.")),
        (lambda r: f"gta_condo_lease_rent_{'bachelor' if r == 'studio' else r}", "#007f86", ("签约租金 · condo", "Signed lease · condo"), "TRREB", "quarter",
         ("经 MLS 实际租出的 condo 平均月租。季度更新。", "Average rent on condos actually leased through the MLS. Quarterly.")),
        (lambda r: f"toronto_condo_rent_{PLUS.get(r, r)}", "#bf6517", ("年度调查 · condo", "Annual survey · condo"), "CMHC", "year",
         ("含已住租客的平均实租。每年一次，变化最慢。", "Average rent actually paid, including sitting tenants. Yearly; moves slowest.")),
        (lambda r: f"toronto_pbr_rent_{PLUS.get(r, r)}", "#7952be", ("年度调查 · 专建出租", "Annual survey · purpose-built"), "CMHC", "year",
         ("专门建来出租的公寓，多为长期租客。", "Buildings built as rentals; mostly long-term tenants.")),
    ),
    "townhouse": (
        (lambda r: f"gta_townhouse_lease_rent_{'bachelor' if r == 'studio' else r}", "#007f86", ("签约租金 · 镇屋", "Signed lease · townhouse"), "TRREB", "quarter",
         ("经 MLS 实际租出的镇屋平均月租。季度更新。", "Average rent on townhouses actually leased through the MLS. Quarterly.")),
        (lambda r: f"toronto_row_rent_{PLUS.get(r, r)}", "#7952be", ("年度调查 · 专建出租镇屋", "Annual survey · purpose-built townhouses"), "CMHC", "year",
         ("专门建来出租的联排镇屋，含已住租客。", "Townhouse rentals built as such, including sitting tenants.")),
    ),
}
ROOMS = {"studio": ("开间", "Studio"), "1br": ("一卧", "1 bedroom"), "2br": ("两卧", "2 bedrooms"), "3br": ("三卧", "3 bedrooms")}


def latest_observations(db, fields):
    """{field: {period: value}} holding only each field's latest period, from the newest version."""
    out = {}
    for field in fields:
        row = db.execute("""SELECT period, value FROM observations o WHERE series_id=? AND version=(SELECT MAX(version)
            FROM observations WHERE series_id=o.series_id AND period=o.period) ORDER BY period DESC LIMIT 1""", (field,)).fetchone()
        if row:
            out[field] = {row[0]: row[1]}
    return out


def measure_fields():
    return [f for group in MEASURES.values() for field, *_ in group for room in ROOMS if (f := field(room))]


def render_measures(observations, key, room_keys=()):
    """Dumbbell of asking, signed and surveyed rents by unit type (published site, Figma 12).

    Streamlit cannot select on layered charts, so the unit-type radio drives the highlighted row and
    `room_keys`, the page's bedroom selectors below, follow it.
    """
    import altair as alt
    import pandas as pd
    import streamlit as native_st
    en = english()
    i = 1 if en else 0
    st.subheader("One unit type, different rent measures" if en else "同一房型，不同口径的租金")
    left, right = st.columns(2)
    with left:
        kind = st.radio("物业类型", ["apartment", "townhouse"], format_func={"apartment": "公寓", "townhouse": "镇屋"}.get,
                        horizontal=True, label_visibility="collapsed", key=key + "-type")
    def follow():
        chosen = native_st.session_state.get(key)
        for room_key, rooms in room_keys:
            if chosen in rooms:
                native_st.session_state[room_key] = chosen

    with right:
        room = st.radio("房型", list(ROOMS), index=1, format_func=lambda r: ROOMS[r][0], horizontal=True,
                        label_visibility="collapsed", key=key, on_change=follow)
    rows, missing = [], []
    for room_id, names in ROOMS.items():
        label = names[i] + ("*" if room_id == "3br" else "")
        for field, color, measure, source, kind_of_period, _ in MEASURES[kind]:
            series_id = field(room_id)
            series = observations.get(series_id) or {} if series_id else {}
            if not series:
                missing.append(f"{label} · {measure[i]}")
                continue
            period = max(series)
            if kind_of_period == "year":
                when = f"Oct {period}" if en else f"{period} 年 10 月"
            elif kind_of_period == "quarter":
                q = (int(period[5:7]) - 1) // 3 + 1
                when = f"{period[:4]} Q{q}" if en else f"{period[:4]} 年第 {q} 季度"
            else:
                when = period if en else f"{period[:4]} 年 {int(period[5:7])} 月"
            rows.append({"room": room_id, "type": label, "measure": measure[i], "color": color,
                         "rent": series[period], "when": f"{when} · {source}"})
    if not rows:
        return
    frame = pd.DataFrame(rows)
    order = [names[i] + ("*" if r == "3br" else "") for r, names in ROOMS.items()]
    measures = [m[2][i] for m in MEASURES[kind]]
    y = alt.Y("type:N", sort=order, title=None, axis=alt.Axis(domain=False, ticks=False, labelFontSize=13))
    band = alt.Chart(pd.DataFrame({"type": [order[list(ROOMS).index(room)]]})).mark_bar(color="#edf2ff", size=34).encode(
        y=y, x=alt.value(0), x2=alt.value("width"))
    rule = alt.Chart(frame).mark_rule(color="#c9c9c9", strokeWidth=2).encode(y=y, x="min(rent):Q", x2="max(rent):Q")
    dots = alt.Chart(frame).mark_circle(size=170, opacity=1, stroke="#ffffff", strokeWidth=2).encode(
        y=y, x=alt.X("rent:Q", title=None, scale=alt.Scale(zero=False, nice=True), axis=alt.Axis(format="$,.0f", tickCount=6)),
        color=alt.Color("measure:N", scale=alt.Scale(domain=measures, range=[m[1] for m in MEASURES[kind]]),
                        legend=alt.Legend(title=None, orient="top")),
        tooltip=[alt.Tooltip("type:N", title="Unit" if en else "房型"), alt.Tooltip("measure:N", title="Measure" if en else "口径"),
                 alt.Tooltip("rent:Q", format="$,.0f", title="Rent" if en else "租金"), alt.Tooltip("when:N", title="Source" if en else "来源")],
    )
    native_st.altair_chart(alt.layer(band, rule, dots).properties(height=220), use_container_width=True)
    note = ("\\* CMHC figures are 3+ bedrooms. The highlighted row is the unit type chosen above, which the trend below follows." if en else
            "\\* CMHC 为三卧及以上。高亮行是上方选中的房型，下方走势跟随它切换。")
    if missing:
        note += (" Not available: " if en else " 无数据：") + "、".join(missing) + ("." if en else "。")
    st.caption(note + (" Asking, signed and surveyed rents answer different questions; detached and semi-detached houses and shared rooms have no reliable public series."
                       if en else " 开价、成交和存量调查回答不同的问题；独立屋、半独立屋和单间合租暂无可靠公开数据。"))
