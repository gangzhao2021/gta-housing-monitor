"""Build data/research/trreb-history.csv: board-wide monthly TRREB totals 2004-01 onward.

2004-01..2022-08 come from archived PDFs in data/raw/trreb_history/ (housing.trreb_history);
later months come from the validated district import (All TRREB Areas, all home types).
"""
import csv
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from housing.trreb_history import extract

FIELDS = ["period", "layout", "sales", "new_listings", "active_listings", "average_price", "median_price",
          "dollar_volume", "snlr_trend", "moi_trend", "avg_sp_lp", "avg_pct_list", "avg_dom", "avg_ldom", "avg_pdom",
          "grand_total_differs", "source_pdf", "source_sha256"]


def main():
    rows = []
    year, month = 2004, 1
    while (year, month) <= (2022, 8):
        period = f"{year}-{month:02d}"
        pdf = ROOT / "data/raw/trreb_history" / f"mw{year % 100:02d}{month:02d}.pdf"
        record = extract(pdf, period)
        record["source_sha256"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if record.get("grand_total_differs"):
            record["grand_total_differs"] = json.dumps(record["grand_total_differs"])
        rows.append(record)
        month += 1
        if month == 13:
            year, month = year + 1, 1
    db = sqlite3.connect(f"file:{ROOT / 'data/housing.sqlite3'}?mode=ro", uri=True)
    for ym, values, pdf_sha in db.execute("""SELECT d.ym, d.values_json, d.pdf_sha256 FROM district_observations d JOIN
            (SELECT ym, MAX(version) v FROM district_observations WHERE house_type='all_types' AND region='All TRREB Areas' GROUP BY ym) x
            ON d.ym=x.ym AND d.version=x.v WHERE d.house_type='all_types' AND d.region='All TRREB Areas' ORDER BY d.ym"""):
        v = json.loads(values)
        rows.append({"period": ym, "layout": "district_import_ldom_pdom", **{k: v.get(k) for k in (
            "sales", "new_listings", "active_listings", "average_price", "median_price", "dollar_volume",
            "snlr_trend", "moi_trend", "avg_sp_lp", "avg_ldom", "avg_pdom")}, "source_pdf": f"mw{ym[2:4]}{ym[5:]}.pdf",
            "source_sha256": pdf_sha})
    db.close()
    output = ROOT / "data/research/trreb-history.csv"
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    output.chmod(0o600)
    print("wrote", output, len(rows), rows[0]["period"], rows[-1]["period"])


if __name__ == "__main__":
    main()
