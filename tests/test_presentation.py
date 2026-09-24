import tempfile
import unittest
from pathlib import Path

from housing.db import connect
from housing.ingest import ingest
from housing.presentation import (
    annual_data, available_periods, calendar_periods, chart_rows,
    metric_at, period_label, scoped_rows,
)
from housing.snapshot import build


class PresentationTests(unittest.TestCase):
    def test_cards_do_not_replace_missing_month_with_older_value(self):
        data = {"2025-08": {"mortgage": 4.8}, "2026-06": {"mortgage": 4.35}}
        card = metric_at(data, "mortgage", "2026-08", "%")
        self.assertIsNone(card["value"])
        self.assertIsNone(card["delta"])
        self.assertEqual(card["previous_value"], 4.8)
        self.assertEqual(available_periods(data, ["mortgage"]), ["2025-08", "2026-06"])
        self.assertEqual(available_periods(data, ["unavailable"]), [])

    def test_yoy_uses_exact_prior_year_and_correct_units(self):
        data = {"2023": {"rent": 1700}, "2025": {"rent": 2046}}
        self.assertIsNone(metric_at(data, "rent", "2025", "CAD/month")["delta"])
        data["2024"] = {"rent": 1974}
        self.assertAlmostEqual(metric_at(data, "rent", "2025", "CAD/month")["delta"],
                               (2046 / 1974 - 1) * 100)
        rates = {"2025-08": {"rate": 6.2, "moi": 3.5},
                 "2026-08": {"rate": 6.7, "moi": 4.84}}
        rate = metric_at(rates, "rate", "2026-08", "%")
        self.assertAlmostEqual(rate["delta"], 0.5)
        self.assertEqual(rate["delta_unit"], "百分点")
        self.assertAlmostEqual(metric_at(rates, "moi", "2026-08", "月")["delta"], 1.34)

    def test_zero_base_and_missing_value_do_not_create_false_growth(self):
        values = {"2024": {"rate": 0, "count": 0}, "2025": {"rate": 1, "count": 2}}
        self.assertIsNone(metric_at(values, "count", "2025")["delta"])
        self.assertEqual(metric_at(values, "rate", "2025", "%")["delta"], 1)
        self.assertIsNone(metric_at({"2025": {"rate": float("nan")}}, "rate", "2025")["value"])

    def test_chart_and_export_keep_same_scope_and_do_not_bridge_calendar_gaps(self):
        data = {"2025-12": {"sales": 10}, "2026-02": {"sales": 30},
                "2026-03": {"sales": 40}}
        exported = scoped_rows(data, ["sales"], "2025-12", "2026-02")
        chart = chart_rows(data, "sales", "2025-12", "2026-02")
        self.assertEqual([row["period"] for row in exported], ["2025-12", "2026-01", "2026-02"])
        self.assertEqual([row["sales"] for row in exported], [10, None, 30])
        self.assertEqual([row["value"] for row in chart], [10, None, 30])
        self.assertNotEqual(chart[0]["segment"], chart[2]["segment"])
        self.assertEqual(calendar_periods("2023", "2025"), ["2023", "2024", "2025"])
        with self.assertRaises(ValueError):
            calendar_periods("2026-08", "2025-08")
        with self.assertRaises(ValueError):
            calendar_periods("2025", "2026-08")

    def test_readable_period_labels(self):
        self.assertEqual(period_label("2026-06"), "2026年6月")
        self.assertEqual(period_label("2025"), "2025年")
        self.assertEqual(period_label("2026-08-31"), "2026年8月31日")

    def test_snapshot_reference_cutoffs_and_daily_current_month(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.txt"
            source.write_text("calendar observation fixture")
            db = connect(Path(temp) / "test.sqlite3")
            rows = [
                ("trreb_sales", "2025-06", 1000),
                ("trreb_sales", "2025-08", 1000),
                ("trreb_sales", "2025-10", 1000),
                ("boc_policy_rate", "2025-08-29", 2.25),
                ("goc_5y_yield", "2025-08-28", 3.0),
                ("goc_5y_yield", "2025-08-29", 3.2),
                ("toronto_cma_2021_population", "2024", 7_000_000),
                ("toronto_cma_2021_population", "2025", 7_100_000),
                ("toronto_pbr_rent_2br", "2024", 1974),
                ("toronto_pbr_rent_2br", "2025", 2046),
            ]
            ingest(db, "fixture", source, "https://example.org/source", "2024/2025", "fixture", rows)
            june = build(db, "2025-06")
            august = build(db, "2025-08")
            october = build(db, "2025-10")
            self.assertEqual(june["inputs"]["toronto_cma_2021_population"]["source_period"], "2024")
            self.assertEqual(august["inputs"]["toronto_cma_2021_population"]["source_period"], "2025")
            self.assertEqual(august["inputs"]["toronto_pbr_rent_2br"]["source_period"], "2024")
            self.assertEqual(october["inputs"]["toronto_pbr_rent_2br"]["source_period"], "2025")
            self.assertEqual(october["inputs"]["toronto_pbr_rent_2br"]["reference_month"], "2025-10")
            self.assertNotIn("boc_policy_rate", august["no_new_value_for_selected_month"])
            self.assertNotIn("goc_5y_yield", august["no_new_value_for_selected_month"])
            yield_input = august["inputs"]["goc_5y_yield"]
            self.assertEqual(len(yield_input["ids"]), 2)
            self.assertEqual(len(yield_input["versions"]), 2)
            self.assertAlmostEqual(yield_input["value"], 3.1)
            annual = annual_data(db, ["toronto_pbr_rent_2br"])
            self.assertEqual(annual["2025"]["toronto_pbr_rent_2br"], 2046)
            self.assertEqual(scoped_rows(annual, ["toronto_pbr_rent_2br"], "2024", "2024"),
                             [{"period": "2024", "toronto_pbr_rent_2br": 1974}])
            with self.assertRaises(ValueError):
                annual_data(db, ["trreb_sales"])
            db.close()


if __name__ == "__main__":
    unittest.main()
