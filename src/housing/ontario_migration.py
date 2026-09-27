"""Verified Ontario quarterly migration components from two StatCan tables."""
import csv
import hashlib
import io
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

from .ingest import ingest, register_raw, validate_rows
from .manifest import write_manifest

SOURCE = "StatsCan Ontario migration"
START = "2022-07"
TABLES = {
    "interprovincial": {
        "number": "17100020", "column": "Interprovincial migration",
        "components": {"In-migrants": ("v509048", "7.1"), "Out-migrants": ("v509063", "7.2")},
    },
    "international": {
        "number": "17100040", "column": "Components of population growth",
        "components": {
            "Immigrants": ("v29850372", "7.1"), "Net non-permanent residents": ("v29850376", "7.5"),
            "Net emigration": ("v1566834794", "7.6"),
        },
    },
}


def table_url(table):
    return f'https://www150.statcan.gc.ca/n1/tbl/csv/{TABLES[table]["number"]}-eng.zip'


def fetch(url):
    request = Request(url, headers={"User-Agent": "TorontoHousingMonitor/0.1 (public data research)"})
    with urlopen(request, timeout=90) as response:
        content = response.read(10 * 1024 * 1024 + 1)
    if not content.startswith(b"PK") or len(content) > 10 * 1024 * 1024:
        raise ValueError("Unexpected StatCan ZIP response")
    return content


def parse_table(content, table):
    config = TABLES[table]
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        expected = config["number"] + ".csv"
        if expected not in archive.namelist():
            raise ValueError(f"Missing official {expected}")
        with archive.open(expected) as source:
            reader = csv.DictReader(io.TextIOWrapper(source, encoding="utf-8-sig", newline=""))
            required = {"REF_DATE", "GEO", "DGUID", config["column"], "UOM", "SCALAR_FACTOR",
                        "VECTOR", "VALUE", "STATUS", "COORDINATE"}
            if not required <= set(reader.fieldnames or ()):
                raise ValueError("StatCan migration table schema changed")
            result = {}
            for row in reader:
                if row["GEO"] != "Ontario" or row["REF_DATE"] < START:
                    continue
                component = row[config["column"]]
                if component not in config["components"]:
                    continue
                period = row["REF_DATE"]
                datetime.strptime(period + "-01", "%Y-%m-%d")
                if period[5:] not in ("01", "04", "07", "10"):
                    raise ValueError(f"Non-quarterly migration period: {period}")
                if (row["DGUID"] != "2021A000235" or row["UOM"] != "Persons"
                        or row["SCALAR_FACTOR"] != "units"
                        or (row["VECTOR"], row["COORDINATE"]) != config["components"][component]
                        or row["STATUS"] or not row["VALUE"]):
                    raise ValueError(f"Ontario migration definition or value changed: {period} {component}")
                bucket = result.setdefault(period, {})
                if component in bucket:
                    raise ValueError(f"Duplicate Ontario migration component: {period} {component}")
                bucket[component] = float(row["VALUE"])
    if not result or any(set(bucket) != set(config["components"]) for bucket in result.values()):
        raise ValueError(f"Incomplete Ontario {table} component set")
    return result


def derive_rows(interprovincial, international):
    if set(interprovincial) != set(international):
        raise ValueError("Ontario migration tables have different quarterly coverage")
    rows = []
    for period in sorted(interprovincial):
        p = interprovincial[period]
        i = international[period]
        rows.append(("ontario_net_interprovincial_migration", period,
                     p["In-migrants"] - p["Out-migrants"]))
        rows.append(("ontario_net_international_migration", period,
                     i["Immigrants"] + i["Net non-permanent residents"] - i["Net emigration"]))
    validate_rows(rows)
    return rows


def refresh_migration(db, root, fetcher=fetch):
    root = Path(root)
    source_dir = root / "data/raw/statcan"
    manual_dir = root / "data/manual"
    source_dir.mkdir(parents=True, exist_ok=True)
    manual_dir.mkdir(parents=True, exist_ok=True)
    documents = {}
    hashes = {}
    for table in TABLES:
        content = fetcher(table_url(table))
        sha = hashlib.sha256(content).hexdigest()
        path = source_dir / f"{TABLES[table]['number']}-{sha[:12]}.zip"
        if not path.exists():
            path.write_bytes(content)
        elif hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError("Existing migration source hash mismatch")
        documents[table] = parse_table(content, table)
        hashes[table] = (sha, path)
    rows = derive_rows(documents["interprovincial"], documents["international"])
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["series_id", "period", "value", "interprovincial_sha256", "international_sha256"])
    writer.writerows((*row, hashes["interprovincial"][0], hashes["international"][0]) for row in rows)
    content = buffer.getvalue().encode("utf-8")
    sha = hashlib.sha256(content).hexdigest()
    path = manual_dir / f"statcan-ontario-migration-{sha[:12]}.csv"
    if not path.exists():
        path.write_bytes(content)
    elif hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        raise ValueError("Existing derived migration CSV hash mismatch")
    prior = db.execute("""SELECT 1 FROM ingestion_runs WHERE source=? AND status='success'
                        AND raw_sha256=? LIMIT 1""", (SOURCE, sha)).fetchone()
    if prior:
        return {"source": SOURCE, "status": "unchanged", "periods": len(rows) // 2}
    backup = root / "data/backups" / f"ontario-migration-before-{datetime.now().strftime('%Y%m%dT%H%M%S%f')}.sqlite3"
    backup.parent.mkdir(parents=True, exist_ok=True)
    target = sqlite3.connect(backup)
    try:
        db.backup(target)
    finally:
        target.close()
    backup.chmod(0o600)
    with db:
        for table, (_, raw_path) in hashes.items():
            register_raw(db, raw_path, SOURCE, table_url(table),
                         f"{rows[0][1]}/{rows[-1][1]}", "official quarterly CSV ZIP")
    result = ingest(db, SOURCE, path, table_url("international"),
                    f"{rows[0][1]}/{rows[-1][1]}",
                    "verified Ontario components; official formulas; no historical vintage inference", rows)
    write_manifest(db, root)
    return {"source": SOURCE, "status": "success", "periods": len(rows) // 2, "csv": str(path), **result}
