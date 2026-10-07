"""Board-wide TRREB monthly totals from archived Market Watch PDFs, 2004 onward.

Research dataset only; dashboard series keep their own 2022-09 start.

Layouts:
  legacy (2004 .. late 2011): last page "District Totals", row "Grand Total":
      New, Active, Listed (N/A), Sales, $ Volume, Avg Price, Med Price, Avg DOM, Avg % List
  summary (late 2011 .. 2026-08): "SUMMARY OF EXISTING HOME TRANSACTIONS" total row
      ("TREB Total" / "TRREB Total" / "All TRREB Areas"): Sales, $ Volume, Avg, Median,
      New, SNLR (Trend), Active, Mos Inv (Trend), Avg SP/LP, Avg DOM [or LDOM, PDOM]
  dashboard (2026-09 ..): read from the validated district import instead.

Definitions differ across layouts for SP/LP (average of ratios vs ratio of
averages) and DOM (single DOM vs LDOM/PDOM); those fields carry the layout so
they are never spliced. Coverage of "all areas" also grew over time, so levels
of counts are not comparable across years; ratios (MOI, SNLR) are less affected.
"""
import re
from pathlib import Path

NUMBER = re.compile(r'^\$?-?[\d,]+(?:\.\d+)?%?$')
TOTAL_LABELS = ('TREB Total', 'TRREB Total', 'All TRREB Areas')
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
          'September', 'October', 'November', 'December']


def _num(token):
    return float(token.replace('$', '').replace(',', '').replace('%', ''))


GROUPED = re.compile(r'N/A|\$?\d{1,3}(?:,\d{3})+(?:\.\d+)?|\$?\d+(?:\.\d+)?')


def _grouped_numbers(text):
    """Numbers from text; digits printed spaced apart ('1 2 , 5 1 6 1 3 , 11 6') are rejoined
    using thousands grouping. Normal text is split on whitespace."""
    parts = text.split()
    if parts and sum(len(t) for t in parts) / len(parts) < 2.5:
        return GROUPED.findall(re.sub(r'\s+', '', text))
    return [t for t in parts if GROUPED.fullmatch(t)]


def _rows(page, tolerance=3):
    seen, words = set(), []
    for w in page.get_text('words'):
        key = (round(w[0]), round(w[1]), w[4])
        if w[4] != 'Abc' and key not in seen:  # duplicate text layers sit at identical positions
            seen.add(key)
            words.append(w)
    rows = {}
    for w in words:
        rows.setdefault(round(w[1] / tolerance), []).append(w)
    return [' '.join(w[4] for w in sorted(r, key=lambda w: w[0])) for _, r in sorted(rows.items())]


def _check_volume(record):
    if record['sales'] <= 0 or abs(record['dollar_volume'] / record['sales'] - record['average_price']) > 1.01:
        raise ValueError(f'dollar volume / sales does not match average price: {record}')
    return record


def front_summary(document):
    """Legacy front page: 'Sales a b (x%) New Listings a b (y%) Active Listings* a b (z%)'; b is current."""
    flat = ' '.join(document[0].get_text().split())
    found = {}
    for key, label in (('sales', r'Sales'), ('new_listings', r'New Listings\*?'), ('active_listings', r'Active Listings\*{0,2}')):
        # previous year, current year, then '(+x%)' or a dash when the change is not printed
        match = re.search(label + r'\s+((?:[\d,]\s?)+?)\s*(?:\(|–|-\s|N/A)', flat)
        if match:
            numbers = _grouped_numbers(match.group(1))
            if len(numbers) == 2:
                found[key] = _num(numbers[1])
    return found


