"""Shared owner/viewer section for the market temperature reading (see market_temperature.py)."""
from html import escape

from .i18n import st, english

LABELS = {'cool': ('偏冷', 'Cool'), 'balanced': ('平衡', 'Balanced'), 'hot': ('偏热', 'Hot')}
MEANING = {'cool': ('买方议价空间较大', 'buyers have more leverage'),
           'balanced': ('供需大致平衡', 'supply and demand roughly balanced'),
           'hot': ('卖方占优', 'sellers have the upper hand')}


def _month(period):
    return period if english() else f'{period[:4]}年{int(period[5:])}月'


def _card(r, band, period, en):
    """Gauge from -30 to +30 pp (wider when needed), same layout as the published site."""
    i = 1 if en else 0
    limit = max(30, -(-abs(r['gap']) // 10) * 10)
    pos = (max(-limit, min(limit, r['gap'])) + limit) / (2 * limit) * 100
    side, mid = (limit - band) / (2 * limit) * 100, band / limit * 100
    gap = f"{r['gap']:+.1f}".replace('-', '−')
    zones = (('cool', side), ('balanced', mid), ('hot', side))
    track = ''.join(f'<span class="zone {k}" style="width:{w:.2f}%"></span>' for k, w in zones)
    labels = ''.join(f'<span class="{"current" if k == r["state"] else ""}" style="width:{w:.2f}%">{escape(LABELS[k][i])}</span>'
                     for k, w in zones)
    reading = (f"Three-month sales-to-new-listings ratio {r['snlr3']:.1f}%, {abs(r['gap']):.1f} pp {'below' if r['gap'] < 0 else 'above'} "
               f"its seasonal norm of {r['snlr_norm']:.1f}%: {MEANING[r['state']][1]}. Three-month months of inventory {r['moi3']:.1f} (norm {r['moi_norm']:.1f})."
               if en else
               f"近三个月成交／新挂牌比 {r['snlr3']:.1f}%，比同期历史常态 {r['snlr_norm']:.1f}% {'低' if r['gap'] < 0 else '高'} {abs(r['gap']):.1f} 个百分点："
               f"{MEANING[r['state']][0]}。近三个月库存月数 {r['moi3']:.1f}（同期常态 {r['moi_norm']:.1f}）。")
    return (f'<div class="temp-card"><div class="temp-card-head"><span class="temperature-chip {r["state"]}">{escape(LABELS[r["state"]][i])}</span>'
            f'<span class="temperature-month">{escape(_month(period))} · {"last three months" if en else "近三个月"}</span></div>'
            f'<div class="gauge"><span class="gauge-marker" style="left:{pos:.1f}%"><b>{gap}</b></span><div class="gauge-track">{track}</div>'
            f'<div class="gauge-labels">{labels}</div></div><p>{escape(reading)}</p></div>')


def render(temperature, end, month_key=None, selectable=()):
    """Show the reading for the latest month at or before `end`; quiet when no data.

    With `month_key` (the page's observation-month selectbox) a click on a heatmap cell
    from `selectable` moves the whole page to that month, as on the published site.
    """
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
    st.subheader('Market temperature' if en else '市场温度')
    st.html(_card(r, band, period, en))
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
    rows = []
    for k in ('cool', 'balanced', 'hot'):
        o = temperature['outcomes_12m'][k]
        change = '—' if o['mean_change'] is None else f"{o['mean_change']:+.1f}%".replace('-', '−')
        share = '—' if o['share_up'] is None else f"{o['share_up'] * 100:.0f}%"
        now = k == r['state']
        tag = f'<small>{"now" if en else "当前"}</small>' if now else ''
        rows.append(f'<div class="outcome-row{" current" if now else ""}"><span class="outcome-name">{escape(LABELS[k][i])}{tag}</span>'
                    f'<b>{change}</b><span class="outcome-meta">{share} {"rose" if en else "上涨"} · {o["n"]} {"months" if en else "个月"}</span></div>')
    heading = 'HPI over the following 12 months, by reading' if en else '历史上，各温度之后 12 个月的 HPI'
    st.html(f'<div class="outcomes"><h3>{heading}</h3>{"".join(rows)}</div>')
    heatmap(temperature, period, en, month_key, selectable)
    st.caption('Historical TRREB HPI statistics since 2012; out-of-sample research (from 2018) found this reading informative about '
               'price direction over the next 6–12 months. It describes market balance; it is not a forecast or investment advice.'
               if en else '2012 年以来 TRREB HPI 的历史统计；样本外研究（2018 年起）显示该读数对未来 6–12 个月价格方向有参考意义。'
               '描述供需状况，不是预测，不构成投资建议。')


def heatmap(temperature, selected, en, month_key=None, selectable=()):
    """Year x month grid of the gap to the seasonal norm (2012 on), the selected month outlined."""
    import altair as alt
    import pandas as pd
    import streamlit as native_st
    months, i = temperature['months'], 1 if en else 0
    rows = [{'period': p, 'year': p[:4], 'month': int(p[5:7]), 'gap': r['gap'],
             'reading': LABELS[r['state']][i], 'label': _month(p)} for p, r in sorted(months.items()) if p >= '2012-01']
    if not rows:
        return
    keys = sorted(months)
    run = 0
    for p in reversed([k for k in keys if k <= selected]):
        if months[p]['state'] != months[selected]['state']:
            break
        run += 1
    last_hot = max((p for p in keys if p <= selected and months[p]['state'] == 'hot'), default=None)
    native_st.markdown(f"**{'Month-by-month heatmap' if en else '逐月热力图'}**")
    frame = pd.DataFrame(rows)
    pick = alt.selection_point(fields=['period'], name='cell')
    month_names = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split() if en else [f'{m}月' for m in range(1, 13)]
    label_expr = '[' + ','.join(f'"{n}"' for n in month_names) + '][datum.value - 1]'
    chart = alt.Chart(frame).mark_rect(cornerRadius=2).encode(
        x=alt.X('month:O', title=None, axis=alt.Axis(labelExpr=label_expr, labelAngle=0, orient='top', domain=False, ticks=False)),
        y=alt.Y('year:O', title=None, axis=alt.Axis(domain=False, ticks=False, labelOverlap=False)),
        color=alt.Color('gap:Q', scale=alt.Scale(domain=[-30, 0, 30], range=['#2855d9', '#f3f3f3', '#bf6517'], clamp=True),
                        legend=alt.Legend(title='pp' if en else '个百分点', orient='bottom', gradientLength=240)),
        stroke=alt.condition(alt.datum.period == selected, alt.value('#171717'), alt.value('#ffffff')),
        strokeWidth=alt.condition(alt.datum.period == selected, alt.value(2.5), alt.value(1)),
        tooltip=[alt.Tooltip('label:N', title='Month' if en else '月份'), alt.Tooltip('gap:Q', format='+.1f', title='Gap (pp)' if en else '相差（个百分点）'),
                 alt.Tooltip('reading:N', title='Reading' if en else '温度')],
    ).add_params(pick).properties(height=26 * frame.year.nunique())
    options = set(selectable)

    def jump():
        picked = (native_st.session_state.get(f'heatmap-{month_key}') or {}).get('selection', {}).get('cell') or []
        period = picked[0].get('period') if picked else None
        if period in options:
            native_st.session_state[month_key] = period

    if month_key and options:
        native_st.altair_chart(chart, use_container_width=True, on_select=jump, selection_mode='cell', key=f'heatmap-{month_key}')
    else:
        native_st.altair_chart(chart, use_container_width=True)
    state = months[selected]['state']
    if en:
        reading = f"{_month(selected)} reads {LABELS[state][1].lower()}, {run} month{'s' if run > 1 else ''} in a row" + (f"; the last hot month was {_month(last_hot)}." if last_hot else '.')
        hint = ' Select a cell from September 2022 on to move the page to that month.' if month_key and options else ''
    else:
        reading = f"{_month(selected)}为{LABELS[state][0]}，已连续 {run} 个月{LABELS[state][0]}" + (f"；上一次偏热是 {_month(last_hot)}。" if last_hot else '。')
        hint = '点 2022 年 9 月以后的格子，整页切到该月。' if month_key and options else ''
    native_st.caption(reading + hint)
