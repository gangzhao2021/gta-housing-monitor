import hashlib
import json
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from housing.db import connect
from housing.external_factors import parse_building_cost, parse_energy, parse_fx, parse_wti
from housing.freshness import assess
from housing.ingest import ingest, validate_rows
from scripts.refresh_official import refresh_one, source_url
from scripts.run_refresh_cycle import run_cycle


class ExternalFactorsTests(unittest.TestCase):
    def test_boc_monthly_parsers_use_exact_series_and_leave_missing_months_out(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "source.json"
            file.write_text(json.dumps({
                "seriesDetail": {"FXMUSDCAD": {}, "M.ENER": {}},
                "observations": [
                    {"d": "2026-06-01", "FXMUSDCAD": {"v": "1.3512"}, "M.ENER": {"v": "710.5"}},
                    {"d": "2026-07-01"},
                    {"d": "2026-08-01", "FXMUSDCAD": {"v": "1.3898"}, "M.ENER": {"v": "725.1"}},
                ],
            }))
            self.assertEqual(parse_fx(file), [("usd_cad_monthly", "2026-06", 1.3512),
                                              ("usd_cad_monthly", "2026-08", 1.3898)])
            self.assertEqual(parse_energy(file)[-1], ("boc_energy_price_index", "2026-08", 725.1))
            file.write_text(json.dumps({"seriesDetail": {}, "observations": []}))
            with self.assertRaisesRegex(ValueError, "metadata"):
                parse_fx(file)

    def test_wti_parser_keeps_eia_gaps_and_rejects_wrong_page(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "wti.html"
            file.write_text("Cushing, OK WTI Spot Price FOB (Dollars per Barrel)"
                            "<table><tr><th>Jan</th><th>Feb</th><th>Dec</th></tr>"
                            "<tbody><tr><td>2026</td>" +
                            "".join(f"<td>{80.5 + month}</td>" if month in (1, 3) else "<td></td>"
                                    for month in range(1, 13)) +
                            "</tr></tbody></table>")
            self.assertEqual(parse_wti(file), [("wti_cushing_spot_price", "2026-01", 81.5),
                                               ("wti_cushing_spot_price", "2026-03", 83.5)])
            file.write_text("Other energy page")
            with self.assertRaisesRegex(ValueError, "Not the EIA"):
                parse_wti(file)

    def test_building_cost_selects_toronto_residential_composite_only(self):
        header = ("REF_DATE,GEO,DGUID,Type of building,Division,UOM,SCALAR_FACTOR,VECTOR,VALUE,STATUS\n")
        line = ('2026-04,"Toronto, Ontario",2021S0503535,Residential buildings [621],'
                'Division composite,"Index, 2023=100",units,v1617912612,105.7,\n')
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "source.zip"
            with zipfile.ZipFile(file, "w") as archive:
                archive.writestr("18100289.csv", header + line + line.replace("Toronto, Ontario", "Ottawa, Ontario").replace("v1617912612", "v0"))
            self.assertEqual(parse_building_cost(file),
                             [("toronto_residential_construction_cost_index", "2026-04", 105.7)])
            validate_rows(parse_building_cost(file))
            with zipfile.ZipFile(file, "w") as archive:
                archive.writestr("18100289.csv", header + line.replace("Division composite", "Concrete"))
            with self.assertRaisesRegex(ValueError, "definition changed"):
                parse_building_cost(file)

    def test_quarterly_freshness_uses_completed_quarter_without_monthly_gap(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "quarter.txt"
            source.write_text("sample")
            db = connect(root / "housing.sqlite3")
            try:
                ingest(db, "StatsCan BCPI", source, "https://example.test", "2026-01/2026-04", "fixture",
                       [("toronto_residential_construction_cost_index", "2026-01", 106.5),
                        ("toronto_residential_construction_cost_index", "2026-04", 105.7)])
                current = assess(db, "toronto_residential_construction_cost_index", date(2026, 9, 24))
                self.assertEqual((current["status"], current["expected_period"]), ("current", "2026-04"))
                overdue = assess(db, "toronto_residential_construction_cost_index", date(2026, 12, 20))
                self.assertEqual(overdue["missing_periods"], ["2026-07"])
                self.assertEqual(overdue["status"], "overdue")
            finally:
                db.close()

    def test_fx_refresh_records_immutable_source_and_skips_same_bytes(self):
        payload = json.dumps({"seriesDetail": {"FXMUSDCAD": {}},
                              "observations": [{"d": "2026-08-01", "FXMUSDCAD": {"v": "1.3898"}}]}).encode()

        def fetcher(url, path):
            path.write_bytes(payload)
            return hashlib.sha256(payload).hexdigest()

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            db = connect(root / "data/housing.sqlite3")
            try:
                first = refresh_one(db, "fx", root, date(2026, 9, 24), fetcher)
                again = refresh_one(db, "fx", root, date(2026, 9, 24), fetcher)
                self.assertEqual(first["inserted"], 1)
                self.assertEqual(again["status"], "unchanged")
                self.assertEqual(db.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 1)
                self.assertIn("end_date=2026-08-31", source_url("fx", date(2026, 9, 24)))
            finally:
                db.close()

    def test_factor_failure_keeps_a_verified_core_display_update(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "data").mkdir()
            calls = []

            def runner(command, **kwargs):
                calls.append(command)
                failed = "factors" in command
                return SimpleNamespace(returncode=int(failed), stdout="", stderr="source unavailable" if failed else "")

            with patch("scripts.run_refresh_cycle.verify_dataset", return_value={"source_files": 1}):
                result = run_cycle(root, runner)
            self.assertTrue(result["snapshot_published"])
            self.assertEqual(result["factors_exit_code"], 1)
            self.assertEqual(len(calls), 3)


if __name__ == "__main__":
    unittest.main()
