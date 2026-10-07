"""Additional official background series; source snapshots are not vintage history."""
import csv
import hashlib
import json
import time
from calendar import monthrange
from datetime import date, datetime
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

WDS = 'https://www150.statcan.gc.ca/t1/wds/rest/'
START = '2022-09'
CONFIG = {
    'boc_prime': dict(id='boc_prime_rate', label='特许银行最优惠贷款利率', source='BoC prime', vector='V80691311', title='Prime rate', unit='%', geo='Canada', definition='每月最后有效周三报价；不是央行政策利率'),
    'boc_conventional_mortgage': dict(id='boc_conventional_mortgage_5y', label='传统五年期按揭公布利率', source='BoC conventional mortgage', vector='V80691335', title='Conventional mortgage, 5-year', unit='%', geo='Canada', definition='每月最后有效周三报价；不是新增贷款金额加权实际利率'),
    'toronto_nhpi': dict(id='toronto_nhpi_total', label='Toronto 新房价格指数（房屋及土地）', source='StatsCan NHPI', vector=111955499, table=18100205, coordinate='20.1.0.0.0.0.0.0.0.0', title='Toronto, Ontario;Total (house and land)', uom=347, unit='index, 2016=100', geo='Toronto CMA 2011 boundary', definition='新建住宅房屋与土地综合指数；非转售 HPI，非全部 condo 市场'),
    'ontario_shelter': dict(id='ontario_cpi_shelter', label='Ontario 居住成本 CPI', source='StatsCan shelter CPI', vector=41691952, table=18100004, coordinate='14.79.0.0.0.0.0.0.0.0', title='Ontario;Shelter', uom=17, unit='index, 2002=100', geo='Ontario', definition='居住消费成本指数，包含租金和自有住房成本；不是房价指数'),
    'toronto_permits_archive': dict(id='toronto_permits_units_34100066', label='Toronto 住宅许可新增单位（停更历史表）', source='StatsCan permits archive', vector=122233956, table=34100066, coordinate='45.4.1.2.1.0.0.0.0.0', title='Toronto, Ontario;Total residential;Types of work, total;Number of dwelling-units created;Unadjusted, current', uom=223, unit='units', geo='Toronto CMA 2011 boundary', definition='住宅总体、全部工作类型、新增住宅单位；表于 2023-10 停更，独立保存不拼接', archived=True),
    'cmhc_absorptions': dict(id='toronto_cmhc_absorptions', label='Toronto 新建完工住宅吸纳量', source='StatsCan CMHC absorptions', vector=1930492, table=34100149, coordinate='24.1.1.0.0.0.0.0.0.0', title='Toronto, Ontario;Absorptions;Total units', uom=300, unit='units', geo='Toronto CMA 2011 boundary', definition='CMHC 吸纳调查：当月完工的自住及 condo 项目中已售出套数，预售单位在完工时计入；不含专建出租，不是转售成交'),
    'cmhc_unabsorbed': dict(id='toronto_cmhc_unabsorbed_inventory', label='Toronto 新建完工未吸纳库存', source='StatsCan CMHC absorptions', vector=1930777, table=34100149, coordinate='24.2.1.0.0.0.0.0.0.0', title='Toronto, Ontario;Unabsorbed inventory;Total units', uom=300, unit='units', geo='Toronto CMA 2011 boundary', definition='CMHC 吸纳调查：已完工但未售出的自住及 condo 新房套数；不含在建预售未售单位和专建出租，不是转售挂牌'),
    'starts_condo': dict(id='toronto_starts_condo', label='Toronto 开工量：condo 市场', source='StatsCan CMHC starts by market', vector=1459027, table=34100148, coordinate='35.1.3.0.0.0.0.0.0.0', title='Toronto, Ontario;Total units;Condo', uom=300, unit='units', geo='Toronto CMA 2011 boundary', definition='CMHC 开工调查中预定为 condo 产权出售的住宅单位；与专建出租、自住市场分列，三者合计等于总开工（另有少量合作社／其他）'),
    'starts_rental': dict(id='toronto_starts_rental', label='Toronto 开工量：专建出租', source='StatsCan CMHC starts by market', vector=1458998, table=34100148, coordinate='35.1.2.0.0.0.0.0.0.0', title='Toronto, Ontario;Total units;Rental', uom=300, unit='units', geo='Toronto CMA 2011 boundary', definition='CMHC 开工调查中预定为专建出租的住宅单位；不含业主出租的 condo'),
    'starts_homeowner': dict(id='toronto_starts_homeowner', label='Toronto 开工量：自住市场', source='StatsCan CMHC starts by market', vector=1458969, table=34100148, coordinate='35.1.1.0.0.0.0.0.0.0', title='Toronto, Ontario;Total units;Homeowner', uom=300, unit='units', geo='Toronto CMA 2011 boundary', definition='CMHC 开工调查中预定为非 condo 产权出售或自建的住宅单位（主要为低层）'),
    'canada_epu': dict(id='canada_policy_uncertainty', label='加拿大经济政策不确定性指数', source='Baker-Bloom-Davis EPU (FRED)', fred='CANEPUINDXM', vector='CANEPUINDXM', title='Economic Policy Uncertainty Index for Canada', unit='index', geo='Canada', definition='按加拿大主要报纸中同时提及经济、政策与不确定性的文章比例编制的月度指数（Baker、Bloom、Davis），新闻计数口径，波动大；只作不确定性背景，不是房价预测'),
    'toronto_permits': dict(id='toronto_permits_units', label='Toronto 住宅许可新增单位', source='StatsCan permits', vector=1675206466, table=34100292, coordinate='45.4.1.2.1.0.0.0.0.0', title='Toronto, Ontario;Total residential;Types of work, total;Number of dwelling-units created;Unadjusted, current', uom=223, unit='units', geo='Toronto CMA 2011 boundary', definition='现行后继表 34-10-0292；住宅总体、全部工作类型、新增住宅单位；不是许可证张数、净增量、开工或竣工'),
}


