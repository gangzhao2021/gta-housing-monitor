import sqlite3
from pathlib import Path
from .catalog import SERIES

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS series (
 id TEXT PRIMARY KEY, label TEXT NOT NULL, source TEXT NOT NULL,
 source_series TEXT NOT NULL, geography TEXT NOT NULL, unit TEXT NOT NULL,
 frequency TEXT NOT NULL, seasonal_adjustment TEXT NOT NULL,
 smoothing TEXT NOT NULL, definition TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS raw_files (
 sha256 TEXT PRIMARY KEY, path TEXT NOT NULL, source TEXT NOT NULL,
 source_url TEXT NOT NULL, retrieved_at TEXT NOT NULL, reference_period TEXT,
 method TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS observations (
 id INTEGER PRIMARY KEY, series_id TEXT NOT NULL REFERENCES series(id),
 period TEXT NOT NULL, value REAL NOT NULL, version INTEGER NOT NULL,
 raw_sha256 TEXT NOT NULL REFERENCES raw_files(sha256),
 first_seen_at TEXT NOT NULL, published_at TEXT, availability_evidence TEXT,
 UNIQUE(series_id,period,version)
);
CREATE TABLE IF NOT EXISTS ingestion_runs (
 id INTEGER PRIMARY KEY, source TEXT NOT NULL, started_at TEXT NOT NULL,
 status TEXT NOT NULL, raw_sha256 TEXT, inserted INTEGER NOT NULL DEFAULT 0,
 unchanged INTEGER NOT NULL DEFAULT 0, revised INTEGER NOT NULL DEFAULT 0,
 error TEXT
);
"""

def connect(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    db.executemany("""INSERT INTO series VALUES (?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET label=excluded.label,
                   source=excluded.source, source_series=excluded.source_series,
                   geography=excluded.geography, unit=excluded.unit,
                   frequency=excluded.frequency, seasonal_adjustment=excluded.seasonal_adjustment,
                   smoothing=excluded.smoothing, definition=excluded.definition""",
                   ((key, *value) for key, value in SERIES.items()))
    db.commit()
    return db

def latest(db, series_id):
    return db.execute("""SELECT o.* FROM observations o JOIN
      (SELECT period, MAX(version) version FROM observations WHERE series_id=? GROUP BY period) x
      ON o.period=x.period AND o.version=x.version WHERE o.series_id=? ORDER BY o.period""",
      (series_id, series_id)).fetchall()
