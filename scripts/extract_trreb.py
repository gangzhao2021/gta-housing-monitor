"""Conservative extraction of the All TRREB Areas / All Home Types row."""
import csv
import hashlib
import io
import re
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
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

def extract(path):
    reader = PdfReader(path)
    period = f"20{path.stem[2:4]}-{path.stem[4:6]}"
    sales_page, sales = row_on_page(reader, "SUMMARY OF EXISTING HOME TRANSACTIONS")
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
