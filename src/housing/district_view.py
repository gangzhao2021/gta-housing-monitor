"""Shared owner/viewer exploration of published TRREB district aggregates."""
from .i18n import st, english
PROPERTY_TYPES = {'all_types': ['全部房型', 'All property types'], 'detached': ['独立屋', 'Detached'], 'semi_detached': ['半独立屋', 'Semi-detached'], 'townhouse': ['镇屋', 'Townhouse'], 'condo_townhouse': ['公寓镇屋', 'Condo townhouse'], 'condo_apartment': ['公寓', 'Condo apartment'], 'link': ['连接屋', 'Link'], 'coop_apartment': ['合作公寓', 'Co-op apartment'], 'detached_condo': ['独立式公寓', 'Detached condo'], 'coownership_apartment': ['共同产权公寓', 'Co-ownership apartment']}


def render(rows):
    import pandas as pd
    import altair as alt
    title = 'District resale' if english() else '地区转售明细'
    with st.expander(title):
        if not rows:
            st.info('No published district data.' if english() else '尚无已发布地区明细。')
            return
        df = pd.DataFrame(rows)
        types = sorted(df.house_type.unique())
        kind = st.selectbox('Property type' if english() else '转售房型', types, format_func=lambda v: PROPERTY_TYPES[v][1 if english() else 0], key='district-type')
        df = df[df.house_type == kind]
        options = sorted(df.region.unique())
        defaults = [r for r in ['City of Toronto', 'Markham'] if r in options]
        areas = st.multiselect('Compare up to three areas' if english() else '比较地区（最多三个）', options,
                               default=defaults, max_selections=3, key='district-regions')
        field = st.selectbox('Measure' if english() else '转售指标',
                             ['average_price', 'sales', 'new_listings', 'active_listings', 'median_price', 'avg_ldom', 'avg_pdom', 'avg_sp_lp'],
                             format_func=lambda v: {'average_price': ('均价','Average price'), 'sales': ('成交','Sales'), 'new_listings': ('新增挂牌','New listings'), 'active_listings': ('在售挂牌','Active listings'), 'median_price': ('中位价','Median price'), 'avg_ldom': ('挂牌天数','Listing days'), 'avg_pdom': ('物业在市天数','Property days on market'), 'avg_sp_lp': ('成交价／挂牌价 %','Sale-to-list price %')}[v][1 if english() else 0], key='district-field')
        end = st.selectbox('Month' if english() else '转售观察月', sorted(df.ym.unique(), reverse=True), key='district-month')
        data = df[(df.region.isin(areas)) & (df.ym <= end)].copy()
        months = sorted(data.ym.unique())[-36:]
        data = data[data.ym.isin(months)]
        st.caption('TRREB report areas are not interchangeable with rental-market areas. Average prices reflect the sales mix; not HPI. Overlapping areas are not summed.' if english() else
                   'TRREB 报告地区不能与租赁市场地区互换。均价受成交构成影响，不是 HPI；父子地区有重叠，不相加。')
        if data.empty:
            st.info('No observations.' if english() else '该选择暂无观测。')
            return
        chart = alt.Chart(data).mark_line().encode(x=alt.X('ym:O', title=None),
            y=alt.Y(field+':Q', title='CAD' if 'price' in field else ('%' if field=='avg_sp_lp' else 'Days' if field in ('avg_ldom', 'avg_pdom') else 'Count'), scale=alt.Scale(zero=False)),
            color=alt.Color('region:N', title=None), tooltip=['ym:N','region:N',alt.Tooltip(field+':Q',format=',.0f')]).properties(height=280)
        st.altair_chart(chart, use_container_width=True)
        st.table(data[data.ym == end][['region',field]].set_index('region'))
