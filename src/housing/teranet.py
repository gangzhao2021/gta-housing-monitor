"""Teranet-National Bank House Price Index, Toronto (repeat sales from land registry).

Downloaded manually from housepriceindex.ca after accepting its Terms of Use
(non-commercial, personal use; reproduce accurately and credit the source).
Repeat-sales history is revised as new pairs arrive, so each import is a new
vintage handled by the normal versioned ingest. Not combined with TRREB HPI.
"""
import csv
import io
from datetime import datetime

SOURCE = 'Teranet-National Bank HPI'
URL = 'https://housepriceindex.ca/index-history/'
GEO = 'Toronto (Teranet-National Bank market)'
NOTE = '土地登记处同一住房两次成交配对的重复交易指数，2005-06=100；新配对会修订历史；不同于 TRREB MLS HPI，两者不合并'
COLUMNS = ['Index', 'SA Index', 'Smoothed Index', 'Smoothed SA Index', 'Sales Pair Count']
SERIES = {  # series id -> (label, unit, column)
    'teranet_toronto_index': ('Teranet–National Bank 房价指数：Toronto', 'index, 2005-06=100', 'Index'),
    'teranet_toronto_index_sa': ('Teranet–National Bank 房价指数：Toronto（季调）', 'index, 2005-06=100', 'SA Index'),
    'teranet_toronto_sales_pairs': ('Teranet Toronto 重复交易配对数', 'sales pairs', 'Sales Pair Count'),
}


def parse(content):
    rows = list(csv.reader(io.StringIO(content.decode('utf-8-sig'))))
    top, sub = rows[0], rows[1]
    if top[0] != 'Transaction Date' or 'on_toronto' not in top:
        raise ValueError('Teranet file layout changed: Toronto column group missing')
    start = top.index('on_toronto')
    if sub[start:start + 5] != COLUMNS:
        raise ValueError('Teranet Toronto measures changed')
    result, base = [], None
    for row in rows[2:]:
        if not row or not row[0]:
            continue
        period = datetime.strptime(row[0], '%b-%Y').strftime('%Y-%m')
        cells = dict(zip(COLUMNS, row[start:start + 5]))
        if period == '2005-06':
            base = cells['Index']
        for series_id, (_, _, column) in SERIES.items():
            if cells[column]:
                result.append((series_id, period, float(cells[column])))
    if base is None or abs(float(base) - 100) > 0.005:
        raise ValueError('Teranet Toronto index is no longer based at 2005-06=100')
    periods = sorted({p for s, p, _ in result if s == 'teranet_toronto_index'})
    expected = (int(periods[-1][:4]) - int(periods[0][:4])) * 12 + int(periods[-1][5:]) - int(periods[0][5:]) + 1
    if len(periods) != expected:
        raise ValueError('Teranet Toronto index has internal gaps')
    return result
