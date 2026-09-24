import json
import hashlib
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

from housing.db import connect
from housing.owner_auth import make_verifier, verify, session_valid, SESSION_SECONDS
from housing.publication import build_display_snapshot, load_display_snapshot, monthly_display, publish, restore_display_snapshot
from housing.research import as_known_at


class PublicationTests(unittest.TestCase):
    def test_owner_app_stops_before_database_without_verifier(self):
        root = Path(__file__).resolve().parents[1]
        with patch.dict("os.environ", {"HOUSING_REQUIRE_OWNER_AUTH": "1"}), \
             patch.dict("os.environ", {"HOUSING_OWNER_VERIFIER": ""}), \
             patch("housing.db.connect", side_effect=AssertionError("private database opened")):
            app = AppTest.from_file(str(root / "app.py"), default_timeout=20).run()
        self.assertFalse(list(app.exception))
        self.assertFalse(list(app.radio))

    def test_display_app_has_no_management_or_download_surface(self):
        root = Path(__file__).resolve().parents[1]
        with patch.dict("os.environ", {"HOUSING_REQUIRE_OWNER_AUTH": "0"}):
            app = AppTest.from_file(str(root / "viewer_app.py"), default_timeout=20).run()
        self.assertFalse(list(app.exception))
        self.assertNotIn("数据与记录", app.radio(key="navigation").options)
        self.assertEqual(len(app.get("button")), 0)
        self.assertEqual(len(app.get("arrow_vega_lite_chart")) > 0, True)

    def test_display_rental_and_economy_scopes_render(self):
        root = Path(__file__).resolve().parents[1]
        with patch.dict("os.environ", {"HOUSING_REQUIRE_OWNER_AUTH": "0"}):
            app = AppTest.from_file(str(root / "viewer_app.py"), default_timeout=20).run()
            app.radio(key="navigation").set_value("租赁市场").run()
            self.assertFalse(list(app.exception))
            app.radio(key="ui-租金口径").set_value("地区对比").run()
            app.radio(key="ui-地区资料频率").set_value("年度 CMHC").run()
            self.assertFalse(list(app.exception))
            self.assertTrue(list(app.get("arrow_vega_lite_chart")))
            app.radio(key="navigation").set_value("经济与供给").run()
            self.assertFalse(list(app.exception))
            self.assertIn("人口", {item.value for item in app.subheader})

    def test_display_app_stops_before_snapshot_without_verifier(self):
        root = Path(__file__).resolve().parents[1]
        with patch.dict("os.environ", {"HOUSING_REQUIRE_OWNER_AUTH": "1", "HOUSING_OWNER_VERIFIER": ""}), \
             patch("housing.publication.load_display_snapshot", side_effect=AssertionError("snapshot opened")):
            app = AppTest.from_file(str(root / "viewer_app.py"), default_timeout=20).run()
        self.assertFalse(list(app.exception))
        self.assertFalse(list(app.radio))

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

    def test_display_publish_archives_and_can_restore_previous_good_version(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            database = root / "private.sqlite3"
            db = connect(database)
            db.execute("INSERT INTO raw_files VALUES (?,?,?,?,?,?,?)", ("first", "data/raw/a.csv", "test", "url", "2026-09-01", "2026-08", "CSV"))
            db.execute("INSERT INTO observations (series_id,period,value,version,raw_sha256,first_seen_at) VALUES (?,?,?,?,?,?)", ("trreb_sales", "2026-08", 100, 1, "first", "2026-09-01"))
            db.commit()
            output = root / "display.json"
            publish(database, output)
            old_hash = hashlib.sha256(output.read_bytes()).hexdigest()
            db.execute("INSERT INTO raw_files VALUES (?,?,?,?,?,?,?)", ("second", "data/raw/b.csv", "test", "url", "2026-09-02", "2026-08", "CSV"))
            db.execute("INSERT INTO observations (series_id,period,value,version,raw_sha256,first_seen_at) VALUES (?,?,?,?,?,?)", ("trreb_sales", "2026-08", 110, 2, "second", "2026-09-02"))
            db.commit()
            db.close()
            publish(database, output)
            self.assertEqual(load_display_snapshot(output)["observations"]["trreb_sales"]["2026-08"], 110)
            archived = root / "display_history" / f"{old_hash}.json"
            self.assertTrue(archived.is_file())
            restore_display_snapshot(output, old_hash)
            self.assertEqual(load_display_snapshot(output)["observations"]["trreb_sales"]["2026-08"], 100)
            archived.write_text("tampered")
            with self.assertRaises(ValueError):
                restore_display_snapshot(output, old_hash)
            self.assertEqual(load_display_snapshot(output)["observations"]["trreb_sales"]["2026-08"], 100)

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

    def test_owner_session_expires_and_rotation_revokes_it(self):
        import hashlib
        verifier = make_verifier("a sufficiently long password")
        state = {"owner_authenticated": True, "owner_authenticated_at": 100.0,
                 "owner_verifier_fingerprint": hashlib.sha256(verifier.encode()).hexdigest()}
        self.assertTrue(session_valid(state, verifier, now=100 + SESSION_SECONDS - 1))
        self.assertFalse(session_valid(state, verifier, now=100 + SESSION_SECONDS))
        self.assertFalse(session_valid(state, make_verifier("a different long password"), now=101))

    def test_failed_refresh_cycle_keeps_last_display_snapshot(self):
        from scripts.run_refresh_cycle import run_cycle
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "data").mkdir()
            current = root / "data/display_snapshot.json"
            current.write_text("last-good")
            calls = []

            def fail_refresh(command, **kwargs):
                calls.append(command)
                return SimpleNamespace(returncode=1, stdout="", stderr="source unavailable")

            report = run_cycle(root, fail_refresh)
            self.assertFalse(report["snapshot_published"])
            self.assertEqual(len(calls), 1)
            self.assertEqual(current.read_text(), "last-good")
            self.assertEqual(len(list((root / "data/run_reports").glob("*.json"))), 1)

    def test_refresh_cycle_requires_recovery_check_before_publish(self):
        from scripts.run_refresh_cycle import run_cycle
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "data").mkdir()
            current = root / "data/display_snapshot.json"
            current.write_text("last-good")
            calls = []

            def successful_refresh(command, **kwargs):
                calls.append(command)
                return SimpleNamespace(returncode=0, stdout="unchanged", stderr="")

            with patch("scripts.run_refresh_cycle.verify_dataset", side_effect=ValueError("bad manifest")):
                report = run_cycle(root, successful_refresh)
            self.assertFalse(report["snapshot_published"])
            self.assertIn("bad manifest", report["error"])
            self.assertEqual(current.read_text(), "last-good")
            self.assertEqual(len(calls), 1)

            with patch("scripts.run_refresh_cycle.verify_dataset", return_value={"source_files": 1}):
                report = run_cycle(root, successful_refresh)
            self.assertTrue(report["snapshot_published"])
            self.assertEqual(report["recovery_check"], {"source_files": 1})
            self.assertEqual(len(calls), 3)
