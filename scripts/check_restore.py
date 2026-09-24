"""Rehearse a self-contained backup and read it from a different root."""
import csv
import hashlib
import shutil
import sqlite3
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    with tempfile.TemporaryDirectory(prefix="housing-restore-") as scratch:
        restored = Path(scratch)
        (restored / "data").mkdir()
        original = sqlite3.connect(ROOT / "data/housing.sqlite3")
        copy = sqlite3.connect(restored / "data/housing.sqlite3")
        original.backup(copy)
        original.close()
        copy.row_factory = sqlite3.Row
        assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        for folder in ("raw", "manual", "observations"):
            source = ROOT / "data" / folder
            if source.exists():
                shutil.copytree(source, restored / "data" / folder)
        with (restored / "data/raw/manifest.csv").open(newline="") as source:
            entries = list(csv.DictReader(source))
        for entry in entries:
            saved = restored / entry["path"]
            assert saved.is_file(), saved
            assert hashlib.sha256(saved.read_bytes()).hexdigest() == entry["sha256"], saved
        for row in copy.execute("SELECT raw_sha256 FROM observations"):
            assert any(entry["sha256"] == row["raw_sha256"] for entry in entries)
        snapshots = sorted((restored / "data/observations").glob("*.json"))
        if snapshots:
            import json
            record = json.loads(snapshots[-1].read_text())
            assert record["kind"] == "monthly_observation"
            for series_id, detail in record["inputs"].items():
                for observation_id, version in zip(detail["ids"], detail["versions"], strict=True):
                    row = copy.execute("SELECT series_id,period,version,raw_sha256 FROM observations WHERE id=?",
                                       (observation_id,)).fetchone()
                    assert row and row["series_id"] == series_id and row["version"] == version
                    assert row["period"][:7] == detail["source_period"]
                    assert row["raw_sha256"] in detail["raw_sha256"]
            period = record["period"]
            sales = copy.execute("""SELECT value FROM observations WHERE series_id='trreb_sales'
                AND period=? ORDER BY version DESC LIMIT 1""", (period,)).fetchone()
            assert sales and record["values_for_period"]["trreb_sales"] == sales[0]
            stock = record["values_for_period"]["trreb_active_listings"]
            assert abs(record["values_for_period"]["moi_raw"] - stock / sales[0]) < 1e-10
        print(f"restored DB: {copy.execute('SELECT COUNT(*) FROM observations').fetchone()[0]} observations")
        print(f"verified {len(entries)} source files and {len(snapshots)} monthly records")
        copy.close()

if __name__ == "__main__":
    main()
