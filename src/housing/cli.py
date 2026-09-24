import argparse
import csv
from pathlib import Path

from .db import connect
from .ingest import (ingest, parse_boc, parse_statcan, parse_statcan_construction,
                     parse_statcan_population, parse_cmhc_rental, parse_trreb, record_parse_failure)

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data/housing.sqlite3"

def parse_or_record(db, source, path, parser_fn, source_url):
    try:
        return parser_fn()
    except Exception as exc:
        record_parse_failure(db, source, path, exc, source_url)
        raise

def manifest(db):
    target = ROOT / "data/raw/manifest.csv"
    with target.open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["source", "source_url", "retrieved_at", "reference_period", "path", "sha256", "method"])
        for row in db.execute("SELECT * FROM raw_files ORDER BY retrieved_at,source"):
            saved_path = Path(row["path"])
            if saved_path.is_absolute():
                saved_path = saved_path.relative_to(ROOT)
            writer.writerow([row["source"], row["source_url"], row["retrieved_at"],
                             row["reference_period"], str(saved_path),
                             row["sha256"], row["method"]])
    return target

def main():
    parser = argparse.ArgumentParser(description="Public data import for Toronto housing dashboard")
    parser.add_argument("source", choices=["boc", "statcan", "construction", "population", "cmhc-rental", "trreb", "rentals", "rentals-regions", "cmhc-regions", "status"])
    parser.add_argument("--db", type=Path, default=DB)
    parser.add_argument("--file", type=Path, help="New immutable source file; never overwrite an earlier download")
    parser.add_argument("--chart", type=Path, help="Public Datawrapper HTML metadata paired with Rentals.ca CSV")
    parser.add_argument("--pdf", type=Path, help="TRREB source PDF paired with manual CSV")
    parser.add_argument("--source-url", help="Required with a custom file")
    args = parser.parse_args()
    db = connect(args.db)
    if args.file and not args.source_url:
        parser.error("--source-url is required with --file")
    if args.source == "status":
        for row in db.execute("SELECT source, MAX(started_at) last_run, COUNT(*) runs FROM ingestion_runs GROUP BY source"):
            print(dict(row))
        for row in db.execute("SELECT series_id,MIN(period) first,MAX(period) last,COUNT(DISTINCT period) periods FROM observations GROUP BY series_id ORDER BY series_id"):
            print(dict(row))
        return
    if args.source == "rentals-regions":
        if not args.file or not args.chart or not args.source_url:
            parser.error("rentals-regions requires --file CSV --chart HTML --source-url report-URL")
        from .regional_ingest import import_regional_csv
        summary = import_regional_csv(db, args.file, args.chart, args.source_url)
    elif args.source == "cmhc-regions":
        if not args.file or not args.source_url:
            parser.error("cmhc-regions requires --file XLSX --source-url source-URL")
        from .regional_ingest import regional_cmhc_details
        rows = parse_or_record(db, "CMHC Rental Market Survey", args.file,
            lambda: [(r['series_id'], r['period'], r['value']) for r in regional_cmhc_details(args.file) if r['value'] is not None], args.source_url)
        summary = ingest(db, "CMHC Rental Market Survey", args.file, args.source_url,
            f"{min(r[1] for r in rows)}/{max(r[1] for r in rows)}", "official XLSX; regional PBR Tables 1.1.1 and 1.1.2", rows)
    elif args.source == "rentals":
        if not args.file or not args.chart or not args.source_url:
            parser.error("rentals requires --file CSV --chart HTML --source-url archived-report-URL")
        from .rentals import import_dataset
        summary = import_dataset(db, args.file, args.chart, args.source_url)
    elif args.source == "boc":
        path = args.file or ROOT / "data/raw/boc/core-2022-09-to-2026-08.json"
        url = args.source_url or "https://www.bankofcanada.ca/valet/observations/V39079,BD.CDN.5YR.DQ.YLD,V122667786/json?start_date=2022-09-01&end_date=2026-08-31"
        rows = parse_or_record(db, "BoC", path, lambda: parse_boc(path), url)
        summary = ingest(db, "BoC", path, url, f"{rows[0][1]}/{rows[-1][1]}", "API JSON", rows)
    elif args.source == "statcan":
        path = args.file or ROOT / "data/raw/statcan/14100460-eng.zip"
        url = args.source_url or "https://www150.statcan.gc.ca/n1/en/tbl/csv/14100460-eng.zip"
        rows = parse_or_record(db, "StatsCan", path, lambda: parse_statcan(path), url)
        summary = ingest(db, "StatsCan", path, url, f"{rows[0][1]}/{rows[-1][1]}", "official CSV ZIP", rows)
    elif args.source == "construction":
        path = args.file or ROOT / "data/raw/statcan/34100154-eng.zip"
        url = args.source_url or "https://www150.statcan.gc.ca/n1/en/tbl/csv/34100154-eng.zip"
        rows = parse_or_record(db, "StatsCan construction", path,
                               lambda: parse_statcan_construction(path), url)
        summary = ingest(db, "StatsCan construction", path, url,
                         f"{rows[0][1]}/{rows[-1][1]}", "official CMHC/StatsCan CSV ZIP", rows)
    elif args.source == "population":
        path = args.file or ROOT / "data/raw/statcan/17100148-eng.zip"
        url = args.source_url or "https://www150.statcan.gc.ca/n1/en/tbl/csv/17100148-eng.zip"
        rows = parse_or_record(db, "StatsCan population", path,
                               lambda: parse_statcan_population(path), url)
        summary = ingest(db, "StatsCan population", path, url,
                         f"{rows[0][1]}/{rows[-1][1]}", "official CSV ZIP", rows)
    elif args.source == "cmhc-rental":
        path = args.file or ROOT / "data/raw/cmhc/rmr-toronto-2025-en.xlsx"
        url = args.source_url or "https://assets.cmhc-schl.gc.ca/sites/cmhc/professional/housing-markets-data-and-research/housing-data-tables/rental-market/rental-market-report-data-tables/2025/rmr-toronto-2025-en.xlsx"
        rows = parse_or_record(db, "CMHC Rental Market Survey", path,
                               lambda: parse_cmhc_rental(path), url)
        summary = ingest(db, "CMHC Rental Market Survey", path, url,
                         f"{min(r[1] for r in rows)}/{max(r[1] for r in rows)}",
                         "official XLSX; Toronto CMA rows in Tables 1.1.1, 1.1.2, 4.1.1 and 4.1.3", rows)
    else:
        candidates = sorted((ROOT / "data/manual").glob("trreb-extracted-*.csv"))
        path = args.file or (candidates[-1] if candidates else ROOT / "data/manual/trreb-market-watch.csv")
        pdf = args.pdf or ROOT / "data/raw/trreb"
        url = args.source_url or "https://trreb.ca/market-data/market-watch/market-watch-archive/"
        rows = parse_or_record(db, "TRREB", path, lambda: parse_trreb(path, pdf), url)
        with db:
            from .ingest import register_raw
            with path.open(newline="", encoding="utf-8-sig") as source:
                for item in csv.DictReader(source):
                    pdf_file = pdf / item["source_pdf_name"] if pdf.is_dir() and item.get("source_pdf_name") else pdf
                    pdf_url = f"https://trreb.ca/wp-content/files/market-stats/market-watch/{pdf_file.name}"
                    register_raw(db, pdf_file, "TRREB", pdf_url, item["period"], "official PDF")
        summary = ingest(db, "TRREB", path, url, f"{rows[0][1]}/{rows[-1][1]}", "PDF table extraction; page references in CSV", rows)
    print(args.source, summary)
    print("manifest:", manifest(db))

if __name__ == "__main__":
    main()
