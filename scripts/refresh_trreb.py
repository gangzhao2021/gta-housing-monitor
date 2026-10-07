"""Append newly published monthly reports; never rewrite existing headline CSVs."""
import csv
import fcntl
import hashlib
import io
import json
import sqlite3
import subprocess
import sys
from datetime import date,datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts.extract_trreb import extract
from scripts.download_trreb import months
from housing.db import connect
from housing.ingest import ingest,register_raw,parse_trreb
from housing.districts import import_csv
from housing.breakdowns import trreb_hpi_breakdown
from housing.trreb_yoy import rows_for as yoy_rows
FIELDS=['period','geography','home_type','sales','new_listings','active_listings','hpi_composite','hpi_benchmark','source_pdf_sha256','sales_page','hpi_page','source_pdf_name']

def run():
    today=date.today();index=today.year*12+today.month-2
    end=f'{index//12:04d}-{index%12+1:02d}'
    report={'through':end,'downloaded':[],'pending':[],'headline_inserted':0}
    with (ROOT/'data/.refresh-official.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        db=connect(ROOT/'data/housing.sqlite3')
        try:
            backup=ROOT/'data/backups'/('trreb-before-'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.sqlite3')
            backup.parent.mkdir(parents=True,exist_ok=True)
            target=sqlite3.connect(backup)
            try:db.backup(target)
            finally:target.close()
            backup.chmod(0o600)
            for y,m in months('2022-09',end):
                period=f'{y:04d}-{m:02d}';pdf=ROOT/'data/raw/trreb'/f'mw{y%100:02d}{m:02d}.pdf'
                url='https://trreb.ca/wp-content/files/market-stats/market-watch/'+pdf.name
                if not pdf.exists():
                    try:
                        with urlopen(url,timeout=45) as response:content=response.read()
                    except HTTPError as exc:
                        if exc.code==404 and period==end:
                            report['pending'].append(period);continue
                        raise
                    if not content.startswith(b'%PDF-'):raise ValueError('Expected official PDF')
                    temporary=pdf.with_suffix('.download');temporary.write_bytes(content);temporary.chmod(0o600);temporary.replace(pdf)
                    report['downloaded'].append(period)
                # Existing observations are left untouched. Revisions require a
                # separately reviewed source, never an older archive replay.
                if db.execute("SELECT 1 FROM observations WHERE series_id='trreb_sales' AND period=?",(period,)).fetchone():continue
                record=extract(pdf);buffer=io.StringIO(newline='');writer=csv.writer(buffer);writer.writerow(FIELDS);writer.writerow(record)
                content=buffer.getvalue();sha=hashlib.sha256(content.encode()).hexdigest()[:10]
                path=ROOT/'data/manual'/f'trreb-extracted-{period}-to-{period}-{sha}.csv'
                if not path.exists():path.write_text(content)
                with db:register_raw(db,pdf,'TRREB',url,period,'official monthly PDF')
                result=ingest(db,'TRREB',path,url,period,'existing headline extractor',parse_trreb(path,pdf))
                report['headline_inserted']+=result.get('inserted',0)
                stored={s:v for s,v in db.execute("SELECT series_id,value FROM observations WHERE period=? AND series_id IN ('trreb_sales','trreb_new_listings','trreb_active_listings')",(period,))}
                rows=yoy_rows(pdf,period,stored,trreb_hpi_breakdown(pdf))
                if rows:
                    result=ingest(db,'TRREB',pdf,url,period,'published YoY from front page and HPI page; checked against printed amounts',rows)
                    report['yoy_inserted']=report.get('yoy_inserted',0)+result.get('inserted',0)
            latest=db.execute("SELECT MAX(period) FROM observations WHERE series_id='trreb_sales'").fetchone()[0]
            exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='district_observations'").fetchone()
            district_end=db.execute('SELECT MAX(ym) FROM district_observations').fetchone()[0] if exists else None
            if latest and district_end!=latest:
                result=subprocess.run([sys.executable,str(ROOT/'scripts/extract_trreb_districts.py'),'2022-09',latest],cwd=ROOT,capture_output=True,text=True,timeout=300)
                if result.returncode or 'PROBLEM' in result.stdout or 'warning' in (result.stdout+result.stderr).lower():raise RuntimeError('District extraction failed: '+result.stdout[-2000:]+result.stderr[-2000:])
                candidates=list((ROOT/'data/manual').glob(f'trreb-districts-2022-09-to-{latest}-*.csv'))
                if not candidates:raise ValueError('District export missing')
                path=max(candidates,key=lambda p:p.stat().st_mtime_ns)
                check=subprocess.run([sys.executable,str(ROOT/'scripts/check_trreb_districts.py'),str(path)],cwd=ROOT,capture_output=True,text=True,timeout=300)
                if check.returncode:raise RuntimeError('District independent audit failed: '+check.stderr)
                report['districts']=import_csv(db,path,ROOT)
        finally:db.close()
    return report
if __name__=='__main__':print(json.dumps(run()))
