import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import extract_trreb_districts as extractor


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
