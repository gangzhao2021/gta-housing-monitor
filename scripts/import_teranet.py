"""Import a manually downloaded Teranet-National Bank House_Price_Index.csv.

Usage: .venv/bin/python scripts/import_teranet.py ~/Downloads/House_Price_Index.csv
The file is copied into data/raw/teranet/ under its SHA-256 before ingest.
"""
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from housing.db import connect
from housing.ingest import ingest
from housing.teranet import SOURCE, URL, parse

if __name__ == "__main__":
    source = Path(sys.argv[1]).expanduser()
    content = source.read_bytes()
    rows = parse(content)
    sha = hashlib.sha256(content).hexdigest()
    folder = ROOT / "data/raw/teranet"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    saved = folder / f"House_Price_Index-{sha[:12]}.csv"
    if not saved.exists():
        shutil.copyfile(source, saved)
        saved.chmod(0o600)
    db = connect(ROOT / "data/housing.sqlite3")
    backup = ROOT / "data/backups" / f"teranet-before-{datetime.now():%Y%m%dT%H%M%S%f}.sqlite3"
    target = sqlite3.connect(backup)
    db.backup(target)
    target.close()
    backup.chmod(0o600)
    periods = sorted({p for _, p, _ in rows})
    result = ingest(db, SOURCE, saved, URL, f"{periods[0]}/{periods[-1]}",
                    "Manual download after accepting Terms of Use; Toronto index, SA index, sales pairs", rows)
    db.close()
    print(json.dumps({"file": saved.name, "rows": len(rows), "first": periods[0], "last": periods[-1], **result}))
