import copy
import unittest

from housing import market_temperature as mt


def synthetic():
    rows = {}
    for year in range(2004, 2010):
        for month in range(1, 13):
            rows[f'{year}-{month:02d}'] = {'sales': 50.0, 'new_listings': 100.0, 'active_listings': 200.0, 'hpi_index': 100.0}
    return rows


class MarketTemperatureTests(unittest.TestCase):
    def test_bands(self):
        self.assertEqual(mt.state(-10), 'cool')
        self.assertEqual(mt.state(-9.99), 'balanced')
        self.assertEqual(mt.state(10), 'hot')
        self.assertIsNone(mt.state(None))

    def test_norm_uses_only_earlier_years(self):
        rows = synthetic()
        # A hotter 2009 must not move 2008's norm, and 2009 reads hot against 2004-2008.
        hot = copy.deepcopy(rows)
        for month in range(1, 13):
            hot[f'2009-{month:02d}']['sales'] = 70.0
        before, after = mt.readings(rows), mt.readings(hot)
        self.assertEqual(before['2008-06'], after['2008-06'])
        self.assertEqual(after['2009-06']['state'], 'hot')
        self.assertAlmostEqual(after['2009-06']['gap'], 20.0)
        self.assertNotIn('2006-06', before)  # fewer than three earlier years


class TemperatureSnapshotTests(unittest.TestCase):
    def test_snapshot_validation_accepts_reading_and_rejects_bad_state(self):
        from housing.publication import validate_temperature
        good = {'band_pp': 10.0, 'months': {'2026-09': {'snlr3': 37.4, 'snlr_norm': 53.8, 'gap': -16.5, 'state': 'cool',
                                                        'moi3': 4.8, 'moi_norm': 2.6}},
                'outcomes_12m': {k: {'n': 1, 'mean_change': 0.0, 'share_up': 0.5} for k in ('cool', 'balanced', 'hot')}}
        validate_temperature(good)
        bad = copy.deepcopy(good)
        bad['months']['2026-09']['state'] = 'boiling'
        with self.assertRaises(ValueError):
            validate_temperature(bad)
        bad = copy.deepcopy(good)
        bad['months']['2026-09']['gap'] = float('nan')
        with self.assertRaises(ValueError):
            validate_temperature(bad)
