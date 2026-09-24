"""Report whether the private database supports a strict point-in-time backtest."""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from housing.research import audit_availability


def main():
    db = sqlite3.connect(f"file:{(ROOT / 'data/housing.sqlite3').resolve()}?mode=ro", uri=True)
    try:
        rows = audit_availability(db)
    finally:
        db.close()
    result = {"strict_backtest_ready": all(row["observations"] and row["published_at_known"] == row["observations"] and row["evidence_known"] == row["observations"] for row in rows), "core_series": rows}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["strict_backtest_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
