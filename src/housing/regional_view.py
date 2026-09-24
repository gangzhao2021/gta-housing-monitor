"""Same-source regional comparison with visible gaps and source-scoped exports."""
from pathlib import Path
from html import escape
import altair as alt
import pandas as pd
import pydeck as pdk
from .i18n import st
from .i18n import english
from .catalog import SERIES, ASKING_ROOMS, RENTAL_BEDROOMS
from .regions import MONTHLY_REGIONS, CMHC_REGIONS, asking_id, cmhc_id
from .db import latest
from .presentation import annual_data, available_periods, calendar_periods, metric_at
from .dashboard import line_chart, series_color
from .regional_ingest import regional_cmhc_details

ROOT = Path(__file__).resolve().parents[2]
UNAVAILABLE = {'downtown': 'Downtown Toronto', 'richmond_hill': 'Richmond Hill', 'aurora': 'Aurora'}
# Approximate reference locations for point selection, not statistical boundaries.
# Their placement does not claim neighbourhood-level precision or rent coverage.
MAP_POINTS = {
    'toronto': (-79.3832, 43.6532), 'north_york': (-79.4111, 43.7615),
    'scarborough': (-79.2318, 43.7764), 'markham': (-79.3370, 43.8561),
    'vaughan': (-79.5083, 43.8372), 'mississauga': (-79.6441, 43.5890),
    'oakville': (-79.6877, 43.4675),
    'richmond_vaughan_king': (-79.4700, 43.8800),
    'aurora_newmarket_whit': (-79.4400, 44.0200),
}


@st.cache_data(show_spinner=False)
def annual_evidence(path, stamp):
    return regional_cmhc_details(path)


def annual_publication_status(db):
    """Evidence for withheld cells, which have no numeric observation row."""
    result = {}
    for raw in db.execute("SELECT path FROM raw_files WHERE path LIKE '%rmr-toronto-%xlsx' ORDER BY retrieved_at, path"):
        path = ROOT / raw['path']
        if path.is_file():
            for item in annual_evidence(str(path), path.stat().st_mtime_ns):
                result[(item['series_id'], item['period'])] = item['status']
    return result


def export_rows(db, fields, start, end, annual=False):
    evidence = {}
    if annual:
        for raw in db.execute("SELECT * FROM raw_files WHERE path LIKE '%rmr-toronto-%xlsx' ORDER BY path"):
            path = ROOT / raw['path']
            for item in annual_evidence(str(path), path.stat().st_mtime_ns):
                evidence[(item['series_id'], item['period'])] = {**item, 'source_file': raw['path'], 'source_url': raw['source_url'], 'sha256': raw['sha256']}
    records = []
    for field in fields:
        known = {r['period']: dict(r) for r in db.execute('''
            SELECT o.*,r.path AS source_file,r.source_url,r.method,r.sha256
            FROM observations o JOIN raw_files r ON o.raw_sha256=r.sha256
            WHERE o.series_id=? AND o.version=(SELECT MAX(x.version) FROM observations x
                  WHERE x.series_id=o.series_id AND x.period=o.period)''', (field,))}
        for period in calendar_periods(start, end):
            item = known.get(period, {})
            detail = evidence.get((field, period), {})
            records.append({'period': period, 'series_id': field, 'region': SERIES[field][3],
                'measure': SERIES[field][0], 'value': item.get('value'), 'unit': SERIES[field][4],
                'status': 'available' if item else detail.get('status', 'not_available'),
                'source': SERIES[field][1], 'source_url': item.get('source_url', detail.get('source_url')),
                'source_file': item.get('source_file', detail.get('source_file')),
                'sha256': item.get('sha256', detail.get('sha256')), 'version': item.get('version'),
                'quality': detail.get('quality'), 'sheet': detail.get('sheet'), 'cell': detail.get('cell')})
    return records


