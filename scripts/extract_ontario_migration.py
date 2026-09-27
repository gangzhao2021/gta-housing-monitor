"""Refresh verified Ontario quarterly migration background series."""
import fcntl
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from housing.db import connect
from housing.ontario_migration import refresh_migration

if __name__ == "__main__":
    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    with (ROOT / "data/.refresh-official.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        db = connect(ROOT / "data/housing.sqlite3")
        try:
            print(json.dumps(refresh_migration(db, ROOT), ensure_ascii=False))
        finally:
            db.close()
