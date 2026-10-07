"""Download long official histories for the v2 leading-indicator study.

Raw responses are kept under data/raw/research/ by SHA-256; a tidy monthly
CSV (series, period, value, source_sha256) is written to data/research/.
These inputs feed research only; dashboard series keep their own windows.
"""
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from housing.background_series import request_json, request_text

WDS = "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromVectorsAndLatestNPeriods"
VALET = "https://www.bankofcanada.ca/valet/observations/{}/json?start_date=1975-01-01"
SOURCES = {
    "mortgage_5y": ("valet", "V80691335"),
    "bond_5y": ("valet", "BD.CDN.5YR.DQ.YLD"),
    "ontario_unemployment": ("wds", 2063949),
    "toronto_nhpi": ("wds", 111955499),
    "canada_epu": ("fred", "CANEPUINDXM"),
}


def save(name, raw):
    sha = hashlib.sha256(raw).hexdigest()
    folder = ROOT / "data/raw/research"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = folder / f"{name}-{sha[:12]}"
    if not path.exists():
        path.write_bytes(raw)
        path.chmod(0o600)
    return sha


def monthly_mean(points):
    groups = defaultdict(list)
    for day, value in points:
        groups[day[:7]].append(value)
    return {period: sum(values) / len(values) for period, values in groups.items()}


def fetch(name, kind, key):
    if kind == "valet":
        document = request_json(VALET.format(key))
        raw = json.dumps(document, sort_keys=True).encode()
        points = [(o["d"], float(o[key]["v"])) for o in document["observations"] if o.get(key, {}).get("v") not in (None, "")]
        return save(name + ".json", raw), monthly_mean(points)
    if kind == "wds":
        document = request_json(WDS, [{"vectorId": key, "latestN": 700}])
        if document[0].get("status") != "SUCCESS":
            raise ValueError(f"WDS request failed for {key}")
        raw = json.dumps(document, sort_keys=True).encode()
        points = document[0]["object"]["vectorDataPoint"]
        values = {p["refPer"][:7]: float(p["value"]) for p in points if p["value"] is not None and p["statusCode"] == 0}
        return save(name + ".json", raw), values
    text = request_text(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={key}")
    lines = text.strip().splitlines()
    if lines[0] != f"observation_date,{key}":
        raise ValueError("FRED header changed")
    values = {d[:7]: float(v) for d, v in (line.split(",") for line in lines[1:]) if v not in ("", ".")}
    return save(name + ".csv", text.encode()), values


def database_series():
    import sqlite3
    db = sqlite3.connect(f"file:{ROOT / 'data/housing.sqlite3'}?mode=ro", uri=True)
    try:
        result = {}
        for name, series_id in (("starts", "toronto_cma_2011_starts"), ("teranet_index_sa", "teranet_toronto_index_sa"),
                                ("teranet_pairs", "teranet_toronto_sales_pairs")):
            rows = db.execute("""SELECT o.period, o.value, o.raw_sha256 FROM observations o JOIN
                (SELECT period, MAX(version) v FROM observations WHERE series_id=? GROUP BY period) x
                ON o.period=x.period AND o.version=x.v WHERE o.series_id=?""", (series_id, series_id)).fetchall()
            result[name] = (rows[0][2] if rows else "", {p: v for p, v, _ in rows})
        return result
    finally:
        db.close()


def main():
    tidy = []
    for name, (kind, key) in SOURCES.items():
        sha, values = fetch(name, kind, key)
        tidy += [(name, period, value, sha) for period, value in sorted(values.items())]
        print(name, min(values), max(values), len(values))
    for name, (sha, values) in database_series().items():
        tidy += [(name, period, value, sha) for period, value in sorted(values.items())]
        print(name, min(values), max(values), len(values))
    output = ROOT / "data/research/v2-inputs.csv"
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with output.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["series", "period", "value", "source_sha256"])
        writer.writerows(tidy)
    output.chmod(0o600)
    print("wrote", output, len(tidy))


if __name__ == "__main__":
    main()
