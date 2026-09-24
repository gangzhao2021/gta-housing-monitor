"""List or restore validated local display snapshots by full SHA-256 id."""
import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from housing.publication import load_display_snapshot, restore_display_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--list", action="store_true")
    action.add_argument("--restore", metavar="SHA256")
    args = parser.parse_args()
    output = ROOT / "data/display_snapshot.json"
    if args.list:
        for path in sorted((output.parent / "display_history").glob("*.json")):
            if hashlib.sha256(path.read_bytes()).hexdigest() != path.stem:
                continue
            try:
                snapshot = load_display_snapshot(path)
            except (ValueError, OSError):
                continue
            print(path.stem, snapshot["created_at"])
    else:
        print("Restored:", restore_display_snapshot(output, args.restore))


if __name__ == "__main__":
    main()
