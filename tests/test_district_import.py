import csv
import hashlib
import tempfile
import unittest
from pathlib import Path
from housing.db import connect
from housing.districts import FIELDS, import_csv, display_rows
from housing.publication import build_display_snapshot, validate_display_snapshot

class DistrictImportTests(unittest.TestCase):
    def test_idempotence_provenance_and_private_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'data/raw/trreb').mkdir(parents=True)
            pdf=root/'data/raw/trreb/mw2608.pdf';pdf.write_bytes(b'fixture')
            source=root/'district.csv'
            row=dict(ym='2026-08',house_type='all_types',region='Markham',
                     **{k:1 for k in FIELDS},source_pdf=pdf.name,
                     source_pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest())
            def write():
                with source.open('w') as f:
                    w=csv.DictWriter(f,fieldnames=row);w.writeheader();w.writerow(row)
            write()
            db=connect(root/'data/housing.sqlite3')
            self.assertEqual(import_csv(db,source,root)['inserted'],1)
            self.assertEqual(import_csv(db,source,root)['inserted'],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM observations').fetchone()[0],0)
            snapshot=validate_display_snapshot(build_display_snapshot(db))
            self.assertNotIn('source_pdf',snapshot['districts'][0])
            row['source_pdf_sha256']='0'*64;write()
            with self.assertRaisesRegex(ValueError,'hash mismatch'):import_csv(db,source,root)
            self.assertEqual(len(display_rows(db)),1)
            snapshot['districts'][0]['source_pdf']='/private/path'
            with self.assertRaises(ValueError):validate_display_snapshot(snapshot)
            db.close()