def url_for(config):
    if 'fred' in config:
        return f'https://fred.stlouisfed.org/series/{config["fred"]}'
    if 'table' in config:
        return f'https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={config["table"]}01'
    return f'https://www.bankofcanada.ca/valet/observations/{config["vector"]}/json'


def request_json(url, payload=None):
    request = Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                      headers={'Content-Type': 'application/json', 'User-Agent': 'TorontoHousingMonitor/0.1'})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=90) as response:
                return json.load(response)
        except (OSError, ValueError):
            if attempt == 2:
                raise
            time.sleep(0.5 * 2 ** attempt)


def successful(document):
    if len(document) != 1 or document[0].get('status') != 'SUCCESS':
        raise ValueError('WDS request did not return one successful series')
    obj = document[0]['object']
    if obj.get('responseStatusCode') != 0:
        raise ValueError('WDS response status is not successful')
    return obj


def request_text(url):
    request = Request(url, headers={'User-Agent': 'TorontoHousingMonitor/0.1'})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=90) as response:
                return response.read().decode('utf-8')
        except OSError:
            if attempt == 2:
                raise
            time.sleep(0.5 * 2 ** attempt)


def parse_snapshot(document, config, end):
    rows = []
    if 'fred' in config:
        lines = document['data']['csv'].strip().splitlines()
        if lines[0].strip() != f'observation_date,{config["fred"]}':
            raise ValueError('FRED series header changed')
        for line in lines[1:]:
            day, value = line.strip().split(',')
            datetime.strptime(day, '%Y-%m-%d')
            if not day.endswith('-01'):
                raise ValueError('Expected monthly FRED observations')
            if START <= day[:7] <= end and value not in ('', '.'):
                rows.append((config['id'], day[:7], float(value)))
    elif 'table' not in config:
        detail = document['data'].get('seriesDetail', {}).get(config['vector'], {})
        if detail.get('label') != config['title']:
            raise ValueError('BoC series definition changed')
        months = {}
        for item in sorted(document['data']['observations'], key=lambda row: row['d']):
            datetime.strptime(item['d'], '%Y-%m-%d')
            value = item.get(config['vector'], {}).get('v')
            if START <= item['d'][:7] <= end and value not in (None, ''):
                months[item['d'][:7]] = float(value)
        rows = [(config['id'], period, value) for period, value in sorted(months.items())]
    else:
        meta = successful(document['metadata'])
        data = successful(document['data'])
        for obj in (meta, data):
            if any(obj.get(key) != config[field] for key, field in (
                    ('productId', 'table'), ('vectorId', 'vector'), ('coordinate', 'coordinate'))):
                raise ValueError('WDS vector/table/coordinate mismatch')
        if (meta['SeriesTitleEn'] != config['title'] or meta['frequencyCode'] != 6
                or meta['memberUomCode'] != config['uom'] or meta['scalarFactorCode'] != 0):
            raise ValueError('WDS geography, measure, unit or frequency changed')
        for point in data['vectorDataPoint']:
            period = point['refPer']
            datetime.strptime(period, '%Y-%m-%d')
            if not period.endswith('-01'):
                raise ValueError('Expected monthly reference period')
            if not START <= period[:7] <= end:
                continue
            # Suppressed/unavailable values remain absent, never zero or interpolated.
            if point['value'] is None or point.get('securityLevelCode', 0) != 0:
                continue
            if point['scalarFactorCode'] != 0 or point['frequencyCode'] != 6:
                raise ValueError('WDS datapoint scale/frequency changed')
            if point['statusCode'] != 0:
                raise ValueError(f'Unexpected numeric WDS status: {point["statusCode"]}')
            rows.append((config['id'], period[:7], float(point['value'])))
    if not rows or len({row[1] for row in rows}) != len(rows):
        raise ValueError('Empty series or duplicate reference periods')
    return rows


