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
