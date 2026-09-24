"""Fetch archived official reports without overwriting a local copy."""
import argparse
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def months(start, end):
    year, month = map(int, start.split("-"))
    final = tuple(map(int, end.split("-")))
    while (year, month) <= final:
        yield year, month
        month += 1
        if month == 13:
            year, month = year + 1, 1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("start")
    parser.add_argument("end")
    args = parser.parse_args()
    folder = ROOT / "data/raw/trreb"
    folder.mkdir(parents=True, exist_ok=True)
    for year, month in months(args.start, args.end):
        name = f"mw{year % 100:02d}{month:02d}.pdf"
        destination = folder / name
        if destination.exists():
            print("already saved", name)
            continue
        url = f"https://trreb.ca/wp-content/files/market-stats/market-watch/{name}"
        temporary = destination.with_suffix(".download")
        command = ["curl", "--fail", "--location", "--silent", "--show-error", "--max-time", "40", url, "-o", str(temporary)]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode:
            temporary.unlink(missing_ok=True)
            print("FAILED", name, completed.stderr.strip())
        else:
            temporary.rename(destination)
            print("saved", name, destination.stat().st_size)
        time.sleep(0.25)

if __name__ == "__main__":
    main()
