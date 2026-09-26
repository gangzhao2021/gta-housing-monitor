"""Run the frozen research protocol; missing evidence yields not_evaluable."""
import json
import sqlite3
import sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from housing.backtest import run
if __name__=='__main__':
    db=sqlite3.connect(f'file:{ROOT / "data/housing.sqlite3"}?mode=ro',uri=True);db.row_factory=sqlite3.Row
    try:report=run(db,datetime.now(timezone.utc))
    finally:db.close()
    output=ROOT/'data/research/latest-backtest.json';output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');output.chmod(0o600)
    print(json.dumps({'report':str(output),'results':[{k:r[k] for k in ('target','horizon_months','status')} for r in report['results']]}))
