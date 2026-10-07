import unittest
from pathlib import Path

from housing.trreb_history import extract

ARCHIVE = Path(__file__).resolve().parents[1] / 'data/raw/trreb_history'


@unittest.skipUnless(ARCHIVE.exists(), 'private TRREB archive not present')
class TrrebHistoryTests(unittest.TestCase):
    def check(self, period, **expected):
        record = extract(ARCHIVE / f'mw{period[2:4]}{period[5:]}.pdf', period)
        for key, value in expected.items():
            self.assertEqual(record[key], value, (period, key))
        return record

    def test_each_layout_and_known_misprints(self):
        self.check('2004-01', layout='legacy', sales=4256, new_listings=10020, active_listings=16347)
        # Grand Total columns misprinted; the front-page summary decides which is which.
        self.check('2004-03', layout='legacy', new_listings=14641, active_listings=19749, sales=9076)
        # Digits printed spaced apart.
        self.check('2006-10', layout='legacy', sales=6876, new_listings=13116, active_listings=24367)
        # Conflicting printed new listings (11,456 vs 11,956): left missing, not guessed.
        self.check('2005-07', new_listings=None, active_listings=22512, sales=7387)
        self.check('2011-07', layout='summary_no_trend', sales=7922, active_listings=17546)
        self.check('2012-01', layout='summary_dom', sales=4567, new_listings=9655)
        # Two overlapping text layers.
        self.check('2022-05', layout='summary_ldom_pdom', sales=7283, new_listings=18679, active_listings=15433)
