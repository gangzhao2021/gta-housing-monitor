"""Install or remove the owner-only macOS LaunchAgent for official-source checks."""
import argparse
import os
import plistlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABEL = "local.toronto-housing.official-refresh"
AGENT = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"


def definition(root=ROOT):
    root = Path(root).resolve()
    return {
        "Label": LABEL,
        "ProgramArguments": [str(root / ".venv/bin/python"), str(root / "scripts/run_refresh_cycle.py")],
        "WorkingDirectory": str(root),
        "StartCalendarInterval": {"Hour": 9, "Minute": 0},
        "RunAtLoad": False,
        "StandardOutPath": str(root / "data/run_reports/launchd.stdout.log"),
        "StandardErrorPath": str(root / "data/run_reports/launchd.stderr.log"),
    }


def install():
    if not (ROOT / ".venv/bin/python").exists():
        raise FileNotFoundError("Create .venv before installing the schedule")
    reports = ROOT / "data/run_reports"
    reports.mkdir(parents=True, exist_ok=True, mode=0o700)
    reports.chmod(0o700)
    AGENT.parent.mkdir(parents=True, exist_ok=True)
    if AGENT.exists():
        raise FileExistsError(f"Existing LaunchAgent must be removed explicitly: {AGENT}")
    agent_data = plistlib.dumps(definition())
    fd = os.open(AGENT, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(agent_data)
    target = f"gui/{os.getuid()}"
    try:
        subprocess.run(["launchctl", "bootstrap", target, str(AGENT)], check=True)
    except Exception:
        AGENT.unlink(missing_ok=True)
        raise
    return AGENT


def uninstall():
    target = f"gui/{os.getuid()}/{LABEL}"
    subprocess.run(["launchctl", "bootout", target], check=False)
    AGENT.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    command = parser.add_mutually_exclusive_group(required=True)
    command.add_argument("--install", action="store_true")
    command.add_argument("--uninstall", action="store_true")
    command.add_argument("--show", action="store_true")
    args = parser.parse_args()
    if args.install:
        print(install())
    elif args.uninstall:
        uninstall()
        print("removed", AGENT)
    else:
        print(plistlib.dumps(definition()).decode())


if __name__ == "__main__":
    main()
