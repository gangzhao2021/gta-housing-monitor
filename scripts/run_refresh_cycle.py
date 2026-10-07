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


def _run(runner, root, script, *args, timeout=900):
    return runner([sys.executable, str(root / script), *args],
                  cwd=root, capture_output=True, text=True, timeout=timeout)


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
            try:
                refresh = _run(runner, root, "scripts/refresh_official.py", "--source", "core")
                report.update({"refresh_exit_code": refresh.returncode,
                               "refresh_stdout": refresh.stdout[-4000:], "refresh_stderr": refresh.stderr[-4000:]})
                if refresh.returncode == 0:
                    report["recovery_check"] = verify_dataset(root)
                    trreb = _run(runner, root, "scripts/refresh_trreb.py")
                    report.update(trreb_exit_code=trreb.returncode, trreb_stdout=trreb.stdout[-4000:],
                                  trreb_stderr=trreb.stderr[-4000:])
                    if trreb.returncode:
                        raise RuntimeError("TRREB refresh failed; retaining the last published snapshot")
                    report['trreb_recovery_check'] = verify_dataset(root)
                    publish = _run(runner, root, "scripts/publish_display.py")
                    report["publish_exit_code"] = publish.returncode
                    report["snapshot_published"] = publish.returncode == 0
                    if publish.returncode:
                        report["publish_error"] = publish.stderr[-4000:]
            except Exception as exc:
                report["error"] = f"{type(exc).__name__}: {exc}"
            # Context sources only write the owner database, so a core or TRREB
            # failure must not stop them. They reach the display only after a
            # verified core publication, and their failure never rolls one back.
            try:
                factors = _run(runner, root, "scripts/refresh_official.py", "--source", "factors")
                report.update({"factors_exit_code": factors.returncode,
                               "factors_stdout": factors.stdout[-4000:],
                               "factors_stderr": factors.stderr[-4000:]})
                rental = _run(runner, root, "scripts/refresh_trreb_rental.py")
                report.update(rental_exit_code=rental.returncode, rental_stdout=rental.stdout[-4000:],
                              rental_stderr=rental.stderr[-4000:])
                report["factor_recovery_check"] = verify_dataset(root)
                if report["snapshot_published"]:
                    if factors.returncode == 0:
                        context_publish = _run(runner, root, "scripts/publish_display.py")
                        report["context_publish_exit_code"] = context_publish.returncode
                        if context_publish.returncode:
                            report["context_publish_error"] = context_publish.stderr[-4000:]
                    export = _run(runner, root, "site/export_site_data.py", timeout=120)
                    report.update(site_export_exit_code=export.returncode,
                                  site_export_error=export.stderr[-4000:],
                                  site_deployment='not_deployed_local_export_only')
            except Exception as exc:
                report["context_error"] = f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        report["completed_at"] = _stamp()
        report["report_path"] = str(_write_report(data, report))
    return report


def succeeded(result):
    return bool(result["snapshot_published"] and result.get("factors_exit_code") == 0
                and result.get("rental_exit_code") == 0 and result.get("context_publish_exit_code") == 0
                and result.get('trreb_exit_code') == 0 and result.get('site_export_exit_code') == 0)


def notify(result):
    """Best-effort macOS notification so a failed scheduled run is not silent."""
    problem = result.get("error") or result.get("context_error") or "部分步骤未成功"
    message = f"更新未完成：{problem}"[:200] + f"。报告：{Path(result['report_path']).name}"
    script = f'display notification {json.dumps(message, ensure_ascii=False)} with title "Toronto Housing 数据更新"'
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        pass


if __name__ == "__main__":
    result = run_cycle()
    print(json.dumps(result, ensure_ascii=False))
    if not succeeded(result):
        notify(result)
    raise SystemExit(0 if succeeded(result) else 1)
