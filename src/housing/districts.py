"""Versioned TRREB district observations, separate from headline series."""
import csv
import hashlib
import json
from pathlib import Path
from .ingest import register_raw, sync_live_manifest

FIELDS = ('sales', 'dollar_volume', 'average_price', 'median_price', 'new_listings',
          'snlr_trend', 'active_listings', 'moi_trend', 'avg_sp_lp', 'avg_ldom', 'avg_pdom')
TYPES = ('all_types', 'detached', 'semi_detached', 'townhouse', 'condo_townhouse',
         'condo_apartment', 'link', 'coop_apartment', 'detached_condo', 'coownership_apartment')
SCHEMA = '''CREATE TABLE IF NOT EXISTS district_observations (
 ym TEXT NOT NULL, house_type TEXT NOT NULL, region TEXT NOT NULL, version INTEGER NOT NULL,
 values_json TEXT NOT NULL, raw_sha256 TEXT NOT NULL REFERENCES raw_files(sha256),
 pdf_sha256 TEXT NOT NULL REFERENCES raw_files(sha256),
 PRIMARY KEY(ym,house_type,region,version));'''


def import_csv(db, path, root):
    from datetime import datetime
    db.executescript(SCHEMA)
    with Path(path).open(newline='') as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != ['ym', 'house_type', 'region', *FIELDS, 'source_pdf', 'source_pdf_sha256']:
            raise ValueError('Unexpected district CSV schema')
        rows = list(reader)
    seen = set()
    hashes = {}
    prepared = []
    for row in rows:
        datetime.strptime(row['ym'], '%Y-%m')
        key = (row['ym'], row['house_type'], row['region'])
        if key in seen or row['house_type'] not in TYPES or not row['region']:
            raise ValueError('Duplicate or invalid district identity')
        seen.add(key)
        name = row['source_pdf']
        if Path(name).name != name or name != 'mw' + row['ym'][2:4] + row['ym'][5:] + '.pdf':
            raise ValueError('PDF period or path mismatch')
        pdf = Path(root) / 'data/raw/trreb' / name
        if name not in hashes:
            hashes[name] = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if hashes[name] != row['source_pdf_sha256']:
            raise ValueError('District source PDF hash mismatch')
        values = {k: float(row[k]) if row[k] else None for k in FIELDS}
        import math
        if any(v is not None and (not math.isfinite(v) or v < 0) for v in values.values()):
            raise ValueError('Invalid district value')
        if values['sales'] is None or values['sales'] != int(values['sales']):
            raise ValueError('Invalid district sales')
        prepared.append((key, json.dumps(values, sort_keys=True), row, pdf))
    if not prepared:
        raise ValueError('Empty district export')
    added = 0
    with db:
        sha = register_raw(db, path, 'TRREB districts', 'https://trreb.ca/market-data/market-watch/market-watch-archive/',
                           f'{min(k[0] for k in seen)}/{max(k[0] for k in seen)}', 'validated district CSV')
        for key, values, row, pdf in prepared:
            pdf_sha = row['source_pdf_sha256']
            if not db.execute('SELECT 1 FROM raw_files WHERE sha256=?', (pdf_sha,)).fetchone():
                register_raw(db, pdf, 'TRREB', 'https://trreb.ca/wp-content/files/market-stats/market-watch/' + pdf.name,
                             key[0], 'official PDF')
            old = db.execute('SELECT values_json,version FROM district_observations WHERE ym=? AND house_type=? AND region=? ORDER BY version DESC LIMIT 1', key).fetchone()
            if old and old[0] == values:
                continue
            if db.execute('SELECT 1 FROM district_observations WHERE ym=? AND house_type=? AND region=? AND raw_sha256=?', (*key, sha)).fetchone():
                raise ValueError('Stale district source replay')
            db.execute('INSERT INTO district_observations VALUES(?,?,?,?,?,?,?)',
                       (*key, old[1]+1 if old else 1, values, sha, pdf_sha))
            added += 1
    sync_live_manifest(db)
    return {'rows': len(rows), 'inserted': added}


def display_rows(db):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='district_observations'").fetchone():
        return []
    rows = db.execute('''SELECT d.* FROM district_observations d JOIN
        (SELECT ym,house_type,region,MAX(version) version FROM district_observations GROUP BY ym,house_type,region) x
        USING(ym,house_type,region,version) ORDER BY ym,house_type,region''')
    return [{'ym': r['ym'], 'house_type': r['house_type'], 'region': r['region'], **json.loads(r['values_json'])} for r in rows]
