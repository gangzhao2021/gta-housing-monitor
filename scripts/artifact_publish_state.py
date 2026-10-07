"""Decide whether the Claude Artifact copy of site/dist needs republishing.

--check prints JSON with "changed" and the current file hashes; --record saves
them after a successful publish. Only files the Artifact serves are compared.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ("site/artifact/gta-housing-monitor.html", "site/dist/app.js", "site/dist/styles.css", "site/dist/data.json")
STATE = ROOT / "data/run_reports/artifact-publish-state.json"
URL = "https://claude.ai/artifact/6kMnQMgJdnwbPuiMC4taXK"


def hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in FILES}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--record", metavar="VERSION")
    args = parser.parse_args()
    current = hashes()
    if args.check:
        previous = json.loads(STATE.read_text())["hashes"] if STATE.exists() else {}
        snapshot = json.loads((ROOT / "site/dist/data.json").read_text())["snapshot"]["created_at"]
        print(json.dumps({"changed": current != previous, "url": URL, "snapshot_created_at": snapshot,
                          "changed_files": [n for n in FILES if current[n] != previous.get(n)]}))
    else:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps({"url": URL, "version": args.record, "hashes": current,
                                     "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}, indent=2))
        STATE.chmod(0o600)
        print("recorded", args.record)


if __name__ == "__main__":
    main()
