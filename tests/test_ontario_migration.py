import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from housing.db import connect
from housing.ontario_migration import derive_rows, parse_table, refresh_migration, table_url


def fixture(table, bad_coordinate=False):
    column = 'Interprovincial migration' if table == 'interprovincial' else 'Components of population growth'
    components = (
        [('In-migrants', 'v509048', '7.1', 100), ('Out-migrants', 'v509063', '7.2', 120)]
        if table == 'interprovincial' else
        [('Immigrants', 'v29850372', '7.1', 50),
         ('Net non-permanent residents', 'v29850376', '7.5', -10),
         ('Net emigration', 'v1566834794', '7.6', 5)]
    )
    fields = ['REF_DATE', 'GEO', 'DGUID', column, 'UOM', 'SCALAR_FACTOR',
              'VECTOR', 'VALUE', 'STATUS', 'COORDINATE']
    data = io.StringIO(newline='')
    writer = csv.DictWriter(data, fieldnames=fields)
    writer.writeheader()
    for period in ('2026-01', '2026-04'):
        for name, vector, coordinate, value in components:
            writer.writerow({'REF_DATE': period, 'GEO': 'Ontario', 'DGUID': '2021A000235',
                             column: name, 'UOM': 'Persons', 'SCALAR_FACTOR': 'units',
                             'VECTOR': vector, 'VALUE': value, 'STATUS': '',
                             'COORDINATE': '7.9' if bad_coordinate else coordinate})
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(table_url(table).rsplit('/', 1)[-1].replace('-eng.zip', '.csv'), data.getvalue())
    return buffer.getvalue()


class OntarioMigrationTests(unittest.TestCase):
    def test_official_components_and_negative_net_values(self):
        provincial = parse_table(fixture('interprovincial'), 'interprovincial')
        international = parse_table(fixture('international'), 'international')
        rows = derive_rows(provincial, international)
        self.assertEqual(rows[-2:], [('ontario_net_interprovincial_migration', '2026-04', -20.0),
                                     ('ontario_net_international_migration', '2026-04', 35.0)])

    def test_coordinate_drift_rejected(self):
        with self.assertRaisesRegex(ValueError, 'definition'):
            parse_table(fixture('international', bad_coordinate=True), 'international')

    def test_ingestion_idempotent_and_manifested(self):
        documents = {table_url(key): fixture(key) for key in ('interprovincial', 'international')}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            db = connect(root / 'data/housing.sqlite3')
            first = refresh_migration(db, root, documents.__getitem__)
            second = refresh_migration(db, root, documents.__getitem__)
            self.assertEqual((first['status'], second['status']), ('success', 'unchanged'))
            self.assertTrue(Path(first['csv']).exists())
            self.assertTrue((root / 'data/raw/manifest.csv').exists())
            self.assertEqual(db.execute("SELECT COUNT(*) FROM observations WHERE series_id LIKE 'ontario_net_%'").fetchone()[0], 4)
            db.close()


if __name__ == '__main__':
    unittest.main()
