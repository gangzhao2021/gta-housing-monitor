"""Publish a path-free, latest-value snapshot for the read-only display app."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from housing.publication import publish


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data/housing.sqlite3")
    parser.add_argument("--output", type=Path, default=ROOT / "data/display_snapshot.json")
    args = parser.parse_args()
    output = publish(args.database, args.output)
    print(f"Published display snapshot: {output}")


if __name__ == "__main__":
    main()
