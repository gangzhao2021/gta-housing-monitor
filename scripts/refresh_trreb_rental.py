"""Download and ingest TRREB quarterly condo rental reports not yet stored."""
import fcntl
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from housing.db import connect
from housing.trreb_rental import refresh

if __name__ == "__main__":
    with (ROOT / "data/.refresh-official.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        db = connect(ROOT / "data/housing.sqlite3")
        try:
            print(json.dumps(refresh(db, ROOT)))
        finally:
            db.close()
