"""Verify the complete private dataset, either in place or from a saved copy."""
import argparse
import csv
import hashlib
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify_dataset(root):
    root = Path(root).resolve()
    data = root / "data"
    db = sqlite3.connect(f"file:{(data / 'housing.sqlite3').resolve()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity check failed")
        if db.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("SQLite foreign key check failed")
        raw = {row["sha256"]: row["path"] for row in db.execute("SELECT sha256,path FROM raw_files")}
        manifest = data / "raw/manifest.csv"
        with manifest.open(newline="", encoding="utf-8") as source:
            entries = list(csv.DictReader(source))
        listed = {row["sha256"]: row["path"] for row in entries}
        if len(listed) != len(entries) or listed != raw:
            raise ValueError("Manifest does not match the database raw-file inventory")
        for sha, name in listed.items():
            path = (root / name).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError(f"Missing or external raw file: {name}")
            if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                raise ValueError(f"Raw-file hash differs: {name}")
        for row in db.execute("SELECT DISTINCT raw_sha256 FROM observations"):
            if row[0] not in listed:
                raise ValueError(f"Observation has no source file: {row[0]}")
        records = sorted((data / "observations").glob("*.json"))
        for path in records:
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("kind") != "monthly_observation":
                raise ValueError(f"Unexpected observation record: {path.name}")
            for series_id, detail in record["inputs"].items():
                ids, versions = detail["ids"], detail["versions"]
                if len(ids) != len(versions) or not ids:
                    raise ValueError(f"Broken observation references: {path.name} {series_id}")
                referenced = []
                for observation_id, version in zip(ids, versions, strict=True):
                    item = db.execute(
                        "SELECT series_id,period,version,raw_sha256,value FROM observations WHERE id=?",
                        (observation_id,)).fetchone()
                    if not item or item["series_id"] != series_id or item["version"] != version:
                        raise ValueError(f"Wrong referenced version: {path.name} {series_id}")
                    if item["period"][:7] != detail["source_period"][:7]:
                        raise ValueError(f"Wrong referenced period: {path.name} {series_id}")
                    referenced.append(item)
                if sorted({item["raw_sha256"] for item in referenced}) != sorted(detail["raw_sha256"]):
                    raise ValueError(f"Wrong referenced raw file: {path.name} {series_id}")
                if len(referenced) == 1 and detail["value"] != referenced[0]["value"]:
                    raise ValueError(f"Wrong saved source value: {path.name} {series_id}")
            values = record["values_for_period"]
            sales, stock = values.get("trreb_sales"), values.get("trreb_active_listings")
            if sales and stock is not None and values.get("moi_raw") is not None:
                if abs(values["moi_raw"] - stock / sales) > 1e-10:
                    raise ValueError(f"Wrong saved MOI: {path.name}")
        return {"observations": db.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
                "source_files": len(entries), "monthly_records": len(records)}
    finally:
        db.close()


def rehearse_current(root=ROOT):
    """Make a temporary complete copy; useful before relying on a saved backup."""
    with tempfile.TemporaryDirectory(prefix="housing-restore-") as scratch:
        restored = Path(scratch)
        data = restored / "data"
        data.mkdir()
        original = sqlite3.connect(f"file:{(Path(root) / 'data/housing.sqlite3').resolve()}?mode=ro", uri=True)
        copy = sqlite3.connect(data / "housing.sqlite3")
        try:
            original.backup(copy)
        finally:
            copy.close()
            original.close()
        for folder in ("raw", "manual", "observations"):
            source = Path(root) / "data" / folder
            if source.exists():
                shutil.copytree(source, data / folder)
        return verify_dataset(restored)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup-dir", type=Path, help="Root containing a saved data/ directory")
    args = parser.parse_args()
    result = verify_dataset(args.backup_dir) if args.backup_dir else rehearse_current()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
