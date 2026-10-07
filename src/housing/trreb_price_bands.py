"""Monthly TRREB sales by sold-price band, from page 2 of each Market Watch report.

Fifteen published buckets are summed into six fixed bands for all home types.
The month's buckets must add up to the stored All TRREB Areas sales total.
"""
import re

BUCKETS = ['$0 to $99,999', '$100,000 to $199,999', '$200,000 to $299,999', '$300,000 to $399,999',
           '$400,000 to $499,999', '$500,000 to $599,999', '$600,000 to $699,999', '$700,000 to $799,999',
           '$800,000 to $899,999', '$900,000 to $999,999', '$1,000,000 to $1,249,999',
           '$1,250,000 to $1,499,999', '$1,500,000 to $1,749,999', '$1,750,000 to $1,999,999', '$2,000,000+']
BANDS = {  # series id -> (label, bucket indexes)
    'trreb_sales_band_under_500k': ('成交价 50 万以下', range(0, 5)),
    'trreb_sales_band_500k_800k': ('成交价 50–80 万', range(5, 8)),
    'trreb_sales_band_800k_1m': ('成交价 80–100 万', range(8, 10)),
    'trreb_sales_band_1m_1_5m': ('成交价 100–150 万', range(10, 12)),
    'trreb_sales_band_1_5m_2m': ('成交价 150–200 万', range(12, 14)),
    'trreb_sales_band_2m_plus': ('成交价 200 万及以上', range(14, 15)),
}
DEFINITION = 'TRREB 月报第 2 页全部房型当月成交套数，按成交价分段合计；各段之和等于当月总成交。成交构成，不是房价指数'
NUMBER = re.compile(r'[\d,]+')


def monthly_buckets(pdf):
    """Return the first (monthly) block of 15 bucket totals from page 2."""
    import pymupdf
    with pymupdf.open(pdf) as document:
        page = document[1]
        words = [w for w in page.get_text('words') if w[4] != 'Abc']
    headers = [w for w in words if w[4] == 'Total']
    if not headers:
        raise ValueError('Price-range table has no Total column')
    total_x = (headers[0][0] + headers[0][2]) / 2
    starts = sorted((w for w in words if w[4].startswith('$') and w[0] < 150), key=lambda w: (w[1], w[0]))
    rows, used = [], set()
    for start in starts:
        line = sorted((w for w in words if abs(w[1] - start[1]) < 3), key=lambda w: w[0])
        key = round(start[1], 1)
        if key in used:
            continue
        used.add(key)
        text = ' '.join(w[4] for w in line)
        label = next((b for b in BUCKETS if text.startswith(b + ' ') or text == b), None)
        if label is None:
            continue
        # Blank cells occur (e.g. no co-ownership sales); only the Total column is read.
        total = [w[4] for w in line[len(label.split()):] if NUMBER.fullmatch(w[4])
                 and abs((w[0] + w[2]) / 2 - total_x) < 40]
        if len(total) != 1:
            raise ValueError(f'Price row {label} has no single Total value')
        rows.append((label, int(total[0].replace(',', ''))))
    if [label for label, _ in rows[:15]] != BUCKETS:
        raise ValueError('Price-range buckets changed or are out of order')
    return [count for _, count in rows[:15]]


def rows_for(pdf, period, sales):
    buckets = monthly_buckets(pdf)
    if sum(buckets) != sales:
        raise ValueError(f'Price bands sum to {sum(buckets)}, not stored sales {sales}')
    return [(series_id, period, float(sum(buckets[i] for i in indexes))) for series_id, (_, indexes) in BANDS.items()]
