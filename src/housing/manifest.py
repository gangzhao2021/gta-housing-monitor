"""Write the recoverable raw-file inventory after an import or rejection."""
import csv
import os
from pathlib import Path

HEADER = ("source", "source_url", "retrieved_at", "reference_period", "path", "sha256", "method")


def write_manifest(db, root):
    root = Path(root).resolve()
    target = root / "data/raw/manifest.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as output:
            writer = csv.writer(output)
            writer.writerow(HEADER)
            for row in db.execute("SELECT * FROM raw_files ORDER BY retrieved_at,source,sha256"):
                saved = Path(row["path"])
                if saved.is_absolute():
                    saved = saved.relative_to(root)
                writer.writerow([row["source"], row["source_url"], row["retrieved_at"],
                                 row["reference_period"], str(saved), row["sha256"], row["method"]])
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target
