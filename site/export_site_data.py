"""Export only the approved read-only snapshot for a private Sites deployment."""
import json
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from housing.catalog import SERIES, SERIES_URLS
from housing.dashboard import LABELS
from housing.i18n import EN
from housing.metric_help import explanation
from housing.publication import CONTEXT_SERIES, DISPLAY_SERIES, load_display_snapshot

snapshot = load_display_snapshot(ROOT / "data/display_snapshot.json")
assert set(snapshot["observations"]) <= DISPLAY_SERIES
assert set(snapshot.get("context", {})) <= CONTEXT_SERIES
fields = sorted(set(snapshot["observations"]) | set(snapshot.get("context", {})))
fields += ["moi_raw", "snlr_raw"]


def translate(text):
    if text in EN:
        return EN[text]
    matcher = re.compile("|".join(re.escape(key) for key in sorted(EN, key=len, reverse=True)))
    return matcher.sub(lambda match: EN[match.group()], text)


metadata = {}
for field in fields:
    source = SERIES.get(field)
    if source is None:
        name = {"moi_raw": "库存月数", "snlr_raw": "成交／新挂牌比"}[field]
        unit = {"moi_raw": "月", "snlr_raw": "%"}[field]
        source_name = "TRREB"
        url = "https://trreb.ca/market-data/market-watch/"
    else:
        name = LABELS.get(field, source[0])
        unit, source_name, url = source[4], source[1], SERIES_URLS.get(field)
    metadata[field] = {
        "zh": name,
        "en": translate(name),
        "unit": unit,
        "source": source_name,
        "geography": source[3] if source else "All TRREB Areas",
        "url": url,
    }
    if details := explanation(field):
        zh, limit_zh, en, limit_en, _ = details
        metadata[field]["help"] = {"zh": [zh, limit_zh], "en": [en, limit_en]}

payload = {"snapshot": snapshot, "series": metadata}
editorial_file = Path(__file__).resolve().parent / "editorial.json"
editorial = json.loads(editorial_file.read_text())
assert isinstance(editorial, dict)
for period, item in editorial.items():
    assert re.fullmatch(r"\d{4}-\d{2}", period), period
    assert set(item) == {"zh", "en", "author", "reviewed_at"}, period
    assert all(isinstance(item[key], str) and item[key].strip() for key in item), period
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", item["reviewed_at"]), period
payload["editorial"] = editorial
boundary_file = Path(__file__).resolve().parent / "municipal_boundaries.geojson"
boundary_bytes = boundary_file.read_bytes()
assert hashlib.sha256(boundary_bytes).hexdigest() == "ccafec64f1a6199c07baee18eae3ddeffa78fdd1e1b37bfc474482a7eeef427e"
boundaries = json.loads(boundary_bytes)
expected_csd = {
    "Toronto": "3520005", "Markham": "3519036", "Vaughan": "3519028",
    "Mississauga": "3521005", "Oakville": "3524001",
    "Richmond Hill": "3519038", "Aurora": "3519046", "Brampton": "3521010",
}
assert boundaries["type"] == "FeatureCollection"
assert {feature["properties"]["CSDNAME"]: feature["properties"]["CSDUID"]
        for feature in boundaries["features"]} == expected_csd
assert all(feature["geometry"]["type"] in ("Polygon", "MultiPolygon")
           for feature in boundaries["features"])
payload["municipal_boundaries"] = boundaries["features"]
# The official all-area row uses the same month and property-type boundary as
# the HPI chart. Keep its source value; do not derive an unweighted district mean.
all_area_average = {
    row["ym"]: row["average_price"]
    for row in snapshot.get("districts", [])
    if row["region"] == "All TRREB Areas"
    and row["house_type"] == "all_types"
    and row.get("average_price") is not None
}
if all_area_average:
    payload["snapshot"]["observations"]["trreb_average_price"] = all_area_average
    payload["series"]["trreb_average_price"] = {
        "zh": "成交均价", "en": "Average sale price", "unit": "CAD",
        "source": "TRREB Market Watch", "geography": "All TRREB Areas",
        "url": "https://trreb.ca/market-data/market-watch/",
        "help": {
            "zh": ["当月全部房型成交价格的平均值。", "会随成交房型和地区构成变化，不等于标准化 HPI 基准价。"],
            "en": ["Mean transaction price across all home types in the month.", "It moves with the mix of sold homes and areas; it is not the standardized HPI benchmark."],
        },
    }
output = Path(__file__).resolve().parent / "dist/data.json"
temporary = output.with_suffix('.json.tmp')
temporary.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
temporary.replace(output)
print(f"Exported {len(snapshot['observations'])} history series and {len(snapshot.get('context', {}))} context values to {output}")
