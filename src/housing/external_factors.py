"""Strict parsers for selected official external context series.

These observations are descriptive context. Publication vintages are not
available from these current-history downloads and must not be inferred from
the file retrieval time.
"""
import csv
import io
import json
import re
import zipfile
from datetime import datetime
from html import unescape
from pathlib import Path


def _boc_monthly(path, source_key, series_id):
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if source_key not in document.get("seriesDetail", {}):
        raise ValueError(f"BoC response lacks {source_key} metadata")
    rows = []
    for item in document.get("observations", []):
        period = item["d"]
        datetime.strptime(period, "%Y-%m-%d")
        if not period.endswith("-01"):
            raise ValueError(f"Expected a monthly BoC period: {period}")
        value = item.get(source_key, {}).get("v")
        if value not in (None, ""):
            rows.append((series_id, period[:7], float(value)))
    if not rows:
        raise ValueError(f"BoC response has no usable {source_key} observations")
    return rows


def parse_fx(path):
    return _boc_monthly(path, "FXMUSDCAD", "usd_cad_monthly")


def parse_energy(path):
    return _boc_monthly(path, "M.ENER", "boc_energy_price_index")


def parse_wti(path):
    """Read the EIA's WTI monthly HTML table, retaining missing months as gaps."""
    page = Path(path).read_text(encoding="utf-8")
    if "Cushing, OK WTI Spot Price FOB" not in page or "Dollars per Barrel" not in page:
        raise ValueError("Not the EIA Cushing WTI monthly source")
    match = re.search(r"<tbody>(.*?)</tbody>", page, re.I | re.S)
    if not match or not all(f">{month}<" in page for month in ("Jan", "Feb", "Dec")):
        raise ValueError("EIA WTI monthly table is missing its month header or body")
    rows = []
    for tr in re.findall(r"<tr\b[^>]*>(.*?)</tr>", match.group(1), re.I | re.S):
        cells = [unescape(re.sub(r"<[^>]+>", "", value)).replace("\xa0", " ").strip()
                 for value in re.findall(r"<td\b[^>]*>(.*?)</td>", tr, re.I | re.S)]
        if not cells or not re.fullmatch(r"\d{4}", cells[0]):
            continue
        if len(cells) != 13:
            raise ValueError(f"EIA WTI year {cells[0]} does not contain twelve month cells")
        year = int(cells[0])
        for month, value in enumerate(cells[1:], 1):
            period = f"{year:04d}-{month:02d}"
            if period < "2022-09" or value in ("", "-", "--", "NA", "W"):
                continue
            rows.append(("wti_cushing_spot_price", period, float(value.replace(",", ""))))
    if not rows:
        raise ValueError("EIA WTI monthly table has no usable recent values")
    return rows


def parse_building_cost(path):
    """Toronto CMA residential composite only; quarter is stored by first month."""
    rows = []
    with zipfile.ZipFile(path) as archive:
        with archive.open("18100289.csv") as binary:
            reader = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8-sig"))
            for item in reader:
                if item["VECTOR"] != "v1617912612":
                    continue
                if (item["GEO"] != "Toronto, Ontario" or item["DGUID"] != "2021S0503535"
                        or item["Type of building"] != "Residential buildings [621]"
                        or item["Division"] != "Division composite"
                        or item["UOM"] != "Index, 2023=100" or item["SCALAR_FACTOR"] != "units"):
                    raise ValueError("Toronto residential construction index source definition changed")
                period = item["REF_DATE"]
                if period[5:] not in ("01", "04", "07", "10"):
                    raise ValueError(f"Unexpected construction quarter: {period}")
                if item["VALUE"] and not item["STATUS"]:
                    rows.append(("toronto_residential_construction_cost_index", period, float(item["VALUE"])))
    if not rows:
        raise ValueError("No Toronto residential construction-cost index values found")
    return rows
