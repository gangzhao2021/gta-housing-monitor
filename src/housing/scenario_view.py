"""Shared owner/viewer sections for the economy readings and the price-first mortgage scenario (Figma 10/11)."""
from html import escape

from .affordability import amortization_by_year, monthly_payment, scenario, scenario_notes
from .i18n import st, english

READINGS = (("boc_policy_rate", ("加拿大央行政策利率", "Bank of Canada policy rate"), 2),
            ("mortgage_uninsured_fixed_5plus", ("5 年以上固定按揭（新发）", "New 5-year-plus fixed mortgage"), 2),
            ("toronto_unemployment_rate", ("多伦多失业率", "Toronto unemployment rate"), 1),
            ("ontario_mortgage_arrears_rate", ("Ontario 按揭拖欠率", "Ontario mortgage arrears rate"), 2))
NOTES_EN = {"首付低于 20% 需另付按揭保险费，此处未计入。": "Below 20% down, mortgage insurance is required; its premium is not included.",
            "房价超过 150 万加元须至少 20% 首付。": "Homes over $1.5 million need at least 20% down.",
            "首付不足 20% 时，30 年摊还仅限首次购房或新建住宅。": "With under 20% down, 30-year amortization is limited to first-time buyers or new builds."}


def _when(period, en):
    if len(period) > 7 or en:
        return period
    return f"{period[:4]} 年 {int(period[5:7])} 月"


def year_ago(series, period):
    """Value from the same month a year earlier (latest day on or before the same date for daily series)."""
    target = f"{int(period[:4]) - 1}{period[4:]}"
    earlier = [p for p in series if p <= target and p[:7] == target[:7]]
    return series[max(earlier)] if earlier else None


def render_readings(get_series):
    """Four headline readings with the value a year earlier; get_series(field) -> {period: value}."""
    en = english()
    cells = []
    for field, label, digits in READINGS:
        series = get_series(field) or {}
        if not series:
            continue
        period = max(series)
        before = year_ago(series, period)
        prior = f" · {'a year earlier' if en else '一年前'} {before:.{digits}f}%" if before is not None else ""
        cells.append(f'<div class="reading"><span>{escape(label[1 if en else 0])}</span><strong>{series[period]:.{digits}f}%</strong>'
                     f'<small>{escape(_when(period, en))}{prior}</small></div>')
    st.html(f'<div class="readings">{"".join(cells)}</div>')


def render_population(series):
    en = english()
    if not series:
        return
    year = max(series)
    value, prior = series[year], series.get(str(int(year) - 1))
    change = ""
    if prior:
        d = value - prior
        sign = "+" if d > 0 else "−" if d < 0 else ""
        change = (f" · vs prior year {sign}{abs(d):,.0f} ({sign}{abs(d / prior * 100):.2f}%)" if en else
                  f" · 较上年 {sign}{abs(d):,.0f} 人（{sign}{abs(d / prior * 100):.2f}%）")
    label = "Toronto CMA population" if en else "多伦多 CMA 人口"
    when = f"July 1, {year}" if en else f"{year} 年 7 月 1 日"
    st.html(f'<div class="population-stat"><div><span>{label}</span><strong>{value:,.0f}</strong></div>'
            f'<p>{escape(when + change)}{". One estimate a year, shown as a number rather than a line." if en else "。每年只有一个估计值，用数字而不是曲线展示。"}</p></div>')


