"""Check and ingest reproducible public API/table sources; no web request runs in the UI.

TRREB PDFs, Rentals.ca charts and CMHC survey editions still require their
source-specific validation paths and are intentionally outside this runner.
"""
import argparse
import fcntl
import hashlib
import os
import sqlite3
import sys
import time
from calendar import monthrange
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from housing.db import connect
from housing.ingest import (ingest, now, parse_boc, parse_statcan,
                            parse_statcan_construction, parse_statcan_population,
                            record_parse_failure)
from housing.manifest import write_manifest
from housing.external_factors import parse_fx, parse_energy, parse_wti, parse_building_cost

CORE_SOURCES = {
    'boc': ('BoC', 'boc', '.json', parse_boc, 'API JSON'),
    'employment': ('StatsCan', 'statcan', '.zip', parse_statcan, 'official CSV ZIP'),
    'construction': ('StatsCan construction', 'statcan', '.zip', parse_statcan_construction, 'official CMHC/StatsCan CSV ZIP'),
    'population': ('StatsCan population', 'statcan', '.zip', parse_statcan_population, 'official CSV ZIP'),
}
FACTOR_SOURCES = {
    'fx': ('BoC FX', 'boc', '.json', parse_fx, 'BoC monthly Valet JSON'),
    'energy': ('BoC BCPI', 'boc', '.json', parse_energy, 'BoC monthly Valet JSON'),
    'wti': ('EIA WTI', 'eia', '.html', parse_wti, 'EIA monthly HTML table'),
    'building_cost': ('StatsCan BCPI', 'statcan', '.zip', parse_building_cost, 'official CSV ZIP'),
}
from housing.background_series import CONFIG as BACKGROUND_CONFIG, refresh_background
FACTOR_SOURCES.update({key: None for key in BACKGROUND_CONFIG if not BACKGROUND_CONFIG[key].get('archived')})
SOURCES = {**CORE_SOURCES, **FACTOR_SOURCES}
TABLES = {'employment': '14100460', 'construction': '34100154', 'population': '17100148'}


def source_url(key, today):
    if key in TABLES:
        return f'https://www150.statcan.gc.ca/n1/en/tbl/csv/{TABLES[key]}-eng.zip'
    if key == 'building_cost':
        return 'https://www150.statcan.gc.ca/n1/en/tbl/csv/18100289-eng.zip'
    if key == 'wti':
        return 'https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=RWTC&f=M'
    complete_month = today.year * 12 + today.month - 2
    year, month = divmod(complete_month, 12)
    end = f'{year:04d}-{month + 1:02d}-{monthrange(year, month + 1)[1]:02d}'
    if key == 'fx':
        return ('https://www.bankofcanada.ca/valet/observations/group/'
                f'FX_RATES_MONTHLY/json?start_date=2022-09-01&end_date={end}')
    if key == 'energy':
        return ('https://www.bankofcanada.ca/valet/observations/group/'
                f'BCPI_MONTHLY/json?start_date=2022-09-01&end_date={end}')
    return ('https://www.bankofcanada.ca/valet/observations/'
            'V39079,BD.CDN.5YR.DQ.YLD,V122667786/json'
            f'?start_date=2022-09-01&end_date={end}')


def fetch(url, temporary, attempts=3):
    """Bounded retry; no partial response is retained as a source snapshot."""
    last_error = None
    for attempt in range(attempts):
        try:
            agent = ('Mozilla/5.0 (compatible; TorontoHousingMonitor/0.1)'
                     if 'eia.gov' in url else 'TorontoHousingMonitor/0.1 (public data research)')
            request = Request(url, headers={'User-Agent': agent})
            with urlopen(request, timeout=90) as response, temporary.open('xb') as output:
                digest = hashlib.sha256()
                size = 0
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > 150 * 1024 * 1024:
                        raise ValueError('Public source exceeds 150 MiB limit')
                    digest.update(chunk)
                    output.write(chunk)
            if not size:
                raise ValueError('Empty public source response')
            return digest.hexdigest()
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(0.5 * 2 ** attempt)
    raise last_error


def backup(db, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    target = sqlite3.connect(destination)
    try:
        db.backup(target)
    finally:
        target.close()


def refresh_one(db, key, root=ROOT, today=None, fetcher=fetch):
    today = today or datetime.now(ZoneInfo('America/Toronto')).date()
    if key in BACKGROUND_CONFIG:
        return refresh_background(db, key, root, today)
    source, folder, suffix, parser, method = SOURCES[key]
    url = source_url(key, today)
    directory = root / 'data/raw' / folder
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / f'.refresh-{key}-{os.getpid()}.download'
    temporary.unlink(missing_ok=True)
    try:
        sha = fetcher(url, temporary)
    except Exception as exc:
        with db:
            db.execute('INSERT INTO ingestion_runs (source,started_at,status,error) VALUES (?,?,?,?)',
                       (source, now(), 'failed', f'download: {exc}'))
        raise
    prior = db.execute('SELECT path,method FROM raw_files WHERE sha256=?', (sha,)).fetchone()
    accepted = prior and not prior['method'].startswith('rejected') and db.execute(
        "SELECT 1 FROM ingestion_runs WHERE raw_sha256=? AND source=? AND status='success' LIMIT 1",
        (sha, source)).fetchone()
    if accepted:
        temporary.unlink(missing_ok=True)
        with db:
            db.execute('INSERT INTO ingestion_runs (source,started_at,status,raw_sha256) VALUES (?,?,?,?)',
                       (source, now(), 'unchanged', sha))
        write_manifest(db, root)
        return {'source': key, 'status': 'unchanged', 'sha256': sha}
    stamp = datetime.now(ZoneInfo('America/Toronto')).strftime('%Y%m%dT%H%M%S%f')
    destination = directory / f'{key}-{stamp}-{sha[:12]}{suffix}'
    temporary.replace(destination)
    try:
        rows = parser(destination)
    except Exception as exc:
        record_parse_failure(db, source, destination, exc, url)
        raise
    if not rows:
        exc = ValueError('Parsed source contains no rows')
        record_parse_failure(db, source, destination, exc, url)
        raise exc
    backup_name = datetime.now(ZoneInfo('America/Toronto')).strftime('%Y%m%dT%H%M%S')
    backup(db, root / 'data/backups' / f'housing-before-{key}-{backup_name}.sqlite3')
    summary = ingest(db, source, destination, url,
                     f'{min(row[1] for row in rows)}/{max(row[1] for row in rows)}', method, rows)
    write_manifest(db, root)
    return {'source': key, 'status': 'success', 'sha256': sha, **summary}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=[*SOURCES, 'core', 'factors', 'all'], default='all')
    args = parser.parse_args()
    lock_path = ROOT / 'data/.refresh-official.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error('Another official-source refresh is already running')
        db = connect(ROOT / 'data/housing.sqlite3')
        failures = 0
        try:
            keys = (list(SOURCES) if args.source == 'all' else
                    list(CORE_SOURCES) if args.source == 'core' else
                    list(FACTOR_SOURCES) if args.source == 'factors' else [args.source])
            for key in keys:
                try:
                    print(refresh_one(db, key), flush=True)
                except Exception as exc:
                    failures += 1
                    print(f'{key}: FAILED: {exc}', file=sys.stderr, flush=True)
        finally:
            db.close()
        return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
