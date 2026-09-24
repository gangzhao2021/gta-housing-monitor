import json
import tempfile
import unittest
from pathlib import Path
from housing.regional_ingest import parse_regional_csv, regional_cmhc_details
from housing.regional_view import export_rows
from housing.db import connect
from housing.regions import asking_id
from housing.ingest import ingest
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/rentals'

class RegionSourcesTests(unittest.TestCase):
    def test_regions_reconcile_and_do_not_mix_all_property_values(self):
        rows, url, _ = parse_regional_csv(RAW/'2026-08-report-apts-cities.csv', RAW/'2026-08-report-apts-cities.html')
        values = {s:v for s,_,v in rows}
        self.assertNotIn(asking_id('north_york','total'), values)
        self.assertEqual(values[asking_id('scarborough','1br')], 1906)
        self.assertEqual(values[asking_id('vaughan','2br')], 2586)
        self.assertEqual(len(rows),13)
        self.assertNotIn(asking_id('markham','total'),values)
        self.assertTrue(url.endswith('/4mt9H/1/'))

    def test_backfilled_totals_continuity_and_conflicting_city_total_excluded(self):
        from housing.presentation import calendar_periods
        observations = {}
        files = sorted(RAW.glob('*regions-history.csv')) + sorted(RAW.glob('*regions-cities.csv'))
        for path in files:
            for series, period, value in parse_regional_csv(path, path.with_suffix('.html'))[0]:
                observations.setdefault(series, {})[period] = value
        for region in ['markham', 'north_york', 'scarborough', 'vaughan', 'mississauga', 'oakville']:
            self.assertEqual(sorted(observations[asking_id(region, 'total')]), calendar_periods('2025-11', '2026-07'))
        self.assertEqual(observations[asking_id('markham', 'total')]['2025-11'], 2390)
        self.assertEqual(observations[asking_id('oakville', 'total')]['2026-04'], 2466)
        city = RAW/'2026-05-report-apts-cities.csv'
        rows = parse_regional_csv(city, city.with_suffix('.html'))[0]
        self.assertNotIn(asking_id('oakville', 'total'), {r[0] for r in rows})

    def test_backfilled_bedrooms_are_report_month_minus_one(self):
        from housing.rentals import parse_dataset
        path = RAW/'2025-12-report-bedrooms.csv'
        rows, _, _ = parse_dataset(path, path.with_suffix('.html'))
        self.assertEqual(rows, [('toronto_asking_rent_1br', '2025-11', 2237),
            ('toronto_asking_rent_2br', '2025-11', 2855), ('toronto_asking_rent_3br', '2025-11', 3499)])

    def test_incompatible_scope_and_duplicate_city_rejected(self):
        html = (RAW/'2026-08-report-apts-cities.html').read_text()
        csv = (RAW/'2026-08-report-apts-cities.csv').read_text()
        with tempfile.TemporaryDirectory() as directory:
            h,c = Path(directory)/'chart.html',Path(directory)/'data.csv'
            h.write_text(html.replace('Average Rent for Apartments &amp; Condos Only', 'Average Rent by City & Unit Type'))
            c.write_text(csv)
            with self.assertRaises(ValueError):parse_regional_csv(c,h)
            h.write_text(html)
            line = next(l for l in csv.splitlines() if ',North York,' in l)
            c.write_text(csv+'\n'+line)
            with self.assertRaises(ValueError):parse_regional_csv(c,h)

    def test_annual_grouped_geography_suppression_and_provenance(self):
        rows = regional_cmhc_details(ROOT/'data/raw/cmhc/rmr-toronto-2025-en.xlsx')
        self.assertEqual(len(rows),140)
        self.assertEqual({r['period'] for r in rows},{'2024','2025'})
        self.assertTrue(any(r['status']=='suppressed' and r['value'] is None for r in rows))
        groups = [r for r in rows if r['region']=='richmond_vaughan_king']
        self.assertTrue(all(r['source_zone']=='Zone 25 - Richmond Hill/Vaughan/King' for r in groups))
        self.assertTrue(all(r['quality'] in ['a','b','c','d'] for r in rows if r['value'] is not None))
        self.assertTrue(all(r['cell'] for r in rows))
