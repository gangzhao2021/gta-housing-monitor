"""Store TRREB's published YoY and price-band sales for every saved Market Watch report (idempotent)."""
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from housing.breakdowns import trreb_hpi_breakdown
from housing.db import connect
from housing.ingest import ingest
from housing.trreb_price_bands import rows_for as band_rows
from housing.trreb_yoy import rows_for

if __name__ == "__main__":
    db = connect(ROOT / "data/housing.sqlite3")
    backup = ROOT / "data/backups" / f"trreb-yoy-before-{datetime.now():%Y%m%dT%H%M%S%f}.sqlite3"
    target = sqlite3.connect(backup)
    db.backup(target)
    target.close()
    backup.chmod(0o600)
    totals = {}
    for pdf in sorted((ROOT / "data/raw/trreb").glob("mw*.pdf")):
        period = f"20{pdf.stem[2:4]}-{pdf.stem[4:6]}"
        stored = dict(db.execute("SELECT series_id, value FROM observations WHERE period=? AND series_id IN "
                                 "('trreb_sales','trreb_new_listings','trreb_active_listings')", (period,)).fetchall())
        if len(stored) != 3:
            continue
        rows = rows_for(pdf, period, stored, trreb_hpi_breakdown(pdf)) + band_rows(pdf, period, int(stored["trreb_sales"]))
        url = "https://trreb.ca/wp-content/files/market-stats/market-watch/" + pdf.name
        result = ingest(db, "TRREB", pdf, url, period, "published YoY from front page and HPI page; checked against printed amounts", rows)
        for key, count in result.items():
            totals[key] = totals.get(key, 0) + count
    db.close()
    print(json.dumps(totals))