def monthly_coverage(db):
    records = []
    for region, name in MONTHLY_REGIONS.items():
        for room, label in ASKING_ROOMS.items():
            rows = latest(db, asking_id(region, room))
            periods = [r['period'] for r in rows]
            records.append({'地区': name, '房型': label,
                '最早观测': periods[0] if periods else '—',
                '最新观测': periods[-1] if periods else '—', '观测数': len(periods),
                '覆盖期间缺月': len(calendar_periods(periods[0], periods[-1])) - len(periods) if periods else None})
    return records


def unavailable_reason(db, region, room, annual=False, measure='rent'):
    if not annual:
        if region == 'downtown':
            return '尚未核定 Downtown 边界并取得对应月度数据。'
        if region in UNAVAILABLE:
            return '尚无已核验的独立月度序列；年度组合调查区不能拆成单个城市。'
        return '已核验月度图表未提供这个地区的该房型数据；总体均值不能代替分房型租金。'
    field = cmhc_id(region, measure, room)
    statuses = []
    for raw in db.execute("SELECT path FROM raw_files WHERE path LIKE '%rmr-toronto-%xlsx'"):
        path = ROOT / raw['path']
        statuses.extend(item['status'] for item in annual_evidence(str(path), path.stat().st_mtime_ns) if item['series_id'] == field)
    if statuses and all(status == 'suppressed' for status in statuses):
        return 'CMHC 已核验年份均抑制发布该项数值，不能估算填补。'
    return '该口径尚无已接入观测。'


def select_annual_alternative(region, room):
    choices = {'region-source': '年度存量租金（CMHC）', 'region-True-0': region,
               'region-True-1': 'none', 'region-True-2': 'none',
               'region-room-True': room, 'region-measure': 'rent'}
    st.session_state.update(choices)
    st.session_state.setdefault('ui-selections', {}).update(choices)


def comparable_change_rows(data, fields, names, start, end):
    """Compare only observations shared by every selected source series."""
    common = set.intersection(*(set(available_periods(data, [field])) for field in fields)) if fields else set()
    common = sorted(period for period in common if start <= period <= end)
    if len(common) < 2:
        return [], None
    first, last = common[0], common[-1]
    rows = []
    for field in fields:
        before, after = data[first][field], data[last][field]
        if before is None or before <= 0 or after is None:
            return [], None
        rows.append({'地区': names[field], '期间变化（%）': (after / before - 1) * 100,
                     '起期值': before, '末期值': after, '起期': first, '末期': last})
    return rows, (first, last)


def select_map_region(region, annual, labels):
    if region not in labels:
        return
    keys = [f'region-{annual}-{index}' for index in range(3)]
    current = [st.session_state.get(key) for key in keys]
    if region in current:
        selected_index = current.index(region)
        if selected_index:
            st.session_state[keys[selected_index]] = 'none'
            st.session_state.setdefault('ui-selections', {})[keys[selected_index]] = 'none'
        else:
            st.session_state['map-selection-message'] = '主要地区请通过“编辑地区”更换。'
        return
    # Keep the primary region and add clicked peers until the comparison is full.
    vacancy = next((index for index in (1, 2) if current[index] == 'none'), None)
    if vacancy is None:
        st.session_state['map-selection-message'] = '已选择三个地区；请先在“编辑地区”移除一个，再从地图加入。'
        return
    st.session_state[keys[vacancy]] = region
    st.session_state.setdefault('ui-selections', {})[keys[vacancy]] = region


def map_selected(annual, labels):
    event = st.session_state.get(f'regional-map-{annual}', {})
    objects = event.get('selection', {}).get('objects', {}).get('regions', [])
    if objects:
        select_map_region(objects[0].get('region'), annual, labels)


