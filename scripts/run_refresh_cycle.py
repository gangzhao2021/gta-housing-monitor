"""Refresh official sources; publish only after data and recovery checks pass."""
import fcntl
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.check_restore import verify_dataset


def _stamp():
    return datetime.now(ZoneInfo("America/Toronto")).isoformat(timespec="seconds")


def _write_report(data, report):
    reports = data / "run_reports"
    reports.mkdir(exist_ok=True)
    reports.chmod(0o700)
    name = datetime.now(ZoneInfo("America/Toronto")).strftime("official-%Y%m%dT%H%M%S%f.json")
    path = reports / name
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
    return path


def run_cycle(root=ROOT, runner=subprocess.run):
    root = Path(root)
    data = root / "data"
    data.mkdir(exist_ok=True)
    data.chmod(0o700)
    report = {"started_at": _stamp(), "snapshot_published": False}
    try:
        with (data / ".refresh-cycle.lock").open("w") as lock:
            lock_path = data / ".refresh-cycle.lock"
            lock_path.chmod(0o600)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            refresh = runner([sys.executable, str(root / "scripts/refresh_official.py"), "--source", "core"],
                             cwd=root, capture_output=True, text=True, timeout=900)
            report.update({"refresh_exit_code": refresh.returncode,
                           "refresh_stdout": refresh.stdout[-4000:], "refresh_stderr": refresh.stderr[-4000:]})
            if refresh.returncode == 0:
                report["recovery_check"] = verify_dataset(root)
                trreb = runner([sys.executable, str(root / 'scripts/refresh_trreb.py')],
                               cwd=root, capture_output=True, text=True, timeout=900)
                report.update(trreb_exit_code=trreb.returncode, trreb_stdout=trreb.stdout[-4000:],
                              trreb_stderr=trreb.stderr[-4000:])
                report['trreb_recovery_check'] = verify_dataset(root)
                publish = runner([sys.executable, str(root / "scripts/publish_display.py")],
                                 cwd=root, capture_output=True, text=True, timeout=900)
                report["publish_exit_code"] = publish.returncode
                report["snapshot_published"] = publish.returncode == 0
                if publish.returncode:
                    report["publish_error"] = publish.stderr[-4000:]
                if report["snapshot_published"]:
                    factors = runner([sys.executable, str(root / "scripts/refresh_official.py"),
                                      "--source", "factors"],
                                     cwd=root, capture_output=True, text=True, timeout=900)
                    report.update({"factors_exit_code": factors.returncode,
                                   "factors_stdout": factors.stdout[-4000:],
                                   "factors_stderr": factors.stderr[-4000:]})
                    # These context series stay in the owner database. A factor
                    # failure must not roll back a verified core display update.
                    report["factor_recovery_check"] = verify_dataset(root)
                    if factors.returncode == 0:
                        context_publish = runner([sys.executable, str(root / "scripts/publish_display.py")],
                                                 cwd=root, capture_output=True, text=True, timeout=900)
                        report["context_publish_exit_code"] = context_publish.returncode
                        if context_publish.returncode:
                            report["context_publish_error"] = context_publish.stderr[-4000:]
                    export = runner([sys.executable, str(root / 'site/export_site_data.py')],
                                    cwd=root, capture_output=True, text=True, timeout=120)
                    report.update(site_export_exit_code=export.returncode,
                                  site_export_error=export.stderr[-4000:],
                                  site_deployment='not_deployed_local_export_only')
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        report["completed_at"] = _stamp()
        report["report_path"] = str(_write_report(data, report))
    return report


if __name__ == "__main__":
    result = run_cycle()
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["snapshot_published"] and result.get("factors_exit_code") == 0
                     and result.get("context_publish_exit_code") == 0
                     and result.get('trreb_exit_code') == 0 and result.get('site_export_exit_code') == 0 else 1)
