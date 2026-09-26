"""Import a validated district CSV without altering headline observations."""
import argparse
import fcntl
import sys
import sqlite3
from datetime import datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from housing.db import connect
from housing.districts import import_csv

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    args = parser.parse_args()
    with (ROOT / 'data/.refresh-official.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        db = connect(ROOT / 'data/housing.sqlite3')
        try:
            backup = ROOT / 'data/backups' / ('districts-before-' + datetime.now().strftime('%Y%m%dT%H%M%S%f') + '.sqlite3')
            backup.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(backup) as target:
                db.backup(target)
            backup.chmod(0o600)
            print(import_csv(db, args.csv, ROOT))
        finally:
            db.close()
