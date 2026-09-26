import copy
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from housing.background_series import CONFIG, parse_snapshot, refresh_background
from housing.db import connect
from housing.freshness import assess
from housing.ingest import ingest
from housing.publication import DISPLAY_SERIES, CONTEXT_SERIES


def wds_fixture():
    c = CONFIG['toronto_nhpi']
    info = dict(responseStatusCode=0, productId=c['table'], vectorId=c['vector'],
                coordinate=c['coordinate'], SeriesTitleEn=c['title'], frequencyCode=6,
                memberUomCode=c['uom'], scalarFactorCode=0)
    point = dict(refPer='2026-08-01', value=106.0, securityLevelCode=0,
                 scalarFactorCode=0, frequencyCode=6, statusCode=0)
    return {'metadata': [{'status': 'SUCCESS', 'object': info}],
            'data': [{'status': 'SUCCESS', 'object': {**info, 'vectorDataPoint': [point]}}]}


class BackgroundSeriesTests(unittest.TestCase):
    def test_wrong_geography_vector_unit_and_scale_rejected(self):
        for key, value in [('SeriesTitleEn', 'Canada;Total (house and land)'),
                           ('vectorId', 111955442), ('memberUomCode', 17), ('scalarFactorCode', 3)]:
            doc = wds_fixture()
            doc['metadata'][0]['object'][key] = value
            with self.assertRaises(ValueError):
                parse_snapshot(doc, CONFIG['toronto_nhpi'], '2026-08')

    def test_suppression_does_not_become_zero_and_duplicate_fails(self):
        doc = wds_fixture()
        points = doc['data'][0]['object']['vectorDataPoint']
        points.append({**points[0], 'refPer': '2026-07-01', 'value': None, 'statusCode': 1})
        points.append({**points[0], 'refPer': '2026-06-01', 'value': 100, 'securityLevelCode': 1})
        self.assertEqual(parse_snapshot(doc, CONFIG['toronto_nhpi'], '2026-08'),
                         [('toronto_nhpi_total', '2026-08', 106.0)])
        points.append(copy.deepcopy(points[0]))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            parse_snapshot(doc, CONFIG['toronto_nhpi'], '2026-08')

    def test_weekly_quotes_use_last_observation_not_average_or_partial_month(self):
        c = CONFIG['boc_prime']
        doc = {'data': {'seriesDetail': {c['vector']: {'label': c['title']}},
                       'observations': [{'d': d, c['vector']: {'v': v}} for d, v in
                                        [('2026-08-26', '5.0'), ('2026-08-05', '6.0'), ('2026-09-02', '4.0')]]}}
        self.assertEqual(parse_snapshot(doc, c, '2026-08'), [('boc_prime_rate', '2026-08', 5.0)])

    def test_ingestion_is_idempotent_keeps_existing_observations_and_manifest(self):
        document = wds_fixture()
        def requester(url, payload=None):
            return document['metadata' if url.endswith('getSeriesInfoFromVector') else 'data']
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            db = connect(root / 'data/housing.sqlite3')
            old_file = root / 'old.txt'
            old_file.write_text('baseline')
            ingest(db, 'BoC', old_file, 'https://example.test', '2026-08-01', 'fixture',
                   [('boc_policy_rate', '2026-08-01', 3.0)])
            old = tuple(db.execute('SELECT * FROM observations').fetchone())
            first = refresh_background(db, 'toronto_nhpi', root, date(2026, 9, 26), requester)
            second = refresh_background(db, 'toronto_nhpi', root, date(2026, 9, 26), requester)
            self.assertEqual((first['inserted'], second['unchanged'], second['revised']), (1, 1, 0))
            self.assertEqual(tuple(db.execute('SELECT * FROM observations WHERE id=1').fetchone()), old)
            self.assertTrue(Path(first['csv']).exists())
            self.assertTrue((root / 'data/raw/manifest.csv').exists())
            self.assertEqual(assess(db, 'toronto_nhpi_total', date(2026, 9, 26))['status'], 'current')
            db.close()

    def test_management_rules_distinguish_archived_and_delayed_release(self):
        db = connect(':memory:')
        from housing.freshness import RULES, _due_date
        self.assertEqual(assess(db, 'toronto_permits_units_34100066')['status'], 'archived')
        self.assertEqual(_due_date(RULES['toronto_permits_units'].release_rule, '2026-08'), date(2026, 10, 31))
        for c in CONFIG.values():
            self.assertIn(c['id'], RULES)
            self.assertNotIn(c['id'], DISPLAY_SERIES | CONTEXT_SERIES)
        db.close()


if __name__ == '__main__':
    unittest.main()
