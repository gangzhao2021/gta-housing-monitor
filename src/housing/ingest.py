import csv
import hashlib
import io
import json
import math
import os
import posixpath
import re
import shutil
import zipfile
from xml.etree import ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .catalog import SERIES, SOURCE_URLS

ROOT = Path(__file__).resolve().parents[2]

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def register_raw(db, path, source, url, reference_period, method):
    path = Path(path)
    sha = digest(path)
    retrieved_at = datetime.fromtimestamp(Path(path).stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
    absolute = path.resolve()
    database = next((row[2] for row in db.execute("PRAGMA database_list") if row[1] == "main"), "")
    private_source = any(absolute.is_relative_to((ROOT / "data" / folder).resolve())
                         for folder in ("raw", "manual"))
    if (database and Path(database).resolve() == (ROOT / "data/housing.sqlite3").resolve()
            and not private_source):
        archive = ROOT / "data/raw/imported"
        archive.mkdir(parents=True, exist_ok=True, mode=0o700)
        archive.chmod(0o700)
        saved = archive / f"{sha}{path.suffix.lower()}"
        if not saved.exists():
            temporary = archive / f".{saved.name}.{os.getpid()}.tmp"
            try:
                with path.open("rb") as source_file, temporary.open("xb") as output:
                    shutil.copyfileobj(source_file, output)
                temporary.chmod(0o600)
                if digest(temporary) != sha:
                    raise ValueError(f"Source changed during private copy: {path}")
                temporary.replace(saved)
            finally:
                temporary.unlink(missing_ok=True)
        elif digest(saved) != sha:
            raise ValueError(f"Private source copy has wrong hash: {saved}")
        absolute = saved.resolve()
    try:
        saved_path = str(absolute.relative_to(ROOT.resolve()))
    except ValueError:
        saved_path = str(absolute)
    db.execute("""INSERT INTO raw_files VALUES (?,?,?,?,?,?,?)
      ON CONFLICT(sha256) DO UPDATE SET source=excluded.source,
      source_url=excluded.source_url,
      reference_period=COALESCE(excluded.reference_period,raw_files.reference_period),
      method=CASE WHEN excluded.method LIKE 'rejected%' AND raw_files.method NOT LIKE 'rejected%'
                  THEN raw_files.method ELSE excluded.method END""",
      (sha, saved_path, source, url, retrieved_at, reference_period, method))
    return sha


def sync_live_manifest(db):
    """Keep the recoverable inventory current, including rejected imports."""
    database = next((row[2] for row in db.execute("PRAGMA database_list") if row[1] == "main"), "")
    if database and Path(database).resolve() == (ROOT / "data/housing.sqlite3").resolve():
        from .manifest import write_manifest
        write_manifest(db, ROOT)

def put(db, series_id, period, value, sha):
    if series_id not in SERIES:
        raise ValueError(f"Unknown series: {series_id}")
    if not math.isfinite(value):
        raise ValueError(f"Non-finite value: {series_id} {period}")
    current = db.execute("SELECT value,version FROM observations WHERE series_id=? AND period=? ORDER BY version DESC LIMIT 1",
                         (series_id, period)).fetchone()
    if current and current["value"] == value:
        return "unchanged"
    prior_file = db.execute(
        "SELECT 1 FROM observations WHERE series_id=? AND period=? AND raw_sha256=? LIMIT 1",
        (series_id, period, sha)).fetchone()
    if prior_file:
        raise ValueError(f"Stale source replay would replace a newer value: {series_id} {period}")
    version = 1 if current is None else current["version"] + 1
    db.execute("""INSERT INTO observations
      (series_id,period,value,version,raw_sha256,first_seen_at)
      VALUES (?,?,?,?,?,?)""", (series_id, period, value, version, sha, now()))
    return "inserted" if current is None else "revised"

def validate_rows(rows):
    """Reject a whole source batch before any observations become visible."""
    seen = {}
    bounds = {
        "boc_policy_rate": (0, 30), "goc_5y_yield": (0, 30),
        "mortgage_uninsured_fixed_5plus": (0, 30),
        "toronto_unemployment_rate": (0, 100), "toronto_employment_rate": (0, 100),
        "toronto_participation_rate": (0, 100),
        "trreb_sales": (1, 30000), "trreb_new_listings": (1, 100000),
        "trreb_active_listings": (1, 100000), "trreb_hpi_composite": (100, 500),
        "trreb_hpi_benchmark": (100000, 2000000),
        "toronto_cma_2011_starts": (0, 100000),
        "toronto_cma_2011_completions": (0, 100000),
        "toronto_cma_2011_under_construction": (0, 1000000),
        "toronto_cma_2021_population": (1000000, 20000000),
        "wti_cushing_spot_price": (1, 1000),
        "usd_cad_monthly": (0.1, 10),
        "boc_energy_price_index": (1, 10000),
        "toronto_residential_construction_cost_index": (1, 1000),
    }
    from .background_series import CONFIG
    bounds.update({c['id']: ((0, 40) if c['unit'] == '%' else (0, 100000) if c['unit'] == 'units' else (1, 10000))
                   for c in CONFIG.values()})
    bounds.update({series_id: ((0, 100) if definition[4] == "%" else (300, 10000))
                   for series_id, definition in SERIES.items() if definition[1] == "CMHC"})
    bounds.update({s: (300, 10000) for s in SERIES if s.startswith(("toronto_asking_rent_", "regional_asking_"))})
    for series_id, period, value in rows:
        if series_id not in SERIES:
            raise ValueError(f"Unknown series in batch: {series_id}")
        if not math.isfinite(value):
            raise ValueError(f"Non-finite value: {series_id} {period}")
        lower, upper = bounds[series_id]
        if not lower <= value <= upper:
            raise ValueError(f"Value outside accepted range for {series_id} {period}: {value}")
        frequency = SERIES[series_id][5]
        try:
            if frequency == "daily":
                datetime.strptime(period, "%Y-%m-%d")
            elif frequency == "annual":
                datetime.strptime(period, "%Y")
            elif frequency == "quarterly":
                datetime.strptime(period + "-01", "%Y-%m-%d")
                if period[5:] not in ("01", "04", "07", "10"):
                    raise ValueError("Quarter must begin in Jan, Apr, Jul or Oct")
            else:
                datetime.strptime(period + "-01", "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(f"Invalid {frequency} period for {series_id}: {period}") from exc
        key = (series_id, period)
        if key in seen and seen[key] != value:
            raise ValueError(f"Conflicting duplicate source values: {series_id} {period}")
        seen[key] = value

def parse_boc(path):
    document = json.loads(Path(path).read_text())
    mapping = {
        "V39079": "boc_policy_rate",
        "BD.CDN.5YR.DQ.YLD": "goc_5y_yield",
        "V122667786": "mortgage_uninsured_fixed_5plus",
    }
    if not set(mapping).issubset(document.get("seriesDetail", {})):
        raise ValueError("BoC response is missing required series metadata")
    result = []
    for row in document["observations"]:
        date = row["d"]
        datetime.strptime(date, "%Y-%m-%d")
        for source_id, series_id in mapping.items():
            item = row.get(source_id)
            if item and item.get("v") not in (None, ""):
                period = date[:7] if source_id == "V122667786" else date
                result.append((series_id, period, float(item["v"])))
    if not result:
        raise ValueError("BoC response has no usable observations")
    return result

def parse_statcan(path):
    mapping = {
        "Unemployment rate": "toronto_unemployment_rate",
        "Employment rate": "toronto_employment_rate",
        "Participation rate": "toronto_participation_rate",
    }
    result = []
    with zipfile.ZipFile(path) as archive:
        with archive.open("14100460.csv") as binary:
            rows = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8-sig"))
            for row in rows:
                characteristic = row["Labour force characteristics"]
                if (row["GEO"] != "Toronto, Ontario" or row["DGUID"] != "2021S0503535"
                    or row["Statistics"] != "Estimate" or row["Data type"] != "Seasonally adjusted"
                    or characteristic not in mapping or row["UOM"] != "Percent"):
                    continue
                if row["VALUE"] and not row["STATUS"]:
                    result.append((mapping[characteristic], row["REF_DATE"], float(row["VALUE"])))
    if not result:
        raise ValueError("No Toronto CMA seasonally adjusted rate values found")
    return result

def parse_statcan_construction(path):
    mapping = {
        "Housing starts": "toronto_cma_2011_starts",
        "Housing completions": "toronto_cma_2011_completions",
        "Housing under construction": "toronto_cma_2011_under_construction",
    }
    result = []
    with zipfile.ZipFile(path) as archive:
        with archive.open("34100154.csv") as binary:
            rows = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8-sig"))
            for row in rows:
                if (row["GEO"] != "Toronto, Ontario" or row["DGUID"] != "2011S0503535"
                    or row["Housing estimates"] not in mapping or row["Type of unit"] != "Total units"
                    or row["UOM"] != "Units" or row["SCALAR_FACTOR"] != "units"):
                    continue
                if row["VALUE"] and not row["STATUS"]:
                    result.append((mapping[row["Housing estimates"]], row["REF_DATE"], float(row["VALUE"])))
    if not result:
        raise ValueError("No Toronto CMA 2011-boundary construction observations found")
    return result

def parse_statcan_population(path):
    result = []
    with zipfile.ZipFile(path) as archive:
        with archive.open("17100148.csv") as binary:
            rows = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8-sig"))
            for row in rows:
                if (row["GEO"] != "Toronto (CMA), Ontario" or row["DGUID"] != "2021S0503535"
                    or row["Gender"] != "Total - gender" or row["Age group"] != "All ages"
                    or row["UOM"] != "Persons" or row["SCALAR_FACTOR"] != "units"):
                    continue
                if row["VALUE"] and not row["STATUS"]:
                    result.append(("toronto_cma_2021_population", row["REF_DATE"], float(row["VALUE"])))
    if not result:
        raise ValueError("No Toronto CMA 2021-boundary population observations found")
    return result

def parse_cmhc_rental_details(path, region_label="Toronto CMA", series_prefix="toronto", pbr_only=False):
    """Read values and their source quality flags without erasing missingness.

    Each result has series_id, period, value, status (available, suppressed or
    not_available), quality (a/b/c/d or None), significance, sheet and cell.
    Significance preserves the source symbol; absent means not supplied, not
    statistically insignificant. Only the numeric wrapper is passed to ingest.
    """
    ns = {
        "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "p": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}
        sheets = {}
        for sheet in workbook.find("m:sheets", ns):
            target = targets[sheet.attrib["{%s}id" % ns["r"]]].lstrip("/")
            sheet_path = target if target.startswith("xl/") else posixpath.normpath(posixpath.join("xl", target))
            sheets[sheet.attrib["name"]] = ET.fromstring(archive.read(sheet_path))
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            table = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(node.text or "" for node in item.iter("{%s}t" % ns["m"]))
                       for item in table]

    def cell_value(cell):
        if cell.attrib.get("t") == "inlineStr":
            return "".join(node.text or "" for node in cell.iter("{%s}t" % ns["m"]))
        value = cell.find("m:v", ns)
        if value is None:
            return None
        if cell.attrib.get("t") == "s":
            return strings[int(value.text)]
        return value.text

    def rows(sheet_name):
        if sheet_name not in sheets:
            raise ValueError(f"CMHC workbook missing required worksheet: {sheet_name}")
        parsed = {}
        for row in sheets[sheet_name].findall(".//m:sheetData/m:row", ns):
            values = {}
            for cell in row.findall("m:c", ns):
                match = re.fullmatch(r"([A-Z]+)([0-9]+)", cell.attrib["r"])
                if match:
                    value = cell_value(cell)
                    if value is not None:
                        values[match.group(1)] = value
            parsed[int(row.attrib["r"])] = values
        return parsed

    def column_number(column):
        number = 0
        for letter in column:
            number = number * 26 + ord(letter) - ord("A") + 1
        return number

    def column_name(number):
        letters = ""
        while number:
            number, remainder = divmod(number - 1, 26)
            letters = chr(ord("A") + remainder) + letters
        return letters

    expected_bedrooms = {
        "Studio": "studio", "1 Bedroom": "1br", "2 Bedroom": "2br",
        "3 Bedroom +": "3plus", "Total": "total",
    }
    result = []
    workbook_years = None
    for sheet_name, market, measure in (
        ("Table 1.1.1", "pbr", "vacancy"),
        ("Table 1.1.2", "pbr", "rent"),
        ("Table 4.1.1", "condo", "vacancy"),
        ("Table 4.1.3", "condo", "rent"),
    ):
        if pbr_only and market != "pbr":
            continue
        table = rows(sheet_name)
        title = table.get(3, {}).get("A", "")
        if not title.startswith(sheet_name.removeprefix("Table ") + " ") or "Toronto CMA" not in title:
            raise ValueError(f"Unexpected CMHC title in {sheet_name}: {title!r}")
        required_title = "Vacancy Rates (%)" if measure == "vacancy" else "Average Rents ($)"
        if required_title not in title:
            raise ValueError(f"Unexpected CMHC measure in {sheet_name}: {title!r}")
        if not any("2021 census geographic definitions" in value for row in table.values() for value in row.values()):
            raise ValueError(f"Unverified CMHC geographic boundary in {sheet_name}")
        matches = [(number, row) for number, row in table.items() if row.get("A") == region_label]
        if len(matches) != 1:
            raise ValueError(f"CMHC {sheet_name} requires exactly one {region_label} row")
        row_number, row = matches[0]
        group_header = table.get(6, {})
        # Older CMHC editions call the same zero-bedroom category Bachelor.
        group_header = {column: "Studio" if value == "Bachelor" else value
                        for column, value in group_header.items()}
        labels = ({"Rental Condominium Apartments": "total", "Apartments in the RMS": None}
                  if market == "condo" and measure == "vacancy" else expected_bedrooms)
        if set(group_header.values()) != set(labels) or len(group_header) != len(labels):
            raise ValueError(f"Unexpected CMHC bedroom/market header in {sheet_name}: {group_header}")
        groups = sorted(((column_number(column), label) for column, label in group_header.items()))
        for index, (first_column, label) in enumerate(groups):
            bedroom = labels[label]
            if bedroom is None:
                continue  # The comparison RMS market is already imported from its own table.
            end_column = groups[index + 1][0] if index + 1 < len(groups) else 1000
            period_columns = [(column, value) for column, value in table.get(7, {}).items()
                              if first_column <= column_number(column) < end_column]
            if len(period_columns) != 2:
                raise ValueError(f"CMHC {sheet_name} {label} requires two survey year columns")
            periods = []
            for column, period_header in sorted(period_columns, key=lambda item: column_number(item[0])):
                match = re.fullmatch(r"Oct-(\d{2})", period_header)
                if not match:
                    raise ValueError(f"Unexpected CMHC survey period header: {period_header!r}")
                period = "20" + match.group(1)
                periods.append(period)
                raw_value = str(row.get(column, "")).strip()
                quality = row.get(column_name(column_number(column) + 1))
                significance_column = column_name(column_number(column) + 2)
                significance = row.get(significance_column)
                if significance not in ("↑", "↓", "-", "–", "++"):
                    significance = None
                if raw_value == "**":
                    value, status, quality = None, "suppressed", None
                elif raw_value in ("", "n/a", "N/A", "..", "..."):
                    value, status, quality = None, "not_available", None
                else:
                    try:
                        value = float(raw_value.replace(",", ""))
                    except ValueError as exc:
                        raise ValueError(f"Unrecognized CMHC value {raw_value!r} in {sheet_name} {column}{row_number}") from exc
                    if quality not in ("a", "b", "c", "d"):
                        raise ValueError(f"Missing CMHC quality flag in {sheet_name} {column}{row_number}")
                    status = "available"
                suffix = "rate" if measure == "vacancy" and bedroom == "total" else bedroom
                result.append({"series_id": f"{series_prefix}_{market}_{measure}_{suffix}",
                               "period": period, "value": value, "status": status,
                               "quality": quality, "significance": significance,
                               "sheet": sheet_name, "cell": f"{column}{row_number}"})
            if int(periods[1]) != int(periods[0]) + 1:
                raise ValueError(f"Nonconsecutive CMHC survey years in {sheet_name}: {periods}")
            if workbook_years is not None and periods != workbook_years:
                raise ValueError(f"Inconsistent CMHC survey years in {sheet_name}: {periods}")
            workbook_years = periods
    validate_rows([(item["series_id"], item["period"], item["value"])
                   for item in result if item["status"] == "available"])
    return result


def parse_cmhc_rental(path):
    """Numeric import rows; suppressed/absent cells remain missing, never zero."""
    return [(item["series_id"], item["period"], item["value"])
            for item in parse_cmhc_rental_details(path) if item["status"] == "available"]

def parse_trreb(path, pdf_path):
    expected = {"sales": "trreb_sales", "new_listings": "trreb_new_listings",
                "active_listings": "trreb_active_listings", "hpi_composite": "trreb_hpi_composite",
                "hpi_benchmark": "trreb_hpi_benchmark"}
    with Path(path).open(newline="", encoding="utf-8-sig") as source:
        rows = list(csv.DictReader(source))
    if not rows:
        raise ValueError("Empty TRREB manual CSV")
    result = []
    for row in rows:
        pdf = Path(pdf_path) / row["source_pdf_name"] if Path(pdf_path).is_dir() and row.get("source_pdf_name") else Path(pdf_path)
        if row["source_pdf_sha256"] != digest(pdf) or row["geography"] != "All TRREB Areas" or row["home_type"] != "All Home Types":
            raise ValueError("TRREB row does not match its source PDF or selected geography/home type")
        if not (int(row["sales_page"]) > 0 and int(row["hpi_page"]) > 0):
            raise ValueError("TRREB PDF page references required")
        datetime.strptime(row["period"] + "-01", "%Y-%m-%d")
        if row.get("source_pdf_name") and row["source_pdf_name"] != f"mw{row['period'][2:4]}{row['period'][5:7]}.pdf":
            raise ValueError("TRREB PDF filename and reference month differ")
        for column, series_id in expected.items():
            if row[column]:
                result.append((series_id, row["period"], float(row[column])))
    return result

def ingest(db, source, raw_path, source_url, reference_period, method, rows):
    sha = digest(raw_path)
    counts = defaultdict(int)
    started = now()
    with db:
        register_raw(db, raw_path, source, source_url, reference_period, method)
    try:
        with db:
            validate_rows(rows)
            for series_id, period, value in rows:
                counts[put(db, series_id, period, value, sha)] += 1
            db.execute("""INSERT INTO ingestion_runs
              (source,started_at,status,raw_sha256,inserted,unchanged,revised)
              VALUES (?,?,?,?,?,?,?)""",
              (source, started, "success", sha, counts["inserted"], counts["unchanged"], counts["revised"]))
    except Exception as exc:
        with db:
            db.execute("INSERT INTO ingestion_runs (source,started_at,status,raw_sha256,error) VALUES (?,?,?,?,?)",
                       (source, started, "failed", sha, str(exc)))
        raise
    finally:
        sync_live_manifest(db)
    return dict(counts)

def record_parse_failure(db, source, raw_path, error, source_url=None):
    """Record rejected source files even when parsing fails before ingest()."""
    from datetime import datetime, timezone
    import hashlib
    path = Path(raw_path)
    sha = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    with db:
        if sha:
            register_raw(db, path, source, source_url or SOURCE_URLS.get(source, "unknown"),
                         None, "rejected source input; see ingestion run error")
        db.execute("""INSERT INTO ingestion_runs
          (source,started_at,status,raw_sha256,error) VALUES (?,?,?,?,?)""",
          (source, datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "failed", sha, str(error)))
    # A failed parse can still register a rejected raw file. Keep the local
    # recovery manifest aligned with that durable audit record.
    sync_live_manifest(db)