def legacy(document):
    """Grand Total row, confirmed by the front-page summary (columns are sometimes misprinted)."""
    page = document[len(document) - 1]
    front = front_summary(document)
    if set(front) != {'sales', 'new_listings', 'active_listings'}:
        return None
    for row in _rows(page, 4):
        compact = re.sub(r'\s+', '', row)
        if not compact.startswith(('GrandTotal', 'GrandTotal:')):
            continue
        body = re.sub(r'^G\s*r\s*a\s*n\s*d\s*T\s*o\s*t\s*a\s*l\s*:?', '', row)
        tokens = _grouped_numbers(body)
        values = [None if t == 'N/A' else _num(t) for t in tokens]
        big = next((i for i, v in enumerate(values) if v is not None and v >= 1_000_000), None)
        if big is None or len(values) < big + 3:
            raise ValueError(f'Unexpected Grand Total row: {row}')
        volume, average, median = values[big:big + 3]
        counts = [v for v in values[:big] if v is not None]
        if abs(volume / front['sales'] - average) > 1.01:
            raise ValueError('Grand Total volume / front-page sales does not match average price')
        # The front page and the Grand Total row are occasionally from different snapshots of the
        # same report; the headline value is kept and a difference above 1% is rejected.
        differences = {}
        for key in ('new_listings', 'active_listings'):
            nearest = min(counts, key=lambda c: abs(c - front[key]), default=None)
            if nearest is None or abs(nearest - front[key]) > 0.01 * front[key]:
                differences[key] = nearest
                front[key] = None  # conflicting printed values: leave this field missing
            elif nearest != front[key]:
                differences[key] = nearest
        tail = values[big + 3:big + 5]
        dom, pct = (tail[0], tail[1]) if len(tail) == 2 and None not in tail else (None, None)
        return {'layout': 'legacy', 'new_listings': front['new_listings'], 'active_listings': front['active_listings'],
                'sales': front['sales'], 'dollar_volume': volume, 'average_price': average, 'median_price': median,
                'avg_dom': dom, 'avg_pct_list': pct,
                'grand_total_differs': differences or None}
    return None


def summary(document, period):
    month = MONTHS[int(period[5:]) - 1]
    for page in document:
        rows = _rows(page)
        flat = ' '.join(rows)
        if 'Active' not in flat or not re.search(r'SP\s*/\s*LP', flat) or 'YEAR-TO-DATE' in flat.upper():
            continue
        if f'{month} {period[:4]}' not in flat and f'{month.upper()} {period[:4]}' not in flat:
            continue
        for row in rows:
            row = re.sub(r'^All All TRREB TRREB Areas Areas', 'All TRREB Areas', row)  # doubled text layer
            label = next((l for l in TOTAL_LABELS if row.startswith(l + ' ')), None)
            if not label:
                continue
            tokens = [t for t in row[len(label):].split() if NUMBER.match(t)]
            if len(tokens) % 2 == 0 and tokens[0::2] == tokens[1::2]:
                tokens = tokens[0::2]
            if len(tokens) not in (8, 10, 11):
                # Two overlapping text layers at different scales (seen in 2022-05): keep the
                # first occurrence of each value; the volume check below still has to pass.
                tokens = list(dict.fromkeys(tokens))
            if len(tokens) == 8:  # mid-2011 layout without SNLR / months of inventory
                v = [_num(t) for t in tokens]
                return _check_volume({'layout': 'summary_no_trend', 'sales': v[0], 'dollar_volume': v[1],
                                      'average_price': v[2], 'median_price': v[3], 'new_listings': v[4],
                                      'active_listings': v[5], 'avg_sp_lp': v[6], 'avg_dom': v[7]})
            if len(tokens) not in (10, 11):
                raise ValueError(f'Unexpected total row on the first summary page: {row}')
            v = [_num(t) for t in tokens]
            record = {'layout': 'summary_ldom_pdom' if len(v) == 11 else 'summary_dom', 'sales': v[0],
                      'dollar_volume': v[1], 'average_price': v[2], 'median_price': v[3], 'new_listings': v[4],
                      'snlr_trend': v[5], 'active_listings': v[6], 'moi_trend': v[7], 'avg_sp_lp': v[8]}
            if len(v) == 11:
                record.update(avg_ldom=v[9], avg_pdom=v[10])
            else:
                record['avg_dom'] = v[9]
            return _check_volume(record)
        raise ValueError('First monthly summary page has no total row')
    return None


def extract(path, period):
    import pymupdf
    with pymupdf.open(path) as document:
        record = summary(document, period)
        if record is None:
            record = legacy(document)
    if record is None:
        raise ValueError('No board-wide monthly total found')
    if not (record['active_listings'] or record['new_listings']):
        raise ValueError('Missing listings')
    return {'period': period, 'source_pdf': Path(path).name, **record}
