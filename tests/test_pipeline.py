import sqlite3
import tempfile
import unittest
import zipfile
from xml.etree import ElementTree as ET
from datetime import date
from pathlib import Path
from unittest.mock import patch

from housing.db import connect
from housing.affordability import monthly_payment, historical_payment_rows
from housing.dashboard import snlr_rolling_rows
from housing.freshness import RULES, assess
from housing.ingest import (ingest, parse_boc, parse_cmhc_rental, parse_cmhc_rental_details,
                            parse_statcan, parse_trreb, register_raw)
from housing.metrics import resale_metrics, year_over_year
from housing.read_model import monthly
from housing.snapshot import save, open_snapshot

ROOT = Path(__file__).resolve().parents[1]

class PipelineTests(unittest.TestCase):
    def test_live_import_archives_external_source_for_recovery(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as external:
            root = Path(folder)
            db = connect(root / "data/housing.sqlite3")
            outside = Path(external) / "report.csv"
            outside.write_text("example source", encoding="utf-8")
            with patch("housing.ingest.ROOT", root):
                sha = register_raw(db, outside, "test", "https://example.test/report", "2026-08", "CSV")
            row = db.execute("SELECT path FROM raw_files WHERE sha256=?", (sha,)).fetchone()
            self.assertEqual(row["path"], f"data/raw/imported/{sha}.csv")
            self.assertEqual((root / row["path"]).read_text(), "example source")

    def test_failed_live_import_updates_manifest_for_rejected_batch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            raw = root / "data/raw/example.csv"
            raw.parent.mkdir(parents=True)
            raw.write_text("bad row")
            db = connect(root / "data/housing.sqlite3")
            with patch("housing.ingest.ROOT", root):
                with self.assertRaises(ValueError):
                    ingest(db, "test", raw, "https://example.test", "2026-08", "CSV",
                           [("trreb_sales", "bad-period", 100)])
            manifest = (root / "data/raw/manifest.csv").read_text()
            self.assertIn("data/raw/example.csv", manifest)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM ingestion_runs WHERE status='failed'").fetchone()[0], 1)

    def test_canadian_mortgage_scenario_calculation(self):
        self.assertAlmostEqual(monthly_payment(0, 5, 25), 0)
        self.assertAlmostEqual(monthly_payment(300_000, 0, 25), 1000)
        payment = monthly_payment(500_000, 5, 25)
        self.assertAlmostEqual(payment, 2908.02, delta=0.02)
        self.assertGreater(monthly_payment(500_000, 6, 25), payment)
        self.assertGreater(monthly_payment(500_000, 5, 20), payment)
        for args in ((-1, 5, 25), (100, -1, 25), (100, 5, 0)):
            with self.assertRaises(ValueError):
                monthly_payment(*args)

    def test_historical_payment_holds_loan_fixed_and_leaves_rate_gap(self):
        rows = historical_payment_rows([
            {'period': '2026-04', 'value': 4.0},
            {'period': '2026-06', 'value': 5.0},
        ], 500_000, 25)
        self.assertEqual([row['所属月份'] for row in rows], ['2026-04', '2026-05', '2026-06'])
        self.assertIsNone(rows[1]['估算月供（加元）'])
        self.assertNotEqual(rows[0]['segment'], rows[2]['segment'])
        self.assertAlmostEqual(rows[0]['估算月供（加元）'], monthly_payment(500_000, 4.0, 25))
        self.assertAlmostEqual(rows[2]['估算月供（加元）'], monthly_payment(500_000, 5.0, 25))

    def test_snlr_average_uses_monthly_ratios_and_resets_after_gap(self):
        values = [50.0, 75.0, 100.0, None, 80.0, 90.0, 100.0]
        months = [f'2026-{month:02d}' for month in range(1, 8)]
        data = {period: {'snlr_raw': ratio, 'trreb_sales': 10, 'trreb_new_listings': 20}
                for period, ratio in zip(months, values)}
        average = [row['比例（%）'] for row in snlr_rolling_rows(data, months[0], months[-1])
                   if row['系列'] == '连续三个月均线']
        self.assertEqual(average, [None, None, 75.0, None, None, None, 90.0])

    def test_monthly_observation_save_open_preserves_input_versions(self):
        db = connect(ROOT / "data/housing.sqlite3")
        with tempfile.TemporaryDirectory() as temp:
            path = save(db, "2026-08", temp)
            loaded = open_snapshot(path)
        self.assertEqual(loaded["kind"], "monthly_observation")
        self.assertEqual(loaded["period"], "2026-08")
        self.assertEqual(loaded["values_for_period"]["trreb_sales"], 5057.0)
        reference = loaded["inputs"]["trreb_sales"]
        self.assertEqual(reference["source_period"], "2026-08")
        self.assertTrue(reference["ids"])
        self.assertTrue(reference["versions"])
        self.assertTrue(reference["raw_sha256"])

    def test_official_samples_and_formulas(self):
        boc = parse_boc(ROOT / "data/raw/boc/core-2022-09-to-2026-08.json")
        statcan = parse_statcan(ROOT / "data/raw/statcan/14100460-eng.zip")
        trreb = parse_trreb(ROOT / "data/manual/trreb-market-watch.csv", ROOT / "data/raw/trreb/mw2608.pdf")
        self.assertIn(("mortgage_uninsured_fixed_5plus", "2026-06", 4.35), boc)
        self.assertIn(("toronto_unemployment_rate", "2026-08", 6.7), statcan)
        self.assertIn(("trreb_sales", "2026-08", 5057.0), trreb)
        self.assertEqual(resale_metrics(5057, 12075, 24482)["moi_raw"], 24482 / 5057)
        self.assertIsNone(resale_metrics(0, 0, 24482)["moi_raw"])
        self.assertIsNone(resale_metrics(0, 0, 24482)["snlr_raw"])
        self.assertIsNone(year_over_year({"2026-08": 5057}, "2026-08"))

    def test_repeated_import_and_revision(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample.txt"
            path.write_text("first")
            db = connect(Path(temp) / "test.sqlite3")
            first = ingest(db, "test", path, "https://example.org/sample", "2026-08", "test",
                           [("trreb_sales", "2026-08", 5057)])
            second = ingest(db, "test", path, "https://example.org/sample", "2026-08", "test",
                            [("trreb_sales", "2026-08", 5057)])
            path.write_text("revised")
            third = ingest(db, "test", path, "https://example.org/sample", "2026-08", "test",
                           [("trreb_sales", "2026-08", 5060)])
            self.assertEqual((first["inserted"], second["unchanged"], third["revised"]), (1, 1, 1))
            rows = db.execute("SELECT version,value FROM observations ORDER BY version").fetchall()
            self.assertEqual([(r["version"], r["value"]) for r in rows], [(1, 5057), (2, 5060)])
            self.assertEqual(monthly(db)["2026-08"]["trreb_sales"], 5060)

    def test_replaying_old_source_does_not_replace_a_revision(self):
        with tempfile.TemporaryDirectory() as temp:
            old, new = Path(temp) / "old.txt", Path(temp) / "new.txt"
            old.write_text("original")
            new.write_text("official revision")
            db = connect(Path(temp) / "test.sqlite3")
            for path, value in ((old, 5057), (new, 5060)):
                ingest(db, "test", path, "https://example.org/report", "2026-08", "fixture",
                       [("trreb_sales", "2026-08", value)])
            with self.assertRaisesRegex(ValueError, "Stale source replay"):
                ingest(db, "test", old, "https://example.org/report", "2026-08", "fixture",
                       [("trreb_sales", "2026-08", 5057)])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 2)
            self.assertEqual(monthly(db)["2026-08"]["trreb_sales"], 5060)
            self.assertEqual(db.execute("SELECT status FROM ingestion_runs ORDER BY id DESC LIMIT 1").fetchone()[0], "failed")

    def test_invalid_batch_is_atomic_and_records_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "bad-batch.txt"
            source.write_text("invalid batch fixture")
            db = connect(Path(temp) / "atomic.sqlite3")
            with self.assertRaisesRegex(ValueError, "outside accepted range"):
                ingest(db, "test", source, "https://example.org/bad", "2026-08", "fixture",
                       [("trreb_sales", "2026-08", 5057),
                        ("toronto_unemployment_rate", "2026-08", 101)])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 0)
            run = db.execute("SELECT status,error FROM ingestion_runs").fetchone()
            self.assertEqual(run["status"], "failed")
            self.assertIn("101", run["error"])

    def test_cmhc_rental_workbook_import_and_freshness(self):
        source = ROOT / "data/raw/cmhc/rmr-toronto-2025-en.xlsx"
        rows = parse_cmhc_rental(source)
        self.assertEqual(len(rows), 39)
        # Private row (townhouse) rents, Table 2.1.2; studio and 2024 one-bedroom cells are suppressed.
        for bedroom, values in (("1br", (None, 1787.0)), ("2br", (1755.0, 1954.0)), ("3plus", (1990.0, 2162.0)), ("total", (1944.0, 2109.0))):
            for period, value in zip(("2024", "2025"), values):
                found = [v for s, p, v in rows if s == f"toronto_row_rent_{bedroom}" and p == period]
                self.assertEqual(found, [value] if value is not None else [])
        self.assertFalse(any(s == "toronto_row_rent_studio" for s, _, _ in rows))
        self.assertIn(("toronto_pbr_vacancy_rate", "2025", 3.0), rows)
        self.assertIn(("toronto_pbr_rent_2br", "2025", 2046.0), rows)
        self.assertIn(("toronto_condo_vacancy_rate", "2025", 0.9), rows)
        self.assertIn(("toronto_condo_rent_2br", "2025", 2891.0), rows)
        self.assertIn(("toronto_condo_rent_2br", "2024", 2924.0), rows)
        for market, values in (("pbr", (1491, 1761, 2046, 2317, 1913)),
                               ("condo", (2242, 2350, 2891, 3306, 2747))):
            for bedroom, value in zip(("studio", "1br", "2br", "3plus", "total"), values):
                self.assertIn((f"toronto_{market}_rent_{bedroom}", "2025", value), rows)
        for bedroom, value in zip(("studio", "1br", "2br", "3plus"), (4.2, 3.6, 2.5, 1.9)):
            self.assertIn((f"toronto_pbr_vacancy_{bedroom}", "2025", value), rows)
        self.assertFalse(any(series_id.startswith("toronto_condo_vacancy_")
                             and series_id != "toronto_condo_vacancy_rate" for series_id, _, _ in rows))
        details = {(item["series_id"], item["period"]): item for item in parse_cmhc_rental_details(source)}
        self.assertEqual(details[("toronto_condo_rent_studio", "2025")]["quality"], "c")
        self.assertEqual(details[("toronto_condo_rent_3plus", "2025")]["quality"], "b")
        self.assertEqual(details[("toronto_condo_rent_2br", "2025")]["significance"], "-")
        self.assertIsNone(details[("toronto_pbr_rent_2br", "2025")]["significance"])
        self.assertEqual(details[("toronto_pbr_vacancy_2br", "2025")]["significance"], "↑")
        with tempfile.TemporaryDirectory() as temp:
            db = connect(Path(temp) / "rental.sqlite3")
            ingest(db, "CMHC Rental Market Survey", source, "https://example.org/rental.xlsx",
                   "2024/2025", "official XLSX", rows)
            for series_id in {row[0] for row in rows}:
                state = assess(db, series_id, date(2026, 9, 23))
                self.assertEqual(state["status"], "current", series_id)
                self.assertEqual(state["latest_period"], "2025", series_id)

    def test_cmhc_suppression_and_missingness_are_not_numeric_zero(self):
        # Mutate only isolated copies of the original workbook, retaining its
        # headers and source layout to exercise the parser's actual cell logic.
        source = ROOT / "data/raw/cmhc/rmr-toronto-2025-en.xlsx"
        with tempfile.TemporaryDirectory() as temp:
            for marker, expected in (("**", "suppressed"), ("", "not_available")):
                target = Path(temp) / f"{expected}.xlsx"
                self._mutate_cmhc_cell(source, target, "Table 1.1.2", "D54", marker)
                details = parse_cmhc_rental_details(target)
                item = next(row for row in details if row["series_id"] == "toronto_pbr_rent_studio"
                            and row["period"] == "2025")
                self.assertEqual(item["status"], expected)
                self.assertIsNone(item["value"])
                numeric = parse_cmhc_rental(target)
                self.assertEqual(len(numeric), 38)
                self.assertNotIn(("toronto_pbr_rent_studio", "2025"),
                                 {(series_id, period) for series_id, period, _ in numeric})
                self.assertIn(("toronto_pbr_rent_studio", "2024", 1448), numeric)

    def test_cmhc_rejects_shifted_headers_unknown_values_and_missing_quality(self):
        source = ROOT / "data/raw/cmhc/rmr-toronto-2025-en.xlsx"
        cases = (("B6", "2 Bedroom", "bedroom/market header"),
                 ("D7", "Oct-26", "Nonconsecutive"),
                 ("D7", "Nov-25", "survey period header"),
                 ("D54", "unrecognized", "Unrecognized CMHC value"),
                 ("E54", "", "quality flag"))
        with tempfile.TemporaryDirectory() as temp:
            for cell, value, error in cases:
                with self.subTest(cell=cell, value=value):
                    target = Path(temp) / "invalid.xlsx"
                    self._mutate_cmhc_cell(source, target, "Table 1.1.2", cell, value)
                    with self.assertRaisesRegex(ValueError, error):
                        parse_cmhc_rental(target)

    @staticmethod
    def _mutate_cmhc_cell(source, target, sheet_name, reference, value):
        ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
              "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
        with zipfile.ZipFile(source) as original:
            workbook = ET.fromstring(original.read("xl/workbook.xml"))
            rels = {item.attrib["Id"]: item.attrib["Target"]
                    for item in ET.fromstring(original.read("xl/_rels/workbook.xml.rels"))}
            sheet = next(item for item in workbook.find("m:sheets", ns)
                         if item.attrib["name"] == sheet_name)
            path = rels[sheet.attrib["{" + ns["r"] + "}id"]].lstrip("/")
            if not path.startswith("xl/"):
                path = "xl/" + path
            document = ET.fromstring(original.read(path))
            cell = document.find(f".//m:c[@r='{reference}']", ns)
            cell.clear()
            cell.set("r", reference)
            cell.set("t", "inlineStr")
            inline = ET.SubElement(cell, "{" + ns["m"] + "}is")
            ET.SubElement(inline, "{" + ns["m"] + "}t").text = value
            with zipfile.ZipFile(target, "w") as altered:
                for name in original.namelist():
                    altered.writestr(name, ET.tostring(document) if name == path else original.read(name))

    def test_freshness_release_cutoffs_and_catalog_coverage(self):
        catalog_db = connect(":memory:")
        series = {row[0] for row in catalog_db.execute("SELECT id FROM series")}
        self.assertEqual(set(RULES), series)
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "policy.json"
            source.write_text("policy rate fixture")
            db = connect(Path(temp) / "policy.sqlite3")
            ingest(db, "test", source, "https://example.org/policy", "2026-07", "fixture",
                   [("boc_policy_rate", "2026-07-31", 2.25)])
            status = assess(db, "boc_policy_rate", date(2026, 9, 23))
            self.assertEqual(status["expected_period"], "2026-08")
            self.assertEqual(status["status"], "overdue")
            self.assertEqual(status["missing_periods"], ["2026-08"])

if __name__ == "__main__":
    unittest.main()
