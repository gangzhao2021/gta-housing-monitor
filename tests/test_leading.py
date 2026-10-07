import copy
import unittest
from pathlib import Path

from housing import leading

INPUTS = Path(__file__).resolve().parents[1] / 'data/research/v2-inputs.csv'
# Latest month each input may contribute at decision month T (protocol v2 lags).
VISIBLE = {'teranet_index_sa': -2, 'teranet_pairs': -2, 'mortgage_5y': 0, 'bond_5y': 0,
           'ontario_unemployment': -1, 'starts': -1, 'toronto_nhpi': -2, 'canada_epu': -1}


class LeadingStudyTests(unittest.TestCase):
    @unittest.skipUnless(INPUTS.exists(), 'private research inputs not present')
    def test_forecasts_ignore_everything_published_after_the_decision(self):
        data = leading.load(INPUTS)
        T = '2015-06'
        before = leading.forecasts(data, 6, [T])[T]
        scrambled = copy.deepcopy(data)
        for series, lag in VISIBLE.items():
            for period in scrambled[series]:
                if period > leading.shift(T, lag):
                    scrambled[series][period] *= 3.7
        after = leading.forecasts(scrambled, 6, [T])[T]
        for key in before:
            if key != 'actual':
                self.assertAlmostEqual(before[key], after[key], places=10, msg=key)
        self.assertNotAlmostEqual(before['actual'], after['actual'])

    def test_clark_west_and_r2_on_a_known_case(self):
        rows = {leading.shift('2010-01', i): {'actual': float(i % 5), 'benchmark': 2.0, 'perfect': float(i % 5)}
                for i in range(40)}
        result = leading.evaluate(rows, 'perfect', 6, '2010-01', '2099-12')
        self.assertAlmostEqual(result['oos_r2'], 1.0)
        self.assertLess(result['clark_west_p_one_sided'], 0.01)
        self.assertEqual(leading.evaluate(rows, 'perfect', 6, '2010-01', '2010-06')['status'], 'too_few_cases')


class LeadingV3Tests(unittest.TestCase):
    @unittest.skipUnless((INPUTS.parent / 'trreb-history.csv').exists(), 'private TRREB history not present')
    def test_trreb_features_ignore_months_after_t_minus_one(self):
        from housing import leading_v3
        data = leading_v3.load_trreb(INPUTS.parent / 'trreb-history.csv', leading.load(INPUTS))
        T = '2016-03'
        before = leading.forecasts(data, 12, [T], features=leading_v3.FEATURES, feature_fn=leading_v3.feature)[T]
        scrambled = copy.deepcopy(data)
        for period, row in scrambled['trreb'].items():
            if period > leading.shift(T, -1):
                for key, value in row.items():
                    if isinstance(value, float):
                        row[key] = value * 2.9
        for period in scrambled['teranet_index_sa']:
            if period > leading.shift(T, -2):
                scrambled['teranet_index_sa'][period] *= 1.7
        after = leading.forecasts(scrambled, 12, [T], features=leading_v3.FEATURES, feature_fn=leading_v3.feature)[T]
        for key in before:
            if key != 'actual':
                self.assertAlmostEqual(before[key], after[key], places=10, msg=key)
