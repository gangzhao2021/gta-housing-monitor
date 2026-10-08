"""Shared owner/viewer page layout pieces matching the published site: the sticky in-page
section nav and the price panel that switches between the recent HPI and the long-run index."""
from .i18n import english, st

SECTIONS = (("sec-price", ("价格", "Prices")), ("sec-temp", ("温度", "Temperature")), ("sec-supply", ("供需", "Supply")),
            ("sec-mix", ("价格段", "Price bands")), ("sec-areas", ("地区", "Areas")))


def anchor(section_id):
    st.html(f'<div id="{section_id}" class="section-anchor"></div>')


def section_nav(sections=SECTIONS):
    """Links to the page's sections, pinned under the top of the page while scrolling."""
    import streamlit as native_st
    i = 1 if english() else 0
    links = "".join(f'<a href="#{sid}">{labels[i]}</a>' for sid, labels in sections)
    with native_st.container(key="section-nav"):
        st.html(f'<nav class="section-jump" aria-label="{"On this page" if i else "本页内容"}">{links}</nav>')


def price_panel(data, start, end, line_chart, available_periods, key, height=330):
    """The 2-year HPI chart, or the Teranet index since 1998, behind one switch."""
    import streamlit as native_st
    en = english()
    teranet = available_periods(data, ["teranet_toronto_index_sa"])
    anchor("sec-price")
    heading, control = native_st.columns([2, 1], vertical_alignment="center")
    with heading:
        st.subheader("房价走势")
    view = "recent"
    if teranet:
        with control:
            view = native_st.radio("Span" if en else "时间跨度", ["recent", "long"], horizontal=True, label_visibility="collapsed", key=key,
                                   format_func=lambda v: ("2 years · HPI" if en else "近 2 年 · HPI") if v == "recent" else ("Since 1998 · Teranet" if en else "1998 年起 · Teranet"))
    if view == "long":
        line_chart(data, ["teranet_toronto_index_sa"], teranet[0], teranet[-1], height=height)
        native_st.caption("Teranet–National Bank Toronto repeat-sales index (seasonally adjusted, June 2005 = 100), dated at registration, "
                          "1–3 months after the MLS sale; a different measure from the 2-year HPI view." if en else
                          "Teranet–National Bank 多伦多重复交易指数（季调，2005 年 6 月 = 100）：按产权登记日期，比 MLS 签约晚 1–3 个月；与「近 2 年 · HPI」视图口径不同。")
    else:
        line_chart(data, ["trreb_hpi_benchmark"], start, end, height=height)
        native_st.caption("The benchmark is the price of a standardized home, not the average sale price." if en else
                          "基准价格是标准化住宅的价格，不是成交均价。")
