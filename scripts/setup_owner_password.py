"""Create a local owner password verifier without storing the password."""
import argparse
import getpass
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from housing.owner_auth import make_verifier


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-demo", action="store_true",
                        help="Allow a six-character password for loopback-only personal demos")
    args = parser.parse_args()
    password = getpass.getpass("New owner password: ")
    repeated = getpass.getpass("Repeat owner password: ")
    minimum = 6 if args.local_demo else 16
    if password != repeated or len(password) < minimum:
        raise SystemExit(f"Passwords differ or are shorter than {minimum} characters")
    target = ROOT / ".streamlit/owner_auth.env"
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write("HOUSING_OWNER_VERIFIER='" + make_verifier(password) + "'\n")
    print(f"Owner verifier saved with user-only permissions: {target}")


if __name__ == "__main__":
    main()