def render_map(data, labels, chosen, room, measure, annual, end):
    points = []
    for region, name in labels.items():
        if region not in MAP_POINTS:
            continue
        field = cmhc_id(region, measure, room) if annual else asking_id(region, room)
        value = data.get(end, {}).get(field)
        longitude, latitude = MAP_POINTS[region]
        points.append({'region': region, 'name': name, 'lon': longitude, 'lat': latitude,
                       'value': value, 'shown': '无观测' if value is None else f'{value:,.1f}%' if measure == 'vacancy' else f'${value:,.0f}',
                       'selected': region in chosen})
    values = [p['value'] for p in points if p['value'] is not None]
    low, high = (min(values), max(values)) if values else (0, 0)
    for point in points:
        if point['value'] is None:
            point['fill'] = [170, 178, 188, 185]
        else:
            fraction = (point['value'] - low) / (high - low) if high > low else 0.5
            point['fill'] = [int(42 - 38 * fraction), int(95 + 45 * fraction), int(200 - 72 * fraction), 220]
        point['radius'] = 12000 if point['selected'] else 9500
    title = '地区探索地图' if not english() else 'Explore areas'
    st.subheader(title)
    st.caption(('位置点仅帮助选区，不代表统计边界或街道级租金；灰色表示该期无观测。点击加入或移除对比地区，最多三个。'
                if not english() else 'Reference points aid selection; they are not statistical boundaries or street-level rents. Grey means no observation. Click to add or remove a comparison area, up to three.'))
    if not points:
        return
    layer = pdk.Layer('ScatterplotLayer', id='regions', data=points, get_position='[lon, lat]',
                      get_fill_color='fill', get_radius='radius', radius_min_pixels=9,
                      radius_max_pixels=22, pickable=True, auto_highlight=True,
                      get_line_color=[255, 255, 255], line_width_min_pixels=2)
    deck = pdk.Deck(layers=[layer], map_style=None, initial_view_state=pdk.ViewState(
        latitude=43.755, longitude=-79.45, zoom=9.4, pitch=0),
        tooltip={'text': '{name}\n{shown} · ' + end + (' · CMHC annual survey' if annual else ' · Rentals.ca / Urbanation monthly asking')},
    )
    st.pydeck_chart(deck, key=f'regional-map-{annual}', on_select=lambda: map_selected(annual, labels),
                    selection_mode='single-object', height=340)
    message = st.session_state.pop('map-selection-message', None)
    if message:
        st.info(message)


