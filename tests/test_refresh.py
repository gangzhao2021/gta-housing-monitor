import hashlib
import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from housing.db import connect
from scripts.refresh_official import refresh_one, source_url


class OfficialRefreshTests(unittest.TestCase):
    def test_boc_refresh_preserves_source_and_skips_identical_bytes(self):
        document = {
            'seriesDetail': {key: {} for key in ('V39079', 'BD.CDN.5YR.DQ.YLD', 'V122667786')},
            'observations': [{'d': '2026-01-30', 'V39079': {'v': '2.25'},
                              'BD.CDN.5YR.DQ.YLD': {'v': '3.40'}, 'V122667786': {'v': '4.50'}}],
        }
        payload = json.dumps(document).encode()

        def fetcher(url, temporary):
            temporary.write_bytes(payload)
            return hashlib.sha256(payload).hexdigest()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = connect(root / 'data/housing.sqlite3')
            try:
                first = refresh_one(db, 'boc', root, date(2026, 2, 23), fetcher)
                second = refresh_one(db, 'boc', root, date(2026, 2, 23), fetcher)
                self.assertEqual(first['inserted'], 3)
                self.assertEqual(second['status'], 'unchanged')
                self.assertEqual(db.execute('SELECT COUNT(*) FROM observations').fetchone()[0], 3)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM raw_files').fetchone()[0], 1)
                with (root / 'data/raw/manifest.csv').open(newline='') as source:
                    registered = list(csv.DictReader(source))
                self.assertEqual(len(registered), 1)
                self.assertEqual(registered[0]['sha256'], first['sha256'])
                self.assertTrue(list((root / 'data/backups').glob('*.sqlite3')))
                self.assertEqual(db.execute("SELECT status FROM ingestion_runs ORDER BY id DESC LIMIT 1").fetchone()[0], 'unchanged')
            finally:
                db.close()

    def test_boc_check_uses_last_complete_month(self):
        self.assertIn('end_date=2026-08-31', source_url('boc', date(2026, 9, 23)))
