import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from housing import trreb_rental
from housing.catalog import SERIES
from housing.db import connect
from housing.publication import CONTEXT_SERIES

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'data/raw/trreb_rental'


class TrrebRentalTests(unittest.TestCase):
    def test_quarters_stop_at_last_completed_quarter(self):
        self.assertEqual(list(trreb_rental.quarters(date(2022, 10, 1))), [(2022, 3)])
        self.assertEqual(list(trreb_rental.quarters(date(2023, 1, 15)))[-1], (2022, 4))
        self.assertEqual(trreb_rental.period_for(2026, 2), '2026-04')

    def test_saved_reports_parse_with_bedroom_reconciliation(self):
        rows = dict((series, value) for series, _, value in
                    trreb_rental.parse_report(REPORTS / 'rental_report_Q2-2026.pdf', 2026, 2))
        self.assertEqual(rows, {'gta_condo_lease_listed': 27844, 'gta_condo_leased': 21251,
                                'gta_condo_lease_rent_bachelor': 1849, 'gta_condo_lease_rent_1br': 2273,
                                'gta_condo_lease_rent_2br': 3013, 'gta_condo_lease_rent_3br': 3779})
        # Original release; a later report's prior-year column is a revision.
        older = trreb_rental.parse_report(REPORTS / 'rental_report_Q2-2025.pdf', 2025, 2)
        self.assertIn(('gta_condo_leased', '2025-04', 20417.0), older)

    def test_wrong_quarter_and_shifted_row_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'quarter'):
            trreb_rental.parse_report(REPORTS / 'rental_report_Q2-2026.pdf', 2026, 1)
        shifted = iter([['27,844', '21,251', '976', '$1,849', '12,096', '$2,273', '7,373', '$3,013', '806']])
        with patch.object(trreb_rental, '_total_rows', side_effect=lambda page: shifted):
            with self.assertRaisesRegex(ValueError, 'Unexpected'):
                trreb_rental.parse_report(REPORTS / 'rental_report_Q2-2026.pdf', 2026, 2)

    def test_series_are_quarterly_context_and_stored_quarters_are_not_replayed(self):
        for series_id in trreb_rental.SERIES:
            self.assertEqual(SERIES[series_id][5], 'quarterly')
            self.assertIn(series_id, CONTEXT_SERIES)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'data/raw').mkdir(parents=True)
            (root / 'data/raw/trreb_rental').symlink_to(REPORTS, target_is_directory=True)
            db = connect(':memory:')
            source = sqlite3.connect(f"file:{ROOT / 'data/housing.sqlite3'}?mode=ro", uri=True)
            source.backup(db)
            source.close()
            fetched = []

            def unpublished(url):
                fetched.append(url)
                raise HTTPError(url, 404, 'Not Found', None, None)

            report = trreb_rental.refresh(db, root, date(2026, 10, 7), opener=unpublished)
            self.assertEqual((report['inserted'], report['downloaded'], report['pending']), (0, [], ['2026Q3']))
            self.assertEqual(fetched, [trreb_rental.URL.format(q=3, year=2026)])
            db.close()
