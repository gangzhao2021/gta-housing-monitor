import csv
import tempfile
import unittest
from pathlib import Path

from housing.db import connect
from housing.rentals import parse_dataset, import_dataset
from housing.freshness import assess
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/rentals'
REPORT = 'https://rentals.ca/blog/rentals-ca-august-2026-rent-report'


class RentalsTests(unittest.TestCase):
    def test_september_report_bedroom_chart_is_august_observation(self):
        csv_path = RAW / '2026-09-report-bedrooms.csv'
        html_path = RAW / '2026-09-report-bedrooms.html'
        rows, url, intro = parse_dataset(csv_path, html_path)
        self.assertEqual(url, 'https://datawrapper.dwcdn.net/7AZ1v/1/')
        self.assertIn('August 2026', intro)
        self.assertEqual(rows, [
            ('toronto_asking_rent_1br', '2026-08', 2229),
            ('toronto_asking_rent_2br', '2026-08', 2955),
            ('toronto_asking_rent_3br', '2026-08', 3642),
        ])
        db = connect(':memory:')
        self.addCleanup(db.close)
        report = 'https://rentals.ca/national-rent-report'
        self.assertEqual(import_dataset(db, csv_path, html_path, report)['inserted'], 3)
        self.assertEqual(import_dataset(db, csv_path, html_path, report)['unchanged'], 3)

    def test_real_source_periods_values_and_idempotence(self):
        csv_path, chart_path = (RAW / f'2026-08-report-history.{ext}' for ext in ['csv', 'html'])
        rows, _, _ = parse_dataset(csv_path, chart_path)
        self.assertEqual(len(rows), 49)
        self.assertEqual(rows[0][1:], ('2022-07', 2555))
        self.assertEqual(rows[-1][1:], ('2026-07', 2577))
        self.assertEqual(rows[-2][2], 2537)
        self.assertEqual(rows[-13][2], 2593)
        db = connect(':memory:')
        self.addCleanup(db.close)
        self.assertEqual(import_dataset(db, csv_path, chart_path, REPORT)['inserted'], 49)
        self.assertEqual(import_dataset(db, csv_path, chart_path, REPORT)['unchanged'], 49)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM raw_files').fetchone()[0], 2)
        self.assertEqual(assess(db, rows[0][0], date(2026, 9, 23))['status'], 'overdue')
        bedrooms, _, _ = parse_dataset(RAW / '2026-08-report-bedrooms.csv', RAW / '2026-08-report-bedrooms.html')
        self.assertEqual([r[1:] for r in bedrooms], [('2026-07', 2242), ('2026-07', 2956), ('2026-07', 3655)])

    def test_malformed_csv_fails_without_mutation(self):
        chart_path = RAW / '2026-08-report-history.html'
        text = (RAW / '2026-08-report-history.csv').read_text()
        variants = [text.replace('Toronto,', 'Wrong city,'), text + '\n' + text.splitlines()[1],
                    text.replace('2022-07-01,2555', '2022-07-01,nan'),
                    text.replace('2022-07-01', '2022-07-15'),
                    '\n'.join(text.splitlines()[:2] + text.splitlines()[3:])]
        with tempfile.TemporaryDirectory() as folder:
            for value in variants:
                path = Path(folder) / 'bad.csv'
                path.write_text(value)
                db = connect(':memory:')
                with self.assertRaises(ValueError):
                    import_dataset(db, path, chart_path, REPORT)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM observations').fetchone()[0], 0)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM raw_files').fetchone()[0], 0)
                db.close()
