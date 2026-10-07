"""Shared owner/viewer section for the market temperature reading (see market_temperature.py)."""
from html import escape

from .i18n import st, english

LABELS = {'cool': ('偏冷', 'Cool'), 'balanced': ('平衡', 'Balanced'), 'hot': ('偏热', 'Hot')}
MEANING = {'cool': ('买方议价空间较大', 'buyers have more leverage'),
           'balanced': ('供需大致平衡', 'supply and demand roughly balanced'),
           'hot': ('卖方占优', 'sellers have the upper hand')}


def _month(period):
    return period if english() else f'{period[:4]}年{int(period[5:])}月'


def render(temperature, end):
    """Show the reading for the latest month at or before `end`; quiet when no data."""
    if not temperature or not temperature.get('months'):
        return
    import altair as alt
    import pandas as pd
    en = english()
    i = 1 if en else 0
    months = temperature['months']
    period = max((p for p in months if p <= end), default=None)
    if period is None:
        return
    r, band = months[period], temperature['band_pp']
    gap = f"{r['gap']:+.1f}"
    st.subheader('Market temperature' if en else '市场温度')
    reading = (f"Sales-to-new-listings ratio <strong>{r['snlr3']:.1f}%</strong> vs a seasonal norm of {r['snlr_norm']:.1f}%: "
               f"<strong>{gap}</strong> pp; {MEANING[r['state']][1]}. Months of inventory {r['moi3']:.1f} (norm {r['moi_norm']:.1f})."
               if en else
               f"成交／新挂牌比 <strong>{r['snlr3']:.1f}%</strong>，同月历史常态 {r['snlr_norm']:.1f}%，相差 <strong>{gap}</strong> 个百分点；"
               f"{MEANING[r['state']][0]}。库存月数 {r['moi3']:.1f}（常态 {r['moi_norm']:.1f}）。")
    st.html(f'<div class="temperature-reading"><span class="temperature-chip {r["state"]}">{escape(LABELS[r["state"]][i])}</span>'
            f'<p>{reading}</p><span class="temperature-month">{escape(_month(period))} · {"last three months" if en else "近三个月"}</span></div>')
    recent = sorted(p for p in months if p <= period)[-36:]
    frame = pd.DataFrame({'month': pd.to_datetime([p + '-01' for p in recent]), 'gap': [months[p]['gap'] for p in recent]})
    limit = max(25.0, (int(max(abs(v) for v in frame.gap) / 5) + 1) * 5)
    bands = pd.DataFrame({'low': [band, -limit], 'high': [limit, -band], 'kind': ['hot', 'cool']})
    x = alt.X('month:T', title=None, axis=alt.Axis(format='%y/%m', tickCount=6))
    shade = alt.Chart(bands).mark_rect(opacity=0.55).encode(
        y=alt.Y('low:Q', scale=alt.Scale(domain=[-limit, limit]), title='pp' if en else '百分点'), y2='high:Q',
        color=alt.Color('kind:N', scale=alt.Scale(domain=['hot', 'cool'], range=['#fbeee3', '#e8eeff']), legend=None))
    zero = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(color='#bbbbbb').encode(y='y:Q')
    line = alt.Chart(frame).mark_line(color='#2855d9', strokeWidth=2.5).encode(
        x=x, y=alt.Y('gap:Q', scale=alt.Scale(domain=[-limit, limit])),
        tooltip=[alt.Tooltip('month:T', format='%Y-%m', title='Month' if en else '月份'),
                 alt.Tooltip('gap:Q', format='+.1f', title='Gap (pp)' if en else '相差（百分点）')])
    # Native call: the translating wrapper rebinds a single dataset and would drop the layers' data.
    # Labels above are already chosen by language and the columns are ASCII.
    import streamlit as native_st
    native_st.altair_chart(alt.layer(shade, zero, line).properties(height=190), use_container_width=True)
    st.caption(f'Hot when {band:g} pp or more above the norm, cool when {band:g} pp or more below.' if en else
               f'高于常态 {band:g} 个百分点以上为偏热，低于 {band:g} 个百分点以上为偏冷。')
    head = ('Reading', 'Months', 'Avg HPI change, next 12 months', 'Share followed by a rise') if en else \
           ('温度', '月数', '其后 12 个月 HPI 平均变化', '其后上涨的比例')
    rows = []
    for k in ('cool', 'balanced', 'hot'):
        o = temperature['outcomes_12m'][k]
        change = '—' if o['mean_change'] is None else f"{o['mean_change']:+.1f}%"
        share = '—' if o['share_up'] is None else f"{o['share_up'] * 100:.0f}%"
        current = 'current' if k == r['state'] else ''
        rows.append(f'<tr class="{current}"><th scope="row">{escape(LABELS[k][i])}</th><td>{o["n"]}</td>'
                    f'<td>{change}</td><td>{share}</td></tr>')
    body = ''.join(rows)
    st.html(f'<table class="temperature-table"><thead><tr>{"".join(f"<th>{escape(h)}</th>" for h in head)}</tr></thead>'
            f'<tbody>{body}</tbody></table>')
    st.caption('Historical TRREB HPI statistics since 2012; out-of-sample research (from 2018) found this reading informative about '
               'price direction over the next 6–12 months. It describes market balance; it is not a forecast or investment advice.'
               if en else '2012 年以来 TRREB HPI 的历史统计；样本外研究（2018 年起）显示该读数对未来 6–12 个月价格方向有参考意义。'
               '描述供需状况，不是预测，不构成投资建议。')
