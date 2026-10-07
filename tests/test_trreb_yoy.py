import unittest
from pathlib import Path

from housing.trreb_yoy import front_comparison

RAW = Path(__file__).resolve().parents[1] / 'data/raw/trreb'


class TrrebPublishedYoyTests(unittest.TestCase):
    def test_both_layouts_read_revised_prior_year_and_printed_change(self):
        september = front_comparison(RAW / 'mw2609.pdf', '2026-09', {
            'trreb_sales': 5040, 'trreb_new_listings': 16500, 'trreb_active_listings': 26131})
        self.assertEqual(september['Sales'], (5040, 5540, -9.0))
        self.assertEqual(september['Active Listings'], (26131, 28813, -9.3))
        # Older layout: template placeholders (1,225 / 0 / -2.1%) share the listings rows.
        august = front_comparison(RAW / 'mw2608.pdf', '2026-08', {
            'trreb_sales': 5057, 'trreb_new_listings': 12075, 'trreb_active_listings': 24482})
        self.assertEqual(august['New Listings'], (12075, 14052, -14.1))
        self.assertEqual(august['Active Listings'], (24482, 27594, -11.3))
        self.assertEqual(august['Average Price'], (993410, 1021300, -2.7))

    def test_value_that_differs_from_the_stored_release_is_left_out(self):
        result = front_comparison(RAW / 'mw2608.pdf', '2026-08', {
            'trreb_sales': 5058, 'trreb_new_listings': 12075, 'trreb_active_listings': 24482})
        self.assertNotIn('Sales', result)
        self.assertIn('New Listings', result)


class TrrebPriceBandTests(unittest.TestCase):
    def test_bands_sum_to_monthly_sales_and_blank_cells_are_tolerated(self):
        from housing.trreb_price_bands import rows_for
        # September 2026 has a blank co-ownership cell in the $1.25M-$1.5M row.
        rows = dict((series, value) for series, _, value in rows_for(RAW / 'mw2609.pdf', '2026-09', 5040))
        self.assertEqual(rows['trreb_sales_band_under_500k'], 674)
        self.assertEqual(sum(rows.values()), 5040)
        with self.assertRaisesRegex(ValueError, 'not stored sales'):
            rows_for(RAW / 'mw2608.pdf', '2026-08', 5058)
