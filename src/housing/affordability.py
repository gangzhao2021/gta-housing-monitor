"""Transparent Canadian mortgage payment scenarios (not an affordability score)."""
from .presentation import calendar_periods

def monthly_payment(principal: float, nominal_annual_rate_pct: float, amortization_years: int) -> float:
    """Monthly principal-and-interest payment for a nominal rate compounded semi-annually."""
    if principal < 0:
        raise ValueError("principal must be non-negative")
    if nominal_annual_rate_pct < 0:
        raise ValueError("annual rate must be non-negative")
    if amortization_years <= 0:
        raise ValueError("amortization must be positive")
    if principal == 0:
        return 0.0
    # Canadian fixed mortgage rates are commonly quoted nominally, compounded
    # semi-annually; convert that quote to an equivalent monthly rate.
    monthly_rate = (1 + nominal_annual_rate_pct / 200) ** (1 / 6) - 1
    months = amortization_years * 12
    if monthly_rate == 0:
        return principal / months
    return principal * monthly_rate / (1 - (1 + monthly_rate) ** -months)


def historical_payment_rows(observations, principal, amortization_years, months=36):
    """Hold loan assumptions fixed and expose missing rate months as chart gaps."""
    if not observations:
        return []
    rates = {row['period']: row['value'] for row in observations}
    end = max(rates)
    year, month = map(int, end.split('-'))
    first = year * 12 + month - months
    start = f'{first // 12:04d}-{first % 12 + 1:02d}'
    start = max(min(rates), start)
    segment = 0
    result = []
    for period in calendar_periods(start, end):
        rate = rates.get(period)
        if rate is None:
            segment += 1
        result.append({'所属月份': period, '日期': period + '-01',
                       '按揭利率（%）': rate,
                       '估算月供（加元）': monthly_payment(principal, rate, amortization_years) if rate is not None else None,
                       'segment': segment})
    return result