def render_regions(db, monthly_data, today):
    with st.container(key='regional-story'):
        rail, plot = st.columns([1, 3.4], gap='large')
    with rail:
        filters = st.container(border=False, key='regional-filters')
    with filters:
        region_names = st.empty()
        with st.container(key='regional-actions'):
            edit_col, room_col = st.columns([1, 1.4])
            with edit_col:
                region_editor = st.popover('编辑地区')
        with st.expander('口径与时间'):
            source_col = st.container()
            detail_col = st.container()
            date_col = st.container()
        with source_col:
            annual = st.selectbox('地区数据口径', ['月度挂牌租金', '年度存量租金（CMHC）'], format_func=lambda v: '年度 · CMHC' if v == '年度存量租金（CMHC）' else '月度 · Rentals.ca', key='region-source') == '年度存量租金（CMHC）'
        rooms = RENTAL_BEDROOMS if annual else ASKING_ROOMS
        labels = CMHC_REGIONS if annual else {**MONTHLY_REGIONS, **UNAVAILABLE}
        defaults = ['north_york', 'scarborough', 'mississauga'] if annual else ['toronto', 'north_york', 'scarborough']
        chosen = []
        for i, col in enumerate([region_editor] * 3):
            with col:
                options = (['none'] if i else []) + [r for r in labels if r not in chosen]
                selected = st.selectbox(['主要地区', '对比地区 2', '对比地区 3'][i], options,
                    index=options.index(defaults[i]) if defaults[i] in options else 0,
                    format_func=lambda r: '不对比' if r == 'none' else labels[r], key=f'region-{annual}-{i}')
                if selected != 'none':
                    chosen.append(selected)
        region_names.html('<div class="region-names">' + ''.join(
            f'<div style="color:{series_color(cmhc_id(r, "rent", "total") if annual else asking_id(r, "total"))}">{escape(labels[r])}</div>'
            for r in chosen) + '</div>')
        measure = 'rent'
        if annual:
            annual_period_col = date_col
            with detail_col:
                measure = st.selectbox('年度地区指标', ['rent', 'vacancy'], format_func=lambda v: '平均租金' if v == 'rent' else '空置率', key='region-measure')
        with room_col:
            def room_label(value):
                count = sum(bool(latest(db, cmhc_id(r, measure, value) if annual else asking_id(r, value))) for r in chosen)
                suffix = ' · 暂无数据' if not count else ' · 部分可用' if count < len(chosen) else ''
                return rooms[value] + suffix
            room = st.selectbox('地区对比房型', list(rooms), index=list(rooms).index('total'), format_func=room_label, key=f'region-room-{annual}')
    with rail:
        st.caption('CMHC · 年度存量租金 · 每年 10 月调查' if annual else
                   'Rentals.ca / Urbanation · 月度挂牌 · 公寓与 condo')
    with plot:
        supported, fields = [], []
        for region in chosen:
            field = cmhc_id(region, measure, room) if annual else asking_id(region, room)
            if field not in SERIES or not latest(db, field):
                reason = unavailable_reason(db, region, room, annual, measure)
                st.info(f"{labels[region]} · {rooms[room]}：{reason}")
                if not annual and region in CMHC_REGIONS and room in RENTAL_BEDROOMS and latest(db, cmhc_id(region, 'rent', room)):
                    st.caption('可查看同地区、同房型的 CMHC 年度存量租金；它不是月度挂牌报价。')
                    st.button(f"查看 {labels[region]} · {rooms[room]}年度存量租金", key=f'annual-alternative-{region}',
                              on_click=select_annual_alternative, args=(region, room))
            else:
                supported.append(region)
                fields.append(field)
        if not annual and any(r in chosen for r in UNAVAILABLE):
            st.caption('Downtown 需先核定边界并取得对应数据；Richmond Hill、Aurora 尚无已核验的独立月度序列，可切换年度口径查看包含它们的组合调查区。')
    if fields:
        data = annual_data(db, fields) if annual else monthly_data
        # Preserve survey years even when one selected bedroom/year is suppressed.
        periods = sorted({r['period'] for r in db.execute("SELECT DISTINCT period FROM observations WHERE series_id LIKE 'regional_cmhc_%'")}) if annual else available_periods(data, fields)
        with filters:
            if annual:
                period_col = annual_period_col
            else:
                period_col, window_col = detail_col, date_col
            with period_col:
                end = st.selectbox('地区观察期', list(reversed(periods)), key=f'region-period-{annual}')
            if annual:
                start = periods[0]
            else:
                with window_col:
                    window = st.selectbox('地区趋势范围', ['近 12 个月', '近 24 个月', '全部历史'], key='region-window')
                count = {'近 12 个月': 12, '近 24 个月': 24}.get(window)
                year, month = map(int, end.split('-'))
                idx = year * 12 + month - (count or 1)
                start = max(periods[0], f'{idx // 12:04d}-{idx % 12 + 1:02d}') if count else periods[0]
        coverage = []
        names = dict(zip(fields, (labels[r] for r in supported)))
        for field in fields:
            p = available_periods(data, [field])
            coverage.append({'地区': names[field], '最早观测': p[0], '最新观测': p[-1], '观测数': len(p)})
        if not annual:
            idx = today.year * 12 + today.month - 2
            expected = f'{idx // 12:04d}-{idx % 12 + 1:02d}'
            if any(r['最新观测'] < expected for r in coverage):
                with rail:
                    st.warning(f'最近完整月为 {expected}；部分地区尚未更新，缺月不补值。')
        with plot:
            render_map(data, labels, chosen, room, measure, annual, end)
        with plot:
            st.subheader('地区租金走势' if measure == 'rent' else '地区空置率走势')
            line_chart(data, fields, start, end, height=340, names=names, points=True)
            if measure == 'rent' and len(fields) > 1:
                changes, common = comparable_change_rows(data, fields, names, start, end)
                if changes:
                    st.subheader('共同期间租金变化')
                    st.caption(f'{common[0]} — {common[1]} · 同来源、同房型、共同起止期 · 两点间变化，非同一套住房租金涨幅')
                    change_chart = alt.Chart(pd.DataFrame(changes)).mark_point(filled=True, size=150).encode(
                        x=alt.X('期间变化（%）:Q', title='期间变化（%）', axis=alt.Axis(format='+,.1f')),
                        y=alt.Y('地区:N', sort=[names[f] for f in fields], title=None),
                        color=alt.Color('地区:N', scale=alt.Scale(domain=[names[f] for f in fields], range=[series_color(f) for f in fields]), legend=None),
                        tooltip=['地区:N', '起期:N', '末期:N', alt.Tooltip('起期值:Q', format=',.0f'), alt.Tooltip('末期值:Q', format=',.0f'), alt.Tooltip('期间变化（%）:Q', format='+,.1f')],
                    ).properties(height=max(160, len(changes) * 55)).configure_view(stroke=None)
                    st.altair_chart(change_chart, use_container_width=True)
                else:
                    st.caption('所选地区在当前范围没有至少两个共同且有效的观察期，暂不比较涨跌幅。')
            for field, col in zip(fields, st.columns(len(fields))):
                with col:
                    metric = metric_at(data, field, end, unit=SERIES[field][4])
                    value = metric['value']
                    with st.container(key=f'metric-{field}'):
                        st.html(f'<style>.st-key-metric-{field} [data-testid="stMetricValue"] {{color:{series_color(field)}}}</style>')
                        st.metric(names[field], '—' if value is None else f'{value:.1f}%' if measure == 'vacancy' else f'${value:,.0f}')
                    if value is None:
                        st.caption('本期无可用观测，可能未发布或被抑制。')
            for field in fields:
                visible = [p for p in available_periods(data, [field]) if start <= p <= end]
                st.caption(f"{names[field]} · 所选期间实际观测：{len(visible)} 个")
                if 0 < len(visible) < 3:
                    st.warning(f"{names[field]}：当前仅有 {len(visible)} 个观测点；连线只表示已知点之间的变化，不足以判断长期趋势。")
        with st.expander('地区数据与来源'):
            st.dataframe(pd.DataFrame(coverage), hide_index=True, width='stretch')
            if not annual and any(len(available_periods(data, [f])) < 12 for f in fields):
                st.caption('部分序列不足 12 个月，尚不能据此判断全年季节性。')
            st.caption('同一房型与口径比较；曲线只连接连续观测，单点保留。短序列不是零租金。')
            export = pd.DataFrame(export_rows(db, fields, start, end, annual))
            st.dataframe(export, hide_index=True, width='stretch')
            st.download_button('下载地区对比数据', export.to_csv(index=False).encode('utf-8-sig'), f'regions-{start}-{end}.csv', 'text/csv')
            st.caption('导出仅包含所选地区、房型、指标和期间。空白保留缺失；CMHC 质量等级及被抑制单元格保留原表位置。')
    with st.expander('地区覆盖与边界说明'):
        st.caption('以下覆盖范围由当前数据库生成；各地区、房型的起止月份可能不同。')
        st.dataframe(pd.DataFrame(monthly_coverage(db)), hide_index=True, width='stretch')
        st.caption('地区总体统一采用 Top 25 公寓／condo 排名图；分房型采用城市表。2026-04 两图均值存在差异，已统一总体来源并保留旧版本，未把差异当作市场波动。')
        st.write('年度：CMHC 专建出租公寓为 2022—2025，可比较租金和空置率。Richmond Hill/Vaughan/King 与 Aurora/Newmarket/Whitchurch-Stouffville 是组合调查区，不提供其中单一城市的推算值。部分房型被来源抑制。')
        st.write('Downtown 尚未定义边界或接入；不能用 Toronto 总体替代。Oakview 暂按 Oakville 处理。地区筛选仅作用本视图，其他页面仍保留原有地区范围。')
        st.write('MLS 实际成交租金尚未接入；当前报价与年度存量租金不能当作实际签约租金。')
