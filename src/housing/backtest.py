"""Frozen point-in-time baseline experiment. Unknown vintages never become facts."""
import calendar
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from .research import as_known_at

PROTOCOL = json.loads(Path(__file__).with_name('research_protocol.json').read_text())

def shift(period, months):
    y,m=map(int,period.split('-')); n=y*12+m-1+months
    return f'{n//12:04d}-{n%12+1:02d}'

def cutoff(period):
    y,m=map(int,period.split('-'))
    return datetime(y,m,calendar.monthrange(y,m)[1],23,59,59,tzinfo=ZoneInfo('America/Toronto'))

def first_publication(db, series, period, asof):
    rows=db.execute('SELECT * FROM observations WHERE series_id=? AND period=? AND published_at IS NOT NULL AND availability_evidence IS NOT NULL',(series,period)).fetchall()
    eligible=[]
    for r in rows:
        if not r['availability_evidence'].strip():continue
        t=datetime.fromisoformat(r['published_at'])
        if t.tzinfo is None:raise ValueError('publication must have timezone')
        if t<=asof:eligible.append((t,r))
    return min(eligible,key=lambda x:x[0])[1] if eligible else None

def run(db, asof):
    if asof.tzinfo is None:raise ValueError('asof must have timezone')
    results=[]
    for target in PROTOCOL['targets']:
        periods=[r[0] for r in db.execute('SELECT DISTINCT period FROM observations WHERE series_id=? ORDER BY period',(target,))]
        for horizon in PROTOCOL['horizons_months']:
            accepted=[];excluded=[]
            for origin in periods:
                if origin<PROTOCOL['test_start'] or cutoff(origin)>asof:continue
                known=as_known_at(db,target,shift(origin,-1),cutoff(origin))
                lag=as_known_at(db,target,shift(origin,-4),cutoff(origin))
                prior=as_known_at(db,target,shift(origin,-13),cutoff(origin))
                seasonal=as_known_at(db,target,shift(origin,horizon-13),cutoff(origin))
                start=first_publication(db,target,origin,asof)
                end=first_publication(db,target,shift(origin,horizon),asof)
                # Frozen rules have no fitted parameters; still require historical
                # mature outcomes before the training boundary for feasibility.
                training=sum(1 for p in periods if shift(p,horizon)<=PROTOCOL['training_end']
                    and first_publication(db,target,p,cutoff(PROTOCOL['training_end'])) is not None
                    and first_publication(db,target,shift(p,horizon),cutoff(PROTOCOL['training_end'])) is not None)
                if not all(r is not None for r in [known,lag,prior,seasonal,start,end]) or training<PROTOCOL['minimum_training_samples']:
                    excluded.append({'origin':origin,'reason':'missing_evidenced_vintage_or_mature_training'});continue
                if min(r['value'] for r in [known,lag,prior,start])<=0:
                    excluded.append({'origin':origin,'reason':'nonpositive_denominator'});continue
                actual=100*(end['value']/start['value']-1)
                predictions={'no_change':0,'seasonal_naive':100*(seasonal['value']/prior['value']-1),
                             'momentum':100*((known['value']/lag['value'])**(horizon/3)-1)}
                accepted.append({'origin':origin,'actual':actual,'predictions':predictions})
            metrics={};band=PROTOCOL['neutral_band_pct'][target]
            def direction(x):return 1 if x>band else -1 if x < -band else 0
            for model in ['no_change','seasonal_naive','momentum']:
                def evaluate(rows):
                    n=len(rows)
                    return {'n':n,'mae_pp':sum(abs(r['predictions'][model]-r['actual']) for r in rows)/n if n else None,
                      'direction_accuracy':sum(direction(r['predictions'][model])==direction(r['actual']) for r in rows)/n if n else None,
                      'false_up':sum(direction(r['predictions'][model])==1 and direction(r['actual'])!=1 for r in rows),
                      'missed_up':sum(direction(r['predictions'][model])!=1 and direction(r['actual'])==1 for r in rows)}
                independent=[]
                for r in accepted:
                    if not independent or r['origin']>=shift(independent[-1]['origin'],horizon):independent.append(r)
                metrics[model]={'all_origins':evaluate(accepted),'non_overlapping':evaluate(independent)}
            results.append({'target':target,'horizon_months':horizon,'status':'experimental' if len(accepted)>=PROTOCOL['minimum_test_samples'] else 'not_evaluable',
                            'metrics':metrics,'accepted':accepted,'excluded':excluded})
    return {'protocol_version':PROTOCOL['version'],'asof':asof.isoformat(),'decision':'retain_experiment_not_for_prediction','results':results}
