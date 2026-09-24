"""Run verified official refreshes and publish only after a healthy complete cycle."""
import fcntl
import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def run_cycle(root=ROOT, runner=subprocess.run):
    data = root / "data"
    data.mkdir(exist_ok=True)
    data.chmod(0o700)
    with (data / ".refresh-cycle.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        started = datetime.now(ZoneInfo("America/Toronto")).isoformat(timespec="seconds")
        refresh = runner([sys.executable, str(root / "scripts/refresh_official.py"), "--source", "all"],
                         cwd=root, capture_output=True, text=True)
        report = {"started_at": started, "refresh_exit_code": refresh.returncode,
                  "refresh_stdout": refresh.stdout[-4000:], "refresh_stderr": refresh.stderr[-4000:],
                  "snapshot_published": False}
        if refresh.returncode == 0:
            db = sqlite3.connect(f"file:{(data / 'housing.sqlite3').resolve()}?mode=ro", uri=True)
            try:
                health = db.execute("PRAGMA integrity_check").fetchone()[0]
                report["integrity_check"] = health
            finally:
                db.close()
            if health == "ok":
                publish = runner([sys.executable, str(root / "scripts/publish_display.py")],
                                 cwd=root, capture_output=True, text=True)
                report["publish_exit_code"] = publish.returncode
                report["snapshot_published"] = publish.returncode == 0
                if publish.returncode:
                    report["publish_error"] = publish.stderr[-4000:]
        report["completed_at"] = datetime.now(ZoneInfo("America/Toronto")).isoformat(timespec="seconds")
        reports = data / "run_reports"
        reports.mkdir(exist_ok=True)
        reports.chmod(0o700)
        stamp = datetime.now(ZoneInfo("America/Toronto")).strftime("%Y%m%dT%H%M%S%f")
        (reports / f"official-{stamp}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        return report


if __name__ == "__main__":
    result = run_cycle()
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["snapshot_published"] else 1)
