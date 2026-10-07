"""Monthly asking rents remain separate from CMHC's annual occupied stock."""
import pandas as pd
from .catalog import ASKING_ROOMS
from .dashboard import cards, line_chart, bar_chart, note
from .freshness import assess
from .i18n import st
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
