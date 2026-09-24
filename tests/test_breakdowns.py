import csv
import io
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from housing.breakdowns import construction_breakdown, trreb_hpi_breakdown, trreb_hpi_for_observation


ROOT = Path(__file__).resolve().parents[1]


class BreakdownTests(unittest.TestCase):
    def observation_database(self):
        # A private copy preserves the delivered database and its catalog.
        source = sqlite3.connect(f"file:{ROOT / 'data/housing.sqlite3'}?mode=ro", uri=True)
        db = sqlite3.connect(":memory:")
        source.backup(db)
        source.close()
        self.addCleanup(db.close)
        return db

    def test_saved_construction_types_and_source_reconciliation(self):
        rows = construction_breakdown(ROOT / "data/raw/statcan/34100154-eng.zip")
        latest = [row for row in rows if row["period"] == "2026-08"]
        self.assertEqual(len(latest), 15)
        starts = {row["type_id"]: row["value"] for row in latest if row["metric"] == "starts"}
        self.assertEqual(starts, {"total": 1192, "detached": 220, "semi_detached": 38,
                                  "row": 205, "apartment_other": 729})
        self.assertTrue(all(row["reconciliation_ok"] for row in latest))
        self.assertEqual({(r["period"], r["metric"]) for r in rows if r["reconciliation_ok"] is False},
                         {("1982-01", "under_construction"), ("1988-01", "under_construction")})
        self.assertEqual(latest[0]["geography"], "Toronto CMA 2011 boundary")
        self.assertEqual(len(latest[0]["source_sha256"]), 64)

    def test_suppressed_value_is_not_zero_and_period_is_scoped(self):
        fields = ["REF_DATE", "GEO", "DGUID", "Housing estimates", "Type of unit", "UOM",
                  "SCALAR_FACTOR", "VALUE", "STATUS"]
        data = io.StringIO()
        writer = csv.DictWriter(data, fieldnames=fields)
        writer.writeheader()
        for period, value, status in [("2026-07", "99", ""), ("2026-08", "0", "x")]:
            writer.writerow(dict(zip(fields, [period, "Toronto, Ontario", "2011S0503535", "Housing starts",
                                              "Total units", "Units", "units", value, status])))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("34100154.csv", data.getvalue())
            rows = construction_breakdown(path, "2026-08")
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["value"])
        self.assertIsNone(rows[0]["reconciliation_ok"])
        self.assertEqual(rows[0]["source_status"], "x")

    def test_saved_trreb_hpi_type_alignment_and_published_yoy(self):
        rows = trreb_hpi_breakdown(ROOT / "data/raw/trreb/mw2608.pdf")
        self.assertEqual(len(rows), 15)
        benchmarks = {r["type_id"]: r["value"] for r in rows if r["metric"] == "benchmark"}
        self.assertEqual(benchmarks, {"composite": 925900, "detached": 1209600, "attached": 919000,
                                      "townhouse": 666500, "apartment": 531200})
        self.assertEqual(next(r["value"] for r in rows if r["type_id"] == "apartment" and r["metric"] == "source_yoy"), -7.08)
        self.assertTrue(all(r["source_page"] == 25 and r["period"] == "2026-08" for r in rows))
        historic = trreb_hpi_breakdown(ROOT / "data/raw/trreb/mw2209.pdf")
        self.assertEqual(next(r["value"] for r in historic if r["type_id"] == "composite" and r["metric"] == "benchmark"), 1110700)

    def test_report_period_cannot_come_from_a_wrong_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            renamed = Path(directory) / "mw2607.pdf"
            renamed.symlink_to(ROOT / "data/raw/trreb/mw2608.pdf")
            with self.assertRaisesRegex(ValueError, "reference month differ"):
                trreb_hpi_breakdown(renamed)

    def test_observation_provenance_ignores_a_later_unselected_source(self):
        db = self.observation_database()
        db.execute("INSERT INTO raw_files VALUES (?,?,?,?,?,?,?)",
                   ("f" * 64, "data/raw/trreb/unused-later.pdf", "TRREB", "https://example.invalid/unused",
                    "2099-01-01T00:00:00+00:00", "2026-08", "unused later source"))
        rows = trreb_hpi_for_observation(db, "2026-08", ROOT)
        self.assertEqual(len(rows), 15)
        anchor = db.execute("SELECT id,raw_sha256 FROM observations WHERE series_id='trreb_hpi_benchmark' "
                            "AND period='2026-08' ORDER BY version DESC LIMIT 1").fetchone()
        self.assertTrue(all(row["anchor_observation_id"] == anchor[0] and
                            row["anchor_source_sha256"] == anchor[1] for row in rows))

    def test_observation_provenance_rejects_changed_pdf_bytes(self):
        db = self.observation_database()
        rows = trreb_hpi_for_observation(db, "2026-08", ROOT)
        db.execute("UPDATE raw_files SET path=? WHERE sha256=?",
                   ("data/raw/trreb/mw2607.pdf", rows[0]["source_sha256"]))
        with self.assertRaisesRegex(ValueError, "checksum differs"):
            trreb_hpi_for_observation(db, "2026-08", ROOT)

    def test_observation_provenance_rejects_a_different_composite_amount(self):
        db = self.observation_database()
        db.execute("UPDATE observations SET value=value+1 WHERE series_id='trreb_hpi_benchmark' "
                   "AND period='2026-08'")
        with self.assertRaisesRegex(ValueError, "differs from the selected observation"):
            trreb_hpi_for_observation(db, "2026-08", ROOT)


if __name__ == "__main__":
    unittest.main()
