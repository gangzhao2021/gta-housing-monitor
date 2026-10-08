import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from housing.affordability import monthly_payment, scenario, scenario_notes


class ScenarioTest(unittest.TestCase):
    def test_price_first_scenario(self):
        s = scenario(917_600, 20, 25, 4.49)
        self.assertAlmostEqual(s["loan"], 734_080)
        self.assertAlmostEqual(s["down"], 183_520)
        self.assertAlmostEqual(s["payment"], 4058.85, places=2)
        self.assertEqual(s["qualifying_rate"], 6.49)
        self.assertAlmostEqual(s["stress_payment"], 4912.59, places=2)
        self.assertAlmostEqual(s["income"], s["stress_payment"] * 12 / 0.39)
        self.assertAlmostEqual(s["interest"], s["payment"] * 300 - 734_080)

    def test_qualifying_rate_floor(self):
        s = scenario(500_000, 20, 25, 2.0)
        self.assertEqual(s["qualifying_rate"], 5.25)
        self.assertAlmostEqual(s["stress_payment"], monthly_payment(400_000, 5.25, 25))

    def test_notes_only_below_twenty_percent(self):
        self.assertEqual(scenario_notes(2_000_000, 20, 30), [])
        notes = scenario_notes(1_600_000, 10, 30)
        self.assertEqual(len(notes), 3)
        self.assertEqual(len(scenario_notes(900_000, 10, 25)), 1)


class AmortizationTest(unittest.TestCase):
    def test_yearly_rows_add_up(self):
        from housing.affordability import amortization_by_year
        rows = amortization_by_year(734_080, 4.49, 25)
        self.assertEqual(len(rows), 25)
        self.assertAlmostEqual(sum(r["principal"] for r in rows), 734_080, delta=1)
        self.assertAlmostEqual(rows[-1]["balance"], 0, delta=1)
        self.assertEqual(next(r["year"] for r in rows if r["principal"] > r["interest"]), 10)
        self.assertAlmostEqual(rows[9]["balance"], 532_401, delta=1)
        payment = monthly_payment(734_080, 4.49, 25)
        self.assertAlmostEqual(rows[0]["principal"] + rows[0]["interest"], payment * 12, delta=0.01)


if __name__ == "__main__":
    unittest.main()
