"""Protocol v3 features: TRREB market balance from the 2004+ archive (see research_protocol_v3.json)."""
import csv
import math
from statistics import fmean

from .leading import shift

FEATURES = ['moi_yoy', 'moi_vs_norm', 'snlr_yoy', 'snlr_vs_norm', 'sp_lp_yoy', 'dom_yoy']
# Different formulas: never compare across families.
SP_LP_FAMILY = {'legacy': ('avg_pct_list', 'legacy'), 'summary_dom': ('avg_sp_lp', 'sp_lp'),
                'summary_no_trend': ('avg_sp_lp', 'sp_lp'), 'summary_ldom_pdom': ('avg_sp_lp', 'sp_lp'),
                'district_import_ldom_pdom': ('avg_sp_lp', 'sp_lp')}
DOM_FAMILY = {'legacy': ('avg_dom', 'dom'), 'summary_dom': ('avg_dom', 'dom'), 'summary_no_trend': ('avg_dom', 'dom'),
              'summary_ldom_pdom': ('avg_ldom', 'ldom'), 'district_import_ldom_pdom': ('avg_ldom', 'ldom')}


def load_trreb(path, data):
    """Add TRREB monthly fields to the v2 data dict under 'trreb' as {period: row}."""
    rows = {}
    with open(path, newline='') as handle:
        for row in csv.DictReader(handle):
            rows[row['period']] = {k: (float(v) if v not in ('', None) and k not in ('period', 'layout', 'source_pdf',
                                       'source_sha256', 'grand_total_differs') else v) for k, v in row.items()}
    data['trreb'] = rows
    return data


def _sum(rows, field, end):
    values = [rows.get(shift(end, -k), {}).get(field) for k in range(3)]
    return None if any(v in (None, '') for v in values) else sum(values)


def moi3(rows, m):
    active, sales = _sum(rows, 'active_listings', m), _sum(rows, 'sales', m)
    return active / sales if active and sales else None


def snlr3(rows, m):
    sales, new = _sum(rows, 'sales', m), _sum(rows, 'new_listings', m)
    return 100 * sales / new if sales and new else None


def _norm(quantity, rows, m):
    """Mean of the same calendar month in all earlier years (at least three)."""
    past = [quantity(rows, f'{year:04d}{m[4:]}') for year in range(2004, int(m[:4]))]
    past = [v for v in past if v is not None]
    return fmean(past) if len(past) >= 3 else None


def _family_change(rows, families, a, b, log=False):
    ra, rb = rows.get(a), rows.get(b)
    if not ra or not rb:
        return None
    (field_a, family_a), (field_b, family_b) = families[ra['layout']], families[rb['layout']]
    va, vb = ra.get(field_a), rb.get(field_b)
    if family_a != family_b or va in (None, '') or vb in (None, ''):
        return None
    if log:
        return 100 * math.log(va / vb) if va > 0 and vb > 0 else None
    return va - vb


def feature(data, name, T):
    rows, m = data['trreb'], shift(T, -1)
    if name == 'moi_yoy':
        now, before = moi3(rows, m), moi3(rows, shift(m, -12))
        return 100 * math.log(now / before) if now and before else None
    if name == 'moi_vs_norm':
        now = moi3(rows, m)
        norm = _norm(lambda r, p: math.log(moi3(r, p)) if moi3(r, p) else None, rows, m)
        return math.log(now) - norm if now and norm is not None else None
    if name == 'snlr_yoy':
        now, before = snlr3(rows, m), snlr3(rows, shift(m, -12))
        return now - before if now is not None and before is not None else None
    if name == 'snlr_vs_norm':
        now, norm = snlr3(rows, m), _norm(snlr3, rows, m)
        return now - norm if now is not None and norm is not None else None
    if name == 'sp_lp_yoy':
        return _family_change(rows, SP_LP_FAMILY, m, shift(m, -12))
    if name == 'dom_yoy':
        return _family_change(rows, DOM_FAMILY, m, shift(m, -12), log=True)
    raise KeyError(name)
