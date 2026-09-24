def ratio(numerator, denominator, multiplier=1.0):
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator * multiplier

def resale_metrics(sales, new_listings, active_listings):
    return {
        "moi_raw": ratio(active_listings, sales),
        "snlr_raw": ratio(sales, new_listings, 100),
    }

def year_over_year(values, period):
    year, month = map(int, period.split("-"))
    previous = values.get(f"{year-1:04d}-{month:02d}")
    result = ratio(values.get(period), previous, 100)
    return None if result is None else result - 100
