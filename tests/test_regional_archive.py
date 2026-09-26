"""Source-evidence checks for manually transcribed historical rental charts."""
import csv
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("regional_archive", ROOT / "scripts/import_regional_archive.py")
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


class RegionalArchiveTests(unittest.TestCase):
    def test_transcript_matches_saved_charts_and_preserves_gaps(self):
        sources = archive.load_rows(ROOT / "docs/RENTAL_REGIONAL_ARCHIVE.csv")
        self.assertEqual(len(sources), 21)
        self.assertEqual(sum(len(rows) for rows in sources.values()), 125)
        periods = {key[0] for key in sources}
        self.assertTrue({'2024-02', '2024-04'} <= periods)
        self.assertNotIn('2024-09', periods)
        july = next(rows for key, rows in sources.items() if key[0] == '2024-07')
        self.assertEqual(len(july), 5)
        self.assertNotIn('regional_asking_markham_total', {row[0] for row in july})

    def test_tampered_image_hash_is_rejected(self):
        source = ROOT / "docs/RENTAL_REGIONAL_ARCHIVE.csv"
        with source.open(newline='', encoding='utf-8') as handle:
            rows = list(csv.DictReader(handle))
        rows[0]['image_sha256'] = '0' * 64
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            altered = Path(directory) / 'archive.csv'
            with altered.open('w', newline='', encoding='utf-8') as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                archive.load_rows(altered)


if __name__ == '__main__':
    unittest.main()
