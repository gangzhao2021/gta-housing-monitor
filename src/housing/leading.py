"""Protocol v2 leading-indicator study (see research_protocol_v2.json).

Every forecast made at decision month T uses only feature values whose
protocol lag places them at or before T, and is trained only on decisions
whose target index month (T'-2+h) is at or before T-2. Nothing is imputed.
"""
import csv
import math
from collections import defaultdict
from statistics import NormalDist, fmean

FEATURES = ['teranet_momentum', 'teranet_pairs_yoy', 'mortgage_rate_change', 'bond_5y_change',
            'ontario_unemployment_change', 'starts_growth', 'new_home_price_growth', 'policy_uncertainty']


def shift(period, months):
    index = int(period[:4]) * 12 + int(period[5:]) - 1 + months
    return f'{index // 12:04d}-{index % 12 + 1:02d}'


def months(first, last):
    out, period = [], first
    while period <= last:
        out.append(period)
        period = shift(period, 1)
    return out


def load(path):
    data = defaultdict(dict)
    with open(path, newline='') as handle:
        for row in csv.DictReader(handle):
            data[row['series']][row['period']] = float(row['value'])
    return data


def _mean(series, periods):
    values = [series.get(p) for p in periods]
    return None if any(v is None for v in values) else fmean(values)


def _log_ratio(a, b):
    return None if a is None or b is None or a <= 0 or b <= 0 else 100 * math.log(a / b)


def _diff(a, b):
    return None if a is None or b is None else a - b


def feature(data, name, T):
    s = lambda k, offset: data[k].get(shift(T, offset))
    if name == 'teranet_momentum':
        return _log_ratio(s('teranet_index_sa', -2), s('teranet_index_sa', -8))
    if name == 'teranet_pairs_yoy':
        pairs = data['teranet_pairs']
        return _log_ratio(_mean(pairs, [shift(T, k) for k in (-4, -3, -2)]),
                          _mean(pairs, [shift(T, k) for k in (-16, -15, -14)]))
    if name == 'mortgage_rate_change':
        return _diff(s('mortgage_5y', 0), s('mortgage_5y', -12))
    if name == 'bond_5y_change':
        return _diff(s('bond_5y', 0), s('bond_5y', -12))
    if name == 'ontario_unemployment_change':
        return _diff(s('ontario_unemployment', -1), s('ontario_unemployment', -13))
    if name == 'starts_growth':
        starts = data['starts']
        now = [starts.get(shift(T, -k)) for k in range(1, 13)]
        before = [starts.get(shift(T, -k)) for k in range(13, 25)]
        if None in now or None in before:
            return None
        return _log_ratio(sum(now), sum(before))
    if name == 'new_home_price_growth':
        return _log_ratio(s('toronto_nhpi', -2), s('toronto_nhpi', -14))
    if name == 'policy_uncertainty':
        value = _mean(data['canada_epu'], [shift(T, k) for k in (-3, -2, -1)])
        return None if value is None or value <= 0 else math.log(value)
    raise KeyError(name)


def target(data, T, h):
    index = data['teranet_index_sa']
    return _log_ratio(index.get(shift(T, -2 + h)), index.get(shift(T, -2)))


def ols(xs, ys):
    mx, my = fmean(xs), fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return my, 0.0
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return my - b * mx, b


def forecasts(data, h, decisions, minimum=60):
    """Return {decision: {'actual', 'benchmark', model: forecast}} with no look-ahead."""
    all_months = sorted({p for d in decisions for p in [d]})
    table = {T: {f: feature(data, f, T) for f in FEATURES} for T in months(shift(all_months[0], -400), all_months[-1])}
    labels = {T: target(data, T, h) for T in table}
    result = {}
    for T in decisions:
        matured = [d for d in table if d <= shift(T, -h) and labels[d] is not None]
        if len(matured) < minimum:
            continue
        row = {'actual': labels.get(T), 'benchmark': fmean(labels[d] for d in matured)}
        for f in FEATURES:
            x_now = table[T][f]
            train = [(table[d][f], labels[d]) for d in matured if table[d][f] is not None]
            if x_now is None or len(train) < minimum:
                continue
            a, b = ols([x for x, _ in train], [y for _, y in train])
            row[f] = a + b * x_now
        univariate = [row[f] for f in FEATURES if f in row]
        if univariate:
            row['combination'] = fmean(univariate)
        result[T] = row
    return result


def newey_west_t(values, lags):
    n = len(values)
    mean = fmean(values)
    e = [v - mean for v in values]
    variance = sum(x * x for x in e) / n
    for lag in range(1, lags + 1):
        weight = 1 - lag / (lags + 1)
        variance += 2 * weight * sum(e[i] * e[i - lag] for i in range(lag, n)) / n
    return mean / math.sqrt(variance / n) if variance > 0 else float('nan')


def evaluate(rows, model, h, start, end):
    cases = [r for T, r in sorted(rows.items()) if start <= T <= end and r['actual'] is not None and model in r]
    if len(cases) < 24:
        return {'n': len(cases), 'status': 'too_few_cases'}
    sse_m = sum((r['actual'] - r[model]) ** 2 for r in cases)
    sse_b = sum((r['actual'] - r['benchmark']) ** 2 for r in cases)
    cw = [(r['actual'] - r['benchmark']) ** 2 - ((r['actual'] - r[model]) ** 2 - (r['benchmark'] - r[model]) ** 2)
          for r in cases]
    t = newey_west_t(cw, h - 1)
    return {
        'n': len(cases),
        'oos_r2': 1 - sse_m / sse_b,
        'rmse': math.sqrt(sse_m / len(cases)),
        'rmse_benchmark': math.sqrt(sse_b / len(cases)),
        'direction_hit': fmean((r[model] > 0) == (r['actual'] > 0) for r in cases),
        'direction_hit_benchmark': fmean((r['benchmark'] > 0) == (r['actual'] > 0) for r in cases),
        'clark_west_t': t,
        'clark_west_p_one_sided': 1 - NormalDist().cdf(t) if math.isfinite(t) else None,
    }
