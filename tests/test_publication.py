import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from streamlit.testing.v1 import AppTest

from housing.db import connect
from housing.owner_auth import make_verifier, verify
from housing.publication import build_display_snapshot, load_display_snapshot, monthly_display, publish
from housing.research import as_known_at


class PublicationTests(unittest.TestCase):
    def test_display_app_has_no_management_or_download_surface(self):
        root = Path(__file__).resolve().parents[1]
        app = AppTest.from_file(str(root / "viewer_app.py"), default_timeout=20).run()
        self.assertFalse(list(app.exception))
        self.assertNotIn("数据与记录", app.radio(key="navigation").options)
        self.assertEqual(len(app.get("button")), 0)
        self.assertEqual(len(app.get("arrow_vega_lite_chart")) > 0, True)

    def test_snapshot_excludes_private_provenance_and_survives_failed_publish(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            db = connect(root / "private.sqlite3")
            db.execute("INSERT INTO raw_files VALUES (?,?,?,?,?,?,?)", ("secret-hash", "/private/secret.csv", "test", "https://example.test", "2026-09-01", "2026-08", "manual"))
            db.execute("INSERT INTO observations (series_id,period,value,version,raw_sha256,first_seen_at) VALUES (?,?,?,?,?,?)", ("trreb_sales", "2026-08", 1234, 1, "secret-hash", "2026-09-01"))
            db.commit()
            db.close()
            output = publish(root / "private.sqlite3", root / "display.json")
            raw = output.read_text()
            self.assertNotIn("secret-hash", raw)
            self.assertNotIn("/private/", raw)
            self.assertNotIn("raw_files", raw)
            self.assertEqual(load_display_snapshot(output)["observations"]["trreb_sales"]["2026-08"], 1234)
            with self.assertRaises(sqlite3.OperationalError):
                publish(root / "missing.sqlite3", output)
            self.assertEqual(json.loads(output.read_text())["observations"]["trreb_sales"]["2026-08"], 1234)

    def test_monthly_display_uses_only_snapshot_values(self):
        source = {"schema_version": 1, "created_at": "2026-09-01T00:00:00Z", "observations": {
            "trreb_sales": {"2026-08": 100}, "trreb_new_listings": {"2026-08": 200},
            "trreb_active_listings": {"2026-08": 300}}}
        self.assertEqual(monthly_display(source)["2026-08"]["snlr_raw"], 50)

    def test_point_in_time_rejects_unknown_and_future_versions(self):
        with tempfile.TemporaryDirectory() as folder:
            db = connect(Path(folder) / "research.sqlite3")
            db.execute("INSERT INTO raw_files VALUES (?,?,?,?,?,?,?)", ("hash", "x", "test", "url", "2026-09-01", "2026-08", "manual"))
            db.execute("INSERT INTO observations (series_id,period,value,version,raw_sha256,first_seen_at) VALUES (?,?,?,?,?,?)", ("trreb_sales", "2026-08", 100, 1, "hash", "2026-09-01"))
            cutoff = datetime(2026, 9, 15, tzinfo=timezone.utc)
            self.assertIsNone(as_known_at(db, "trreb_sales", "2026-08", cutoff))
            db.execute("UPDATE observations SET published_at=?,availability_evidence=?", ("2026-09-10T00:00:00+00:00", "official archive"))
            self.assertEqual(as_known_at(db, "trreb_sales", "2026-08", cutoff)["value"], 100)
            db.execute("INSERT INTO observations (series_id,period,value,version,raw_sha256,first_seen_at,published_at,availability_evidence) VALUES (?,?,?,?,?,?,?,?)", ("trreb_sales", "2026-08", 101, 2, "hash", "2026-10-01", "2026-10-01T00:00:00+00:00", "official revision"))
            self.assertEqual(as_known_at(db, "trreb_sales", "2026-08", cutoff)["value"], 100)
            db.close()

    def test_owner_verifier(self):
        token = make_verifier("a sufficiently long password")
        self.assertTrue(verify("a sufficiently long password", token))
        self.assertFalse(verify("wrong", token))
