"""Create and verify a persistent owner-controlled copy of the private data."""
import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.check_restore import verify_dataset


def backup(destination, root=ROOT):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    if destination == root or destination.is_relative_to(root):
        raise ValueError("Choose a backup directory outside the project")
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    data = destination / "data"
    data.mkdir(mode=0o700)
    try:
        original = sqlite3.connect(f"file:{(root / 'data/housing.sqlite3').resolve()}?mode=ro", uri=True)
        copy = sqlite3.connect(data / "housing.sqlite3")
        try:
            original.backup(copy)
        finally:
            copy.close()
            original.close()
        for folder in ("raw", "manual", "observations", "display_history", "run_reports", "backups"):
            source = root / "data" / folder
            if source.exists():
                shutil.copytree(source, data / folder)
        if (root / "data/display_snapshot.json").exists():
            shutil.copy2(root / "data/display_snapshot.json", data / "display_snapshot.json")
        for folder in ("src", "scripts", "docs", "design", "tests"):
            shutil.copytree(root / folder, destination / folder,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in ("app.py", "viewer_app.py", "README.md", "HANDOFF.md",
                     "requirements.lock", "requirements.txt"):
            shutil.copy2(root / name, destination / name)
        (destination / ".streamlit").mkdir(mode=0o700)
        shutil.copy2(root / ".streamlit/config.toml", destination / ".streamlit/config.toml")
        summary = verify_dataset(destination)
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                                  capture_output=True, text=True, check=False)
        (destination / "CODE_REVISION.txt").write_text(
            (revision.stdout.strip() if revision.returncode == 0 else "Git revision unavailable") + "\n",
            encoding="utf-8")
        (destination / "CODE_REVISION.txt").chmod(0o600)
        for path in destination.rglob("*"):
            path.chmod(0o700 if path.is_dir() else 0o600)
        return summary
    except Exception:
        shutil.rmtree(destination)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-parent", type=Path, required=True,
                        help="Existing private directory outside this project")
    args = parser.parse_args()
    stamp = datetime.now(ZoneInfo("America/Toronto")).strftime("%Y%m%dT%H%M%S%f")
    destination = args.output_parent / f"housing-backup-{stamp}"
    old_umask = os.umask(0o077)
    try:
        print(destination, backup(destination))
    finally:
        os.umask(old_umask)


if __name__ == "__main__":
    main()
