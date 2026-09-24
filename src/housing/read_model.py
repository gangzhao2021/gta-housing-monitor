from collections import defaultdict
from statistics import mean

from .db import latest
from .catalog import SERIES
from .metrics import resale_metrics, year_over_year

def monthly(db):
    result = defaultdict(dict)
    for series_id in (
        "boc_policy_rate", "goc_5y_yield", "mortgage_uninsured_fixed_5plus",
        "toronto_unemployment_rate", "toronto_employment_rate", "toronto_participation_rate",
        "trreb_sales", "trreb_new_listings", "trreb_active_listings",
        "trreb_hpi_composite", "trreb_hpi_benchmark",
        "toronto_cma_2011_starts", "toronto_cma_2011_completions",
        "toronto_cma_2011_under_construction",
        "toronto_asking_rent_total", "toronto_asking_rent_1br",
        "toronto_asking_rent_2br", "toronto_asking_rent_3br",
    ) + tuple(s for s in SERIES if s.startswith("regional_asking_")):
        rows = latest(db, series_id)
        if series_id == "boc_policy_rate":
            for row in rows:
                result[row["period"][:7]][series_id] = row["value"]
        elif series_id == "goc_5y_yield":
            groups = defaultdict(list)
            for row in rows:
                groups[row["period"][:7]].append(row["value"])
            for period, values in groups.items():
                result[period][series_id] = mean(values)
        else:
            for row in rows:
                result[row["period"]][series_id] = row["value"]
    for period, values in result.items():
        if any(k in values for k in ("trreb_sales", "trreb_new_listings", "trreb_active_listings")):
            values.update(resale_metrics(values.get("trreb_sales"), values.get("trreb_new_listings"), values.get("trreb_active_listings")))
    for field in ("trreb_sales", "trreb_new_listings", "trreb_active_listings", "trreb_hpi_composite",
                  "toronto_cma_2011_starts", "toronto_cma_2011_completions",
                  "toronto_cma_2011_under_construction"):
        source = {period: values[field] for period, values in result.items() if field in values}
        for period in source:
            result[period][field + "_yoy"] = year_over_year(source, period)
    return dict(sorted(result.items()))
