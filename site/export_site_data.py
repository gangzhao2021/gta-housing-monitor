"""Export only the approved read-only snapshot for a private Sites deployment."""
import json
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
output = Path(__file__).resolve().parent / "dist/data.json"
temporary = output.with_suffix('.json.tmp')
temporary.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
temporary.replace(output)
print(f"Exported {len(snapshot['observations'])} history series and {len(snapshot.get('context', {}))} context values to {output}")