def refresh_background(db, key, root, today=None, requester=request_json, text_requester=None):
    from .ingest import ingest, register_raw, validate_rows, now
    from .manifest import write_manifest
    from .catalog import SERIES
    today = today or datetime.now(ZoneInfo('America/Toronto')).date()
    year, month = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
    end = f'{year:04d}-{month:02d}'
    config = CONFIG[key]
    source = config['source']
    root = Path(root)
    try:
        if 'fred' in config:
            url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={config["fred"]}'
            document = {'data': {'csv': (text_requester or request_text)(url)}}
        elif 'table' in config:
            meta = requester(WDS + 'getSeriesInfoFromVector', [{'vectorId': config['vector']}])
            count = (year - 2022) * 12 + month - 9 + 1
            data = requester(WDS + 'getDataFromVectorsAndLatestNPeriods',
                             [{'vectorId': config['vector'], 'latestN': max(count + 2, 1)}])
            document = {'metadata': meta, 'data': data}
        else:
            url = url_for(config) + f'?start_date={START}-01&end_date={end}-{monthrange(year, month)[1]}'
            document = {'data': requester(url)}
        raw = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2).encode()
        sha = hashlib.sha256(raw).hexdigest()
        directory = root / 'data/raw/background'
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f'{key}-{sha[:12]}.json'
        if not path.exists():
            path.write_bytes(raw)
        elif hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError('Existing source snapshot hash mismatch')
        # An identical snapshot already ingested successfully needs no new backup or batch.
        if db.execute("SELECT 1 FROM ingestion_runs WHERE raw_sha256=? AND source=? AND status='success' LIMIT 1",
                      (sha, source)).fetchone():
            with db:
                db.execute('INSERT INTO ingestion_runs (source,started_at,status,raw_sha256) VALUES (?,?,?,?)',
                           (source, now(), 'unchanged', sha))
            return {'source': key, 'status': 'unchanged', 'sha256': sha}
        rows = parse_snapshot(document, config, end)
        validate_rows(rows)
        # Only this extractor's declared series is allowed to enter the batch.
        if any(row[0] != config['id'] or row[0] not in SERIES for row in rows):
            raise ValueError('Unexpected series in background batch')
        destination = root / 'data/manual' / f'{key}-{sha[:12]}.csv'
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix('.tmp')
        with temporary.open('w', newline='', encoding='utf-8') as output:
            writer = csv.writer(output)
            writer.writerow(['series_id', 'period', 'value', 'source_url', 'source_sha256'])
            writer.writerows((*row, url_for(config), sha) for row in rows)
        temporary.replace(destination)
        backup_path = root / 'data/backups' / f'background-before-{key}-{datetime.now().strftime("%Y%m%dT%H%M%S%f")}.sqlite3'
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        import sqlite3
        target = sqlite3.connect(backup_path)
        try:
            db.backup(target)
        finally:
            target.close()
        result = ingest(db, source, path, url_for(config), f'{rows[0][1]}/{rows[-1][1]}',
                        'official API snapshot; verified metadata; no historical vintage inference', rows)
        with db:
            register_raw(db, destination, source, url_for(config), f'{rows[0][1]}/{rows[-1][1]}',
                         f'derived CSV from source SHA256 {sha}')
        write_manifest(db, root)
        return {'source': key, 'csv': str(destination), 'count': len(rows), **result}
    except Exception as exc:
        with db:
            db.execute('INSERT INTO ingestion_runs(source,started_at,status,error) VALUES (?,?,?,?)',
                       (source, now(), 'failed', str(exc)))
        raise


def extractor_main(key):
    import fcntl
    from .db import connect
    root = Path(__file__).resolve().parents[2]
    (root / 'data').mkdir(exist_ok=True)
    with (root / 'data/.refresh-official.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        db = connect(root / 'data/housing.sqlite3')
        try:
            print(json.dumps(refresh_background(db, key, root), ensure_ascii=False))
        finally:
            db.close()
