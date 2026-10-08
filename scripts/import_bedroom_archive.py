"""Import verified Rentals.ca Toronto bedroom-type chart transcriptions (2024-01 to 2025-10).

Before December 2025 the bedroom chart ("Average Asking Rent by Bedroom Type for the
Largest Markets, Purpose-built & Condominium Rental Apartments") was published only as an
image. docs/RENTAL_BEDROOM_ARCHIVE.csv is the audit transcript: every value is backed by a
saved chart image whose SHA-256 is checked before insertion, and existing observations are
never overwritten.
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

ROOMS = {"1br", "2br", "3br"}
FIELDS = {"period", "room", "value", "report_url", "image_url", "image_file", "image_sha256"}
IMAGES = ROOT / "data/raw/rentals/archive/bedrooms"


def load_rows(path):
    with path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        if set(reader.fieldnames or []) != FIELDS:
            raise ValueError("Bedroom transcript columns differ from the required schema")
        rows = list(reader)
    if not rows:
        raise ValueError("Bedroom transcript is empty")
    seen, sources = set(), defaultdict(list)
    for row in rows:
        period, room = row["period"], row["room"]
        if not re.fullmatch(r"202[45]-(0[1-9]|1[0-2])", period) or room not in ROOMS:
            raise ValueError(f"Invalid period or room: {period} {room}")
        if period >= "2025-11" or (period, room) in seen:
            raise ValueError(f"Duplicate or chart-CSV period: {period} {room}")
        seen.add((period, room))
        if not row["report_url"].startswith("https://rentals.ca/blog/"):
            raise ValueError(f"Unexpected report URL: {row['report_url']}")
        if not row["image_url"].startswith(("https://images.rentals.ca/", "https://rentals.ca/blog/wp-content/")):
            raise ValueError(f"Unexpected chart URL: {row['image_url']}")
        image = IMAGES / row["image_file"]
        if image.name != row["image_file"] or not image.is_file() or digest(image) != row["image_sha256"]:
            raise ValueError(f"Chart image missing or hash mismatch: {row['image_file']}")
        value = float(row["value"])
        if not 300 <= value <= 10000:
            raise ValueError(f"Rent outside accepted range: {period} {room}")
        sources[(period, row["report_url"], row["image_url"], row["image_file"])].append((f"toronto_asking_rent_{room}", period, value))
    for period in {row["period"] for row in rows}:
        if len({(row["report_url"], row["image_url"]) for row in rows if row["period"] == period}) != 1:
            raise ValueError(f"Multiple chart sources for {period}")
    return sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data/housing.sqlite3")
    parser.add_argument("--transcript", type=Path, default=ROOT / "docs/RENTAL_BEDROOM_ARCHIVE.csv")
    args = parser.parse_args()
    sources = load_rows(args.transcript)
    db = connect(args.database)
    for rows in sources.values():
        for series_id, period, _ in rows:
            if db.execute("SELECT 1 FROM observations WHERE series_id=? AND period=? LIMIT 1", (series_id, period)).fetchone():
                raise ValueError(f"Archive import would overwrite an existing observation: {series_id} {period}")
    totals = defaultdict(int)
    for (period, report_url, image_url, image_file), rows in sorted(sources.items()):
        image = IMAGES / image_file
        transcript = ROOT / "data/manual/rentals-bedroom-archive" / f"{period}.csv"
        transcript.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(("series_id", "period", "value", "chart_sha256"))
        writer.writerows((series_id, period, int(value), digest(image)) for series_id, period, value in rows)
        if transcript.exists() and transcript.read_text() != output.getvalue():
            raise ValueError(f"Existing month transcript differs: {transcript}")
        transcript.write_text(output.getvalue())
        transcript.chmod(0o600)
        with db:
            register_raw(db, image, "Rentals.ca/Urbanation", image_url, period,
                         "Original bedroom-type chart image; manually transcribed Toronto values")
        result = ingest(db, "Rentals.ca/Urbanation", transcript, report_url, period,
                        f"Bedroom-type chart transcription; image SHA-256 {digest(image)}; no missing values inferred", rows)
        for key, count in result.items():
            totals[key] += count
        print(period, len(rows), result)
    sync_live_manifest(db)
    print("Total", dict(totals))


if __name__ == "__main__":
    main()
