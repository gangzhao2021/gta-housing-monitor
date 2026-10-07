"""Download the latest CBA mortgage arrears workbook and ingest Ontario months not yet stored."""
import fcntl
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from housing.cba_arrears import refresh
from housing.db import connect

if __name__ == "__main__":
    with (ROOT / "data/.refresh-official.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        db = connect(ROOT / "data/housing.sqlite3")
        try:
            print(json.dumps(refresh(db, ROOT)))
        finally:
            db.close()
