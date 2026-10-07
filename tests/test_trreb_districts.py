import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import extract_trreb_districts as extractor
from scripts import extract_trreb

ROOT = Path(__file__).resolve().parents[1]
SEPTEMBER_2026 = ROOT / 'data/raw/trreb/mw2609.pdf'


class DistrictExtractorTests(unittest.TestCase):
    def test_period_validation_and_inclusive_months(self):
        self.assertEqual(list(extractor.months_between('2022-12', '2023-02')),
                         [(2022, 12), (2023, 1), (2023, 2)])
        for start, end in [('2023-13', '2024-01'), ('2023-02', '2023-01')]:
            with self.assertRaises(ValueError):
                list(extractor.months_between(start, end))

    def test_price_check_uses_rounding_tolerance_and_requires_positive_sales_amount(self):
        self.assertTrue(extractor.row_ok(dict(sales=2, dollar_volume=201, average_price=101)))
        self.assertFalse(extractor.row_ok(dict(sales=2, dollar_volume=201, average_price=102)))
        self.assertFalse(extractor.row_ok(dict(sales=2, dollar_volume=None, average_price=101)))
        self.assertTrue(extractor.row_ok(dict(sales=0, dollar_volume=None, average_price=None)))

    def test_missing_pdf_fails_without_creating_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(extractor, 'RAW', root / 'raw'), patch.object(extractor, 'OUT', root / 'manual'), \
                 patch('sys.argv', ['extract', '2022-09', '2022-09']), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    extractor.main()
            self.assertEqual(result.exception.code, 1)
            self.assertEqual(list((root / 'manual').glob('*.csv')), [])

    def test_september_2026_layout_keeps_all_sections_and_region_names(self):
        problems = []
        by_type = extractor.scan_pdf(SEPTEMBER_2026, '2026-09', problems)
        self.assertEqual(problems, [])
        self.assertEqual(set(by_type), {'all_types', *extractor.HOME_TYPE_SLUGS.values()})
        rows = {row['area']: row for row in by_type['all_types']}
        # Ligature glyphs are normalized to the names stored for earlier months.
        self.assertIn('Stouffville', rows)
        self.assertIn('Dufferin County', rows)
        self.assertEqual(len(rows), 76)
        total = rows['All TRREB Areas']
        self.assertEqual((total['sales'], total['new_listings'], total['active_listings'], total['avg_sp_lp'], total['avg_ldom']),
                         (5040, 16500, 26131, 98.0, 34))
        self.assertEqual(sum(rows[area]['sales'] for area in extractor.TOP_LEVEL_AREAS), 5040)

    def test_september_2026_headline_matches_front_page_summary(self):
        record = extract_trreb.extract(SEPTEMBER_2026)
        self.assertEqual(record[:8], ['2026-09', 'All TRREB Areas', 'All Home Types', 5040, 16500, 26131, 291.0, 917600])
        self.assertEqual(record[9:11], [3, 25])
        with patch.object(extract_trreb, 'front_summary', return_value={'Sales': 5040, 'New Listings': 16500,
                                                                       'Active Listings': 26130}):
            with self.assertRaisesRegex(ValueError, 'front-page summary'):
                extract_trreb.extract(SEPTEMBER_2026)