def render_scenario(default_price, price_period, default_rate, rate_period, key):
    """Inputs on the left, payment, stress test, income and rate sensitivity on the right."""
    en = english()
    import streamlit as native_st
    # Keyed widgets lose their values when the page is not rendered; keep the last scenario and restore it.
    saved = native_st.session_state.setdefault(f"{key}-saved", {})
    defaults = {f"{key}-price": int(round(default_price)), f"{key}-down": 20, f"{key}-years": 25, f"{key}-rate": float(default_rate)}
    for name in (f"{key}-price", f"{key}-rate"):
        if name not in native_st.session_state:
            native_st.session_state[name] = saved.get(name, defaults[name])
    # Radios take their saved choice as an index; pre-setting their state as well would trigger a Streamlit warning.
    down_index = [10, 20, 35].index(saved.get(f"{key}-down", 20))
    years_index = [25, 30].index(saved.get(f"{key}-years", 25))
    left, right = st.columns([1, 1.7], gap="large")
    with left:
        price = st.number_input("房价（加元）", min_value=0, max_value=20_000_000, step=10_000, key=f"{key}-price")
        if price_period:
            st.caption(f"Default: TRREB HPI composite benchmark, {price_period}" if en else f"默认：{_when(price_period, False)} TRREB HPI 综合基准房价")
        down = st.radio("首付比例", [10, 20, 35], index=down_index, format_func=lambda v: f"{v}%", horizontal=True, key=f"{key}-down")
        years = st.radio("摊还年限", [25, 30], index=years_index, format_func=lambda v: f"{v} years" if en else f"{v} 年", horizontal=True, key=f"{key}-years")
        rate = st.number_input("名义年利率（%）", min_value=0.0, max_value=30.0, step=0.05, format="%.2f", key=f"{key}-rate")
        if rate_period:
            st.caption(f"Default: banks' average new 5-year-plus fixed rate, {rate_period}" if en else
                       f"默认：{_when(rate_period, False)} 银行新发 5 年以上固定按揭平均利率")
    native_st.session_state[f"{key}-saved"] = {name: native_st.session_state[name] for name in defaults}
    if price is None or rate is None:
        with right:
            st.info("Enter every assumption to see the payment." if en else "请填写全部假设后查看月供。")
        return None
    s = scenario(price, down, years, rate)
    with left:
        st.html(f'<div class="loan-line"><span>{"Down payment" if en else "首付"} ${s["down"]:,.0f}</span>'
                f'<span>{"Loan" if en else "贷款金额"} <strong>${s["loan"]:,.0f}</strong></span></div>')
        for note in scenario_notes(price, down, years):
            st.html(f'<p class="message">{escape(NOTES_EN[note] if en else note)}</p>')
    sens = []
    for step in (-1, 0, 1, 2):
        r = rate + step
        if r < 0:
            continue
        p = monthly_payment(s["loan"], r, years)
        diff = "current" if en and step == 0 else "当前假设" if step == 0 else f"{'+' if p > s['payment'] else '−'}${abs(p - s['payment']):,.0f}"
        sens.append(f'<div class="sens-col{" current" if step == 0 else ""}"><span>{r:.2f}%</span><strong>${p:,.0f}</strong><small>{diff}</small></div>')
    interest = round(s["interest"] / 100) * 100
    with right:
        st.html(f'''<div class="payment-main"><span>{"Monthly principal & interest" if en else "每月本息"}</span>
<div><span class="payment-big">${s["payment"]:,.2f}</span><span class="per">{"/ month" if en else "/ 月"}</span></div>
<small>{f"About ${interest:,.0f} of interest over {years} years" if en else f"{years} 年共付利息约 ${interest:,.0f}"}</small></div>
<div class="mortgage-cards"><div class="mortgage-card"><strong>{"Stress-test payment" if en else "压力测试月供"}</strong><span>${s["stress_payment"]:,.2f}</span>
<p>{f"At {s['qualifying_rate']:.2f}%: the higher of the contract rate + 2 points and 5.25%, which lenders use to qualify borrowers." if en else f"按 {s['qualifying_rate']:.2f}% 计算：合同利率 +2 个百分点与 5.25% 取较高者，银行用它审核贷款。"}</p></div>
<div class="mortgage-card"><strong>{"Approximate household income needed" if en else "大约需要的家庭年收入"}</strong><span>${round(s["income"] / 1000) * 1000:,.0f}</span>
<p>{"Stress-test payment at no more than 39% of income; excludes property tax, heating and condo fees, so the real requirement is higher." if en else "按压力测试月供不超过收入 39% 估算；未含物业税、取暖和 condo 管理费，实际要求更高。"}</p></div></div>
<h3 class="sens-title">{"If the rate changes" if en else "如果利率变化"}</h3><div class="sens-row">{"".join(sens)}</div>''')
    with right:
        render_amortization(s["loan"], rate, years, key, en)
    return {"loan": s["loan"], "years": years, "rate": rate}


def render_amortization(loan, rate, years, key, en):
    """Yearly principal and interest bars; a rate picker mirrors the site's clickable rate table."""
    import altair as alt
    import pandas as pd
    import streamlit as native_st
    if loan <= 0:
        return
    steps = [step for step in (-1, 0, 1, 2) if rate + step >= 0]
    step = native_st.radio("Chart rate" if en else "图表利率", steps, index=steps.index(0), horizontal=True,
                           format_func=lambda d: f"{rate + d:.2f}%", key=f"{key}-amort-step")
    chart_rate = rate + step
    rows = amortization_by_year(loan, chart_rate, years)
    principal, interest = ("Principal", "Interest") if en else ("本金", "利息")
    frame = pd.DataFrame([{"year": r["year"], "part": part, "amount": r[field], "order": order,
                           "balance": r["balance"]} for r in rows
                          for part, field, order in ((principal, "principal", 0), (interest, "interest", 1))])
    native_st.markdown(f"**{'Each year: principal and interest' if en else '每年还的钱：本金与利息'}（{chart_rate:.2f}%）**")
    chart = alt.Chart(frame).mark_bar().encode(
        x=alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0, values=[1, *range(5, years + 1, 5)])),
        y=alt.Y("sum(amount):Q", title=None, axis=alt.Axis(format="$,.0f")),
        color=alt.Color("part:N", scale=alt.Scale(domain=[principal, interest], range=["#007f86", "#bf6517"]),
                        legend=alt.Legend(title=None, orient="top")),
        order=alt.Order("order:Q"),
        tooltip=[alt.Tooltip("year:O", title="Year" if en else "年份"), alt.Tooltip("part:N", title=""),
                 alt.Tooltip("amount:Q", format="$,.0f", title="Amount" if en else "金额"),
                 alt.Tooltip("balance:Q", format="$,.0f", title="Year-end balance" if en else "年末剩余本金")],
    ).properties(height=240)
    native_st.altair_chart(chart, use_container_width=True)
    five = rows[:5]
    paid, paid_interest = sum(r["principal"] + r["interest"] for r in five), sum(r["interest"] for r in five)
    total = sum(r["interest"] for r in rows)
    cross = next((r["year"] for r in rows if r["principal"] > r["interest"]), None)
    facts = [("Paid in the first 5 years" if en else "前 5 年共还", f"${round(paid, -2):,.0f}"),
             ("of which interest" if en else "其中利息", f"${round(paid_interest, -2):,.0f}（{paid_interest / paid * 100:.0f}%）"),
             (f"Interest over {years} years" if en else f"{years} 年利息合计", f"${round(total, -2):,.0f}")]
    if len(rows) >= 10:
        facts.append(("Balance after year 10" if en else "第 10 年末剩余本金", f"${round(rows[9]['balance'], -2):,.0f}"))
    st.html('<div class="amort-facts">' + ''.join(f'<div><span>{escape(a)}</span><b>{escape(b)}</b></div>' for a, b in facts) + '</div>')
    if cross:
        native_st.caption(f"Principal exceeds interest from year {cross}." if en else f"第 {cross} 年起本金超过利息。")
