"""Import verified Rentals.ca regional ranking-chart transcriptions.

The CSV is an audit transcript, not an automated scrape. Each observation is
backed by a saved chart image whose SHA-256 is checked before insertion.
"""
import argparse
import csv
import io
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from housing.db import connect
from housing.ingest import digest, ingest, register_raw, sync_live_manifest

REGIONS = {"north_york", "scarborough", "markham", "vaughan", "mississauga", "oakville"}
FIELDS = {"period", "region", "value", "report_url", "image_url", "image_file", "image_sha256"}


def load_rows(path):
    with path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        if set(reader.fieldnames or []) != FIELDS:
            raise ValueError("Archive transcript columns differ from the required schema")
        rows = list(reader)
    if not rows:
        raise ValueError("Archive transcript is empty")
    seen = set()
    sources = defaultdict(list)
    for row in rows:
        period, region = row["period"], row["region"]
        if not re.fullmatch(r"202[45]-(0[1-9]|1[0-2])", period) or region not in REGIONS:
            raise ValueError(f"Invalid period or region: {period} {region}")
        if period >= "2025-11" or (period, region) in seen:
            raise ValueError(f"Duplicate or existing period: {period} {region}")
        seen.add((period, region))
        if not row["report_url"].startswith("https://rentals.ca/blog/"):
            raise ValueError(f"Unexpected report URL: {row['report_url']}")
        if not row["image_url"].startswith(("https://images.rentals.ca/", "https://rentals.ca/blog/wp-content/", "https://web.archive.org/web/")):
            raise ValueError(f"Unexpected chart URL: {row['image_url']}")
        image = ROOT / "data/raw/rentals/archive" / row["image_file"]
        if image.name != row["image_file"] or not image.is_file() or digest(image) != row["image_sha256"]:
            raise ValueError(f"Chart image missing or hash mismatch: {row['image_file']}")
        value = float(row["value"])
        if not 300 <= value <= 10000:
            raise ValueError(f"Rent outside accepted range: {period} {region}")
        sources[(period, row["report_url"], row["image_url"], row["image_file"])].append((f"regional_asking_{region}_total", period, value))
    for period in {row["period"] for row in rows}:
        if len({(row["report_url"], row["image_url"], row["image_file"]) for row in rows if row["period"] == period}) != 1:
            raise ValueError(f"Multiple chart sources for {period}")
    return sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data/housing.sqlite3")
    parser.add_argument("--transcript", type=Path, default=ROOT / "docs/RENTAL_REGIONAL_ARCHIVE.csv")
    args = parser.parse_args()
    sources = load_rows(args.transcript)
    db = connect(args.database)
    for rows in sources.values():
        for series_id, period, _ in rows:
            existing = db.execute("SELECT 1 FROM observations WHERE series_id=? AND period=? LIMIT 1", (series_id, period)).fetchone()
            if existing:
                raise ValueError(f"Archive import would overwrite an existing observation: {series_id} {period}")
    totals = defaultdict(int)
    for (period, report_url, image_url, image_file), rows in sorted(sources.items()):
        image = ROOT / "data/raw/rentals/archive" / image_file
        transcript = ROOT / "data/manual/rentals-regional-archive" / f"{period}.csv"
        transcript.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        transcript.parent.chmod(0o700)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(("series_id", "period", "value", "chart_sha256"))
        writer.writerows((series_id, period, int(value), digest(image)) for series_id, period, value in rows)
        content = output.getvalue()
        if transcript.exists() and transcript.read_text() != content:
            raise ValueError(f"Existing month transcript differs: {transcript}")
        transcript.write_text(content)
        transcript.chmod(0o600)
        with db:
            register_raw(db, image, "Rentals.ca/Urbanation", image_url, period,
                         "Original regional ranking chart; manually transcribed totals")
        result = ingest(db, "Rentals.ca/Urbanation", transcript, report_url, period,
                        f"Regional archive chart transcription; image SHA-256 {digest(image)}; no missing rows inferred", rows)
        for key, count in result.items():
            totals[key] += count
        print(period, len(rows), result)
    sync_live_manifest(db)
    print("Total", dict(totals))


if __name__ == "__main__":
    main()
