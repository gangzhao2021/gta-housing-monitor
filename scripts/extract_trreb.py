"""Conservative extraction of the All TRREB Areas / All Home Types row."""
import csv
import hashlib
import io
import re
import sys
import unicodedata
from pathlib import Path
import pymupdf
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from housing.breakdowns import trreb_hpi_breakdown
from scripts.extract_trreb_districts import dashboard_section, data_rows, header_columns

SOURCE = ROOT / "data/raw/trreb"
OUTPUT_DIR = ROOT / "data/manual"
ROW = re.compile(r"^\s*All\s+TRREB\s+Areas\s+(.*)$", re.I)
NUMBER = re.compile(r"\$?-?\d[\d,]*(?:\.\d+)?%?")

def row_on_page(reader, marker):
    for index, page in enumerate(reader.pages):
        text = page.extract_text(extraction_mode="layout") or ""
        if marker not in " ".join(text.upper().split()):
            continue
        for line in text.splitlines():
            match = ROW.match(line)
            if match:
                return index + 1, NUMBER.findall(match.group(1))
    raise ValueError(f"Missing {marker} / All TRREB Areas row")

def integer(value):
    return int(value.replace(",", "").replace("$", ""))

def front_summary(page, period):
    """Front-page Year-over-Year Summary of the September 2026 layout."""
    blocks = [[line.strip() for line in unicodedata.normalize("NFKC", b[4]).splitlines() if line.strip()]
              for b in page.get_text("blocks")]
    year = int(period[:4])
    if ["Metrics", str(year), str(year - 1)] not in blocks:
        raise ValueError("Front-page year-over-year summary not found")
    values = {}
    for lines in blocks:
        if (len(lines) == 3 and lines[0] in ("Sales", "New Listings", "Active Listings")
                and all(re.fullmatch(r"[\d,]+", value) for value in lines[1:])):
            if lines[0] in values:
                raise ValueError(f"Duplicate front-page {lines[0]} summary")
            values[lines[0]] = integer(lines[1])
    return values


def dashboard_values(path, period):
    """Layout introduced with September 2026: word boxes, checked against page 1."""
    with pymupdf.open(path) as document:
        for index, page in enumerate(document):
            header_y, columns = header_columns(page)
            if not columns or dashboard_section(page, header_y) != ("all_types", period):
                continue
            problems = []
            total = [row for row in data_rows(page, header_y, columns, index + 1, problems)
                     if row["area"] == "All TRREB Areas"]
            if problems or len(total) != 1:
                raise ValueError(f"All TRREB Areas row failed validation: {problems}")
            row, sales_page = total[0], index + 1
            break
        else:
            raise ValueError("Missing All TRREB Areas / All Home types table")
        summary = front_summary(document[0], period)
    table = {"Sales": row["sales"], "New Listings": row["new_listings"],
             "Active Listings": row["active_listings"]}
    if summary != table:
        raise ValueError(f"Table totals {table} differ from front-page summary {summary}")
    composite = {r["metric"]: r for r in trreb_hpi_breakdown(path) if r["type_id"] == "composite"}
    hpi_page = composite["index"]["source_page"]
    return (sales_page, hpi_page, [row["sales"], row["new_listings"], row["active_listings"],
                                   composite["index"]["value"], int(composite["benchmark"]["value"])])


def extract(path):
    reader = PdfReader(path)
    period = f"20{path.stem[2:4]}-{path.stem[4:6]}"
    try:
        sales_page, sales = row_on_page(reader, "SUMMARY OF EXISTING HOME TRANSACTIONS")
    except ValueError:
        sales_page, hpi_page, values = dashboard_values(path, period)
    else:
        hpi_page, hpi = row_on_page(reader, "HOME PRICE INDEX")
        if len(sales) < 7 or len(hpi) < 2:
            raise ValueError(f"Incomplete columns: {len(sales)} sales, {len(hpi)} HPI")
        values = [integer(sales[0]), integer(sales[4]), integer(sales[6]), float(hpi[0]), integer(hpi[1])]
    if not (0 < values[0] < 30000 and 0 < values[1] < 100000 and 0 < values[2] < 100000
            and 100 < values[3] < 500 and 100000 < values[4] < 2000000):
        raise ValueError(f"Out-of-range total row {values}")
    return [period, "All TRREB Areas", "All Home Types", *values,
            hashlib.sha256(path.read_bytes()).hexdigest(), sales_page, hpi_page, path.name]

def main():
    fields = ["period", "geography", "home_type", "sales", "new_listings", "active_listings",
              "hpi_composite", "hpi_benchmark", "source_pdf_sha256", "sales_page", "hpi_page", "source_pdf_name"]
    records, failed = [], []
    for path in sorted(SOURCE.glob("mw2[2-6][0-1][0-9].pdf")):
        try:
            records.append(extract(path))
            print("extracted", path.name, records[-1][3:8])
        except Exception as error:
            failed.append((path.name, str(error)))
    if not records or failed:
        raise RuntimeError(f"Extraction incomplete: {len(records)} rows; failures {failed}")
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(fields)
    writer.writerows(records)
    content = buffer.getvalue()
    short_hash = hashlib.sha256(content.encode()).hexdigest()[:10]
    output = OUTPUT_DIR / f"trreb-extracted-{records[0][0]}-to-{records[-1][0]}-{short_hash}.csv"
    if not output.exists():
        output.write_text(content)
    print(f"saved {len(records)} rows in {output.name}")

if __name__ == "__main__":
    main()
