import unittest
from datetime import datetime,timezone
from housing.db import connect
from housing.research import as_known_at
from housing.backtest import run,shift
class BacktestTests(unittest.TestCase):
    def test_unknown_vintages_are_not_evaluable(self):
        db=connect(':memory:')
        result=run(db,datetime(2026,9,26,tzinfo=timezone.utc))
        self.assertEqual(len(result['results']),4)
        self.assertTrue(all(r['status']=='not_evaluable' and not r['accepted'] for r in result['results']))
        self.assertEqual(shift('2025-01',-13),'2023-12')
        db.close()
    def test_official_time_not_local_version_selects_revision(self):
        db=connect(':memory:')
        db.execute("INSERT INTO raw_files(sha256,source,path,source_url,retrieved_at,method) VALUES('hash','test','test','https://example.org','2026-09-26','fixture')")
        for version,published,value,evidence in [(1,'2026-09-10T00:00:00+00:00',100,'official'),(2,'2026-09-05T00:00:00+00:00',90,'archive'),(3,'2026-09-15T00:00:00+00:00',999,' '),(4,'2026-10-01T00:00:00+00:00',999,'future')]:
            db.execute('INSERT INTO observations(series_id,period,value,version,raw_sha256,first_seen_at,published_at,availability_evidence) VALUES(?,?,?,?,?,?,?,?)',('trreb_sales','2026-08',value,version,'hash','2026-09-26',published,evidence))
        self.assertEqual(as_known_at(db,'trreb_sales','2026-08',datetime(2026,9,26,tzinfo=timezone.utc))['value'],100)
        db.close()
    def test_mature_evidenced_fixture_exercises_metrics(self):
        db=connect(':memory:')
        db.execute("INSERT INTO raw_files VALUES (?,?,?,?,?,?,?)",('hash','fixture','test','https://example.org','2026-09-26',None,'synthetic'))
        for index in range(48):
            period=shift('2022-09',index)
            publication=shift(period,1)+'-05T00:00:00+00:00'
            for target in ['trreb_sales','trreb_hpi_benchmark']:
                db.execute('INSERT INTO observations(series_id,period,value,version,raw_sha256,first_seen_at,published_at,availability_evidence) VALUES(?,?,?,?,?,?,?,?)',(target,period,100+index,1,'hash',publication,publication,'synthetic official evidence'))
        result=run(db,datetime(2026,9,26,tzinfo=timezone.utc))
        self.assertTrue(all(r['status']=='experimental' for r in result['results']))
        for r in result['results']:
            self.assertGreater(r['metrics']['no_change']['all_origins']['n'], r['metrics']['no_change']['non_overlapping']['n'])
            self.assertGreater(len(r['excluded']),0)  # Outcomes not yet mature stay excluded.
        db.close()
