"""Download immutable public source snapshots for the housing dashboard."""
import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def previous_month():
    from datetime import date
    today = date.today()
    year, month = today.year, today.month - 1
    if month == 0:
        year, month = year - 1, 12
    return f"{year:04d}-{month:02d}"

def download(url, destination, kind):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        print("already saved", destination.relative_to(ROOT))
        return False
    temporary = destination.with_name(destination.name + ".download")
    try:
        request = Request(url, headers={"User-Agent": "TorontoHousingLeadingIndicator/0.1 (public data)"})
        with urlopen(request, timeout=90) as response, temporary.open("xb") as output:
            payload = response.read()
            output.write(payload)
        if kind == "json":
            body = json.loads(temporary.read_text(encoding="utf-8"))
            if not body.get("observations") or not body.get("seriesDetail"):
                raise ValueError("BoC response is missing observations or series metadata")
        elif kind in ("zip", "xlsx"):
            with zipfile.ZipFile(temporary) as archive:
                if archive.testzip() is not None:
                    raise ValueError("Downloaded ZIP failed its CRC check")
                if kind == "xlsx" and "xl/workbook.xml" not in archive.namelist():
                    raise ValueError("Downloaded CMHC file is not an Excel workbook")
        temporary.replace(destination)
        print("saved", destination.relative_to(ROOT), f"({destination.stat().st_size:,} bytes)")
        return True
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--end-month", default=previous_month(), help="Latest complete month, YYYY-MM")
    parser.add_argument("--start-month", default="2022-09", help="BoC daily-series start month, YYYY-MM")
    parser.add_argument("--include-population", action="store_true", help="Download the 22 MB annual table snapshot")
    parser.add_argument("--include-rental", action="store_true", help="Download a CMHC Toronto Rental Market Survey workbook")
    parser.add_argument("--rental-year", type=int, default=2025, help="CMHC rental-survey edition year (default: 2025)")
    args = parser.parse_args()
    import re
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", args.end_month) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", args.start_month):
        parser.error("months must use YYYY-MM")
    if args.start_month > args.end_month:
        parser.error("--start-month must not be later than --end-month")
    from calendar import monthrange
    end_date = f"{args.end_month}-{monthrange(*map(int, args.end_month.split('-')))[1]:02d}"
    run_stamp = args.end_month
    boc_url = ("https://www.bankofcanada.ca/valet/observations/"
               "V39079,BD.CDN.5YR.DQ.YLD,V122667786/json"
               f"?start_date={args.start_month}-01&end_date={end_date}")
    download(boc_url, ROOT / "data/raw/boc" / f"core-{args.start_month}-to-{run_stamp}.json", "json")
    tables = [
        ("14100460", "14-10-0460-01 Toronto CMA employment", "statcan"),
        ("34100154", "34-10-0154-01 housing construction", "statcan"),
    ]
    if args.include_population:
        tables.append(("17100148", "17-10-0148-01 CMA population", "statcan"))
    for table_id, label, folder in tables:
        url = f"https://www150.statcan.gc.ca/n1/en/tbl/csv/{table_id}-eng.zip"
        destination = ROOT / "data/raw" / folder / f"{table_id}-{run_stamp}-eng.zip"
        print(label)
        download(url, destination, "zip")
    if args.include_rental:
        rental_year = args.rental_year
        if rental_year < 2000 or rental_year > 2100:
            parser.error("--rental-year must be a four-digit year")
        url = ("https://assets.cmhc-schl.gc.ca/sites/cmhc/professional/"
               "housing-markets-data-and-research/housing-data-tables/rental-market/"
               f"rental-market-report-data-tables/{rental_year}/rmr-toronto-{rental_year}-en.xlsx")
        download(url, ROOT / "data/raw/cmhc" / f"rmr-toronto-{rental_year}-en.xlsx", "xlsx")

if __name__ == "__main__":
    main()
