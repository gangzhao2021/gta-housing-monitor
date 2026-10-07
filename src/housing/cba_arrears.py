"""Canadian Bankers Association: Ontario residential mortgages three or more months in arrears.

The CBA page links a monthly workbook whose name changes each release
(stat-mortgages-arrears-<month>-<year>-en.xlsx). The Ontario sheet holds two
column blocks of month-end rows: date (Excel serial), total mortgages, number in
arrears, share in arrears. Rates are stored as percentages and checked against
the two counts.
"""
import hashlib
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

from .xlsx import read

PAGE = 'https://cba.ca/article/mortgages-in-arrears?l=en-us'
BASE = 'https://cba.ca/Assets/CanadianBankersAssociation/Documents/Articles/Statistics/'
SOURCE = 'CBA mortgage arrears'
START = '2022-09'
SERIES = {
    'ontario_mortgage_arrears_rate': ('Ontario 银行按揭拖欠率', '%'),
    'ontario_mortgage_arrears_count': ('Ontario 银行按揭拖欠笔数', 'mortgages'),
}
DEFINITION = '加拿大银行家协会成员银行的 Ontario 住宅按揭中，还款逾期 3 个月及以上的笔数与占比；不含信用社和私人贷款'


def _get(url):
    with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60) as response:
        return response.read()


def latest_workbook_url(fetch=_get):
    names = sorted(set(re.findall(rb'stat-mortgages-arrears-[a-z]+-\d{4}-en\.xlsx', fetch(PAGE))))
    if len(names) != 1:
        raise ValueError(f'Expected one arrears workbook link, found {names}')
    return BASE + names[0].decode()


def parse(path, start=START):
    workbook = read(path)
    sheet, summary = workbook.get('ON'), workbook.get('Summary', {})
    if sheet is None or 'ONTARIO' not in ' '.join(sheet.get(2, {}).values()).upper():
        raise ValueError('Ontario arrears sheet missing or renamed')
    heading = re.search(r'Month Ended (\w+) \d+, (\d{4})', ' '.join(summary.get(4, {}).values()))
    if not heading:
        raise ValueError('Workbook month heading not found')
    latest = datetime.strptime(f'{heading.group(1)} {heading.group(2)}', '%B %Y').strftime('%Y-%m')
    rows = []
    for number in sorted(sheet):
        if number < 8:
            continue
        cells = sheet[number]
        for date_col, total_col, count_col, rate_col in (('A', 'B', 'C', 'D'), ('F', 'G', 'H', 'I')):
            serial = cells.get(date_col)
            values = [cells.get(c) for c in (total_col, count_col, rate_col)]
            if not serial or not re.fullmatch(r'\d+(\.0)?', serial) or any(v in (None, '', '*') for v in values):
                continue  # labels, suppressed cells and empty placeholder rows for future months
            # Early rows are month-end dates; later rows label the month by its first day.
            period = (date(1899, 12, 30) + timedelta(days=int(float(serial)))).strftime('%Y-%m')
            if period < start:
                continue
            total, count, share = (float(v) for v in values)
            # The printed share is sometimes rounded to four decimals; the rate is computed from the counts.
            if total <= 0 or abs(count / total - share) > 5e-5:
                raise ValueError(f'Arrears share does not match counts for {period}')
            rows += [('ontario_mortgage_arrears_rate', period, round(100 * count / total, 4)),
                     ('ontario_mortgage_arrears_count', period, count)]
    rows.sort(key=lambda row: (row[1], row[0]))
    periods = sorted({p for _, p, _ in rows})
    if not periods or len(periods) != len(rows) // 2:
        raise ValueError('Empty or duplicated arrears months')
    if periods[-1] != latest:
        raise ValueError(f'Latest month {periods[-1]} differs from workbook heading {latest}')
    return rows


def refresh(db, root, fetch=_get):
    from .ingest import ingest, now
    url = latest_workbook_url(fetch)
    content = fetch(url)
    if not content.startswith(b'PK'):
        raise ValueError('Expected an .xlsx workbook')
    sha = hashlib.sha256(content).hexdigest()
    if db.execute("SELECT 1 FROM ingestion_runs WHERE raw_sha256=? AND source=? AND status='success' LIMIT 1",
                  (sha, SOURCE)).fetchone():
        with db:
            db.execute('INSERT INTO ingestion_runs (source,started_at,status,raw_sha256) VALUES (?,?,?,?)',
                       (SOURCE, now(), 'unchanged', sha))
        return {'source': 'cba_arrears', 'status': 'unchanged', 'sha256': sha}
    folder = Path(root) / 'data/raw/cba'
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = folder / f'{url.rsplit("/", 1)[1][:-5]}-{sha[:12]}.xlsx'
    if not path.exists():
        path.write_bytes(content)
        path.chmod(0o600)
    rows = parse(path)
    periods = sorted({p for _, p, _ in rows})
    import sqlite3
    backup = Path(root) / 'data/backups' / f'cba-before-{datetime.now():%Y%m%dT%H%M%S%f}.sqlite3'
    backup.parent.mkdir(parents=True, exist_ok=True)
    target = sqlite3.connect(backup)
    try:
        db.backup(target)
    finally:
        target.close()
    backup.chmod(0o600)
    result = ingest(db, SOURCE, path, url, f'{periods[0]}/{periods[-1]}', 'CBA workbook, Ontario sheet; share checked against counts', rows)
    return {'source': 'cba_arrears', 'latest': periods[-1], **result}
