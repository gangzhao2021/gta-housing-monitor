"""TRREB's own published year-over-year changes, read from each report's front page.

TRREB compares each month with a revised prior-year figure, so its published
change differs from one computed between two original releases. Both are kept:
these series store what TRREB printed, checked against the printed values.
"""
import re
import unicodedata
from datetime import datetime

LABELS = {
    'Sales': ('trreb_sales_yoy_published', 'trreb_sales'),
    'New Listings': ('trreb_new_listings_yoy_published', 'trreb_new_listings'),
    'Active Listings': ('trreb_active_listings_yoy_published', 'trreb_active_listings'),
    'Average Price': ('trreb_average_price_yoy_published', None),
}
HPI_SERIES = 'trreb_hpi_benchmark_yoy_published'
SERIES = {
    'trreb_sales_yoy_published': 'TRREB 公布成交同比',
    'trreb_new_listings_yoy_published': 'TRREB 公布新增挂牌同比',
    'trreb_active_listings_yoy_published': 'TRREB 公布在售挂牌同比',
    'trreb_average_price_yoy_published': 'TRREB 公布成交均价同比',
    HPI_SERIES: 'TRREB 公布 HPI 基准价同比',
}
DEFINITION = 'TRREB 月报首页公布的同比（%），以修订后的上年同月为分母；与两期原发布值自算的同比不同'
NUMBER = re.compile(r'\$?[\d,]+')
PERCENT = re.compile(r'-?\d+(?:\.\d+)?%')


def _amount(text):
    return int(text.replace('$', '').replace(',', ''))


def _pct(text):
    return float(text.rstrip('%'))


def _consistent(current, prior, printed):
    return prior > 0 and abs((current / prior - 1) * 100 - printed) <= 0.051


def _dashboard_front(page, year):
    blocks = [[line.strip() for line in unicodedata.normalize('NFKC', b[4]).splitlines() if line.strip()]
              for b in page.get_text('blocks')]
    if ['Metrics', str(year), str(year - 1)] not in blocks:
        return None
    values, printed = {}, {}
    for lines in blocks:
        if len(lines) == 3 and lines[0] in LABELS and all(NUMBER.fullmatch(v) for v in lines[1:]):
            values[lines[0]] = (_amount(lines[1]), _amount(lines[2]))
        if len(lines) == 2 and lines[0] in LABELS and PERCENT.fullmatch(lines[1]):
            printed[lines[0]] = _pct(lines[1])
    return {label: (*values[label], printed[label]) for label in LABELS if label in values and label in printed}


def _legacy_front(page, year):
    """Older layout: spans on the label's row; template placeholders share the row."""
    labels = [b for b in page.get_text('blocks') if b[4].strip() in LABELS]
    spans = [span for block in page.get_text('dict')['blocks'] for line in block.get('lines', [])
             for span in line['spans']]
    header = next((b for b in page.get_text('blocks') if b[4].strip() == f'{year}\n{year - 1}'), None)
    if header is None:
        return {}
    columns = {}
    for word in page.get_text('words'):
        if word[4] in (str(year), str(year - 1)) and abs(word[1] - header[1]) < 2:
            columns[word[4]] = (word[0] + word[2]) / 2
    if len(columns) != 2:
        return {}
    result = {}
    for block in labels:
        label = block[4].strip()
        row = [s for s in spans if abs(s['bbox'][1] - block[1]) < 4 and s['bbox'][0] > block[2]]
        near = lambda key: [_amount(s['text']) for s in row if NUMBER.fullmatch(s['text'].strip())
                            and abs((s['bbox'][0] + s['bbox'][2]) / 2 - columns[key]) < 20]
        result[label] = (near(str(year)), near(str(year - 1)),
                         [_pct(s['text'].strip()) for s in row if PERCENT.fullmatch(s['text'].strip())])
    return result


def front_comparison(pdf, period, stored):
    """Return {label: (current, revised prior, printed %)} that pass all checks.

    stored maps base series ids to this month's stored values; the current value
    must equal it, and the printed % must follow from the two printed amounts.
    """
    import pymupdf
    year = int(period[:4])
    with pymupdf.open(pdf) as document:
        page = document[0]
        if f'{datetime.strptime(period, "%Y-%m"):%B}' not in page.get_text():
            raise ValueError('Front page does not name the report month')
        dashboard = _dashboard_front(page, year)
        legacy = None if dashboard is not None else _legacy_front(page, year)
    accepted = {}
    for label, (_, base) in LABELS.items():
        if dashboard is not None:
            if label not in dashboard:
                continue
            current, prior, printed = dashboard[label]
            if not _consistent(current, prior, printed):
                continue
        else:
            if label not in legacy:
                continue
            currents, priors, printed_values = legacy[label]
            if base:
                currents = [c for c in currents if c == stored.get(base)]
            if len(currents) != 1:
                continue
            fits = {(p, pct) for p in priors for pct in printed_values if _consistent(currents[0], p, pct)}
            if len({p for p, _ in fits}) != 1:
                continue  # ambiguous or no consistent prior-year value: leave missing
            (prior, printed), = sorted(fits)[:1]
            current = currents[0]
        if base and stored.get(base) != current:
            continue
        accepted[label] = (current, prior, printed)
    return accepted


def rows_for(pdf, period, stored, hpi_rows=None):
    rows = [(LABELS[label][0], period, printed) for label, (_, _, printed) in front_comparison(pdf, period, stored).items()]
    for row in hpi_rows or []:
        if row['type_id'] == 'composite' and row['metric'] == 'source_yoy':
            rows.append((HPI_SERIES, period, row['value']))
    return rows
