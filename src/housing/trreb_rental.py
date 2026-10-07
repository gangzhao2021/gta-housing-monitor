"""TRREB quarterly Rental Market Report: condo apartments leased through MLS.

Signed-lease averages for All TRREB Areas, kept apart from Rentals.ca asking
rents and CMHC stock rents. Quarters are stored by their first month, as for
other quarterly series; values are never interpolated to months.
"""
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

SOURCE = 'TRREB rental'
URL = 'https://trreb.ca/wp-content/files/market-stats/rental-reports/rental_report_Q{q}-{year}.pdf'
ARCHIVE = 'https://trreb.ca/market-data/rental-market-report/rental-market-report-archive/'
START = (2022, 3)
GEO = 'All TRREB Areas'
NOTE = '经 TRREB MLS 报告租出的 condo 公寓，季度流量；不含专建出租和未经 MLS 的租约，均价受房型与地点构成影响，不是同一套房租金涨幅'
# series id -> (label, unit, definition)
SERIES = {
    'gta_condo_lease_listed': ('TRREB condo 公寓租赁挂牌量（季度）', 'units', '季度内经 MLS 挂牌出租的 condo 公寓套数；' + NOTE),
    'gta_condo_leased': ('TRREB condo 公寓签约租出量（季度）', 'units', '季度内经 MLS 租出的 condo 公寓套数；' + NOTE),
    'gta_condo_lease_rent_bachelor': ('TRREB condo 开间平均签约租金（季度）', 'CAD/month', NOTE),
    'gta_condo_lease_rent_1br': ('TRREB condo 一卧平均签约租金（季度）', 'CAD/month', NOTE),
    'gta_condo_lease_rent_2br': ('TRREB condo 两卧平均签约租金（季度）', 'CAD/month', NOTE),
    'gta_condo_lease_rent_3br': ('TRREB condo 三卧平均签约租金（季度）', 'CAD/month', NOTE),
}


def quarters(today=None):
    """Quarters from 2022 Q3 through the last completed quarter."""
    today = today or date.today()
    year, quarter = today.year, (today.month - 1) // 3
    if quarter == 0:
        year, quarter = year - 1, 4
    current = START
    while current <= (year, quarter):
        yield current
        current = (current[0] + 1, 1) if current[1] == 4 else (current[0], current[1] + 1)


def period_for(year, quarter):
    return f'{year:04d}-{3 * quarter - 2:02d}'


def _amount(token):
    return int(token.replace('$', '').replace(',', ''))


def _total_rows(page):
    rows = {}
    for word in page.get_text('words'):
        if word[4] != 'Abc':  # hidden placeholder text in TRREB table cells
            rows.setdefault(round(word[1] / 3), []).append(word)
    for key in sorted(rows):
        words = [unicodedata.normalize('NFKC', w[4]) for w in sorted(rows[key], key=lambda w: w[0])]
        if words[:3] == ['All', 'TRREB', 'Areas'] and len(words) > 3:
            yield words[3:]


def parse_report(path, year, quarter):
    """Return observation rows; any shifted, missing or inconsistent value fails."""
    import pymupdf
    label = f'Apartments, {year} Q{quarter}'
    totals = []
    with pymupdf.open(path) as document:
        front = ' '.join(document[0].get_text().split())
        if f'Rental Market Report, {year} Q{quarter}' not in front:
            raise ValueError('Rental report title does not match the requested quarter')
        for page in document:
            title = ' '.join(w[4] for w in page.get_text('words') if w[1] < 50)
            if 'SUMMARY OF RENTAL TRANSACTIONS' in title and label in title:
                totals.extend(_total_rows(page))
    if not totals:
        raise ValueError('Apartment rental table for All TRREB Areas not found')
    if any(row != totals[0] for row in totals):
        raise ValueError('All TRREB Areas apartment totals differ across pages')
    tokens = totals[0]
    if (len(tokens) != 10 or any(not re.fullmatch(r'\$[\d,]+', tokens[i]) for i in (3, 5, 7, 9))
            or any(not re.fullmatch(r'[\d,]+', tokens[i]) for i in (0, 1, 2, 4, 6, 8))):
        raise ValueError(f'Unexpected All TRREB Areas apartment row: {tokens}')
    values = [_amount(token) for token in tokens]
    listed, leased = values[:2]
    by_type = values[2:]
    if sum(by_type[0::2]) != leased:
        raise ValueError('Bedroom-type leases do not sum to total leased')
    if f'${by_type[3]:,}' not in front or f'{leased:,}' not in front:
        raise ValueError('Front-page summary does not show the table totals')
    period = period_for(year, quarter)
    names = ['gta_condo_lease_listed', 'gta_condo_leased', 'gta_condo_lease_rent_bachelor',
             'gta_condo_lease_rent_1br', 'gta_condo_lease_rent_2br', 'gta_condo_lease_rent_3br']
    numbers = [listed, leased, *by_type[1::2]]
    return [(name, period, float(number)) for name, number in zip(names, numbers)]


def refresh(db, root, today=None, opener=None):
    """Download missing quarterly PDFs and ingest quarters not yet stored."""
    import sqlite3
    from urllib.error import HTTPError
    from urllib.request import urlopen
    from .ingest import ingest
    opener = opener or (lambda url: urlopen(url, timeout=45).read())
    root = Path(root)
    folder = root / 'data/raw/trreb_rental'
    folder.mkdir(parents=True, exist_ok=True)
    report = {'downloaded': [], 'pending': [], 'inserted': 0}
    every = list(quarters(today))
    for year, quarter in every:
        period = period_for(year, quarter)
        pdf = folder / f'rental_report_Q{quarter}-{year}.pdf'
        url = URL.format(q=quarter, year=year)
        if not pdf.exists():
            try:
                content = opener(url)
            except HTTPError as exc:
                if exc.code == 404 and (year, quarter) == every[-1]:
                    report['pending'].append(f'{year}Q{quarter}')
                    continue
                raise
            if not content.startswith(b'%PDF-'):
                raise ValueError('Expected official PDF')
            temporary = pdf.with_suffix('.download')
            temporary.write_bytes(content)
            temporary.chmod(0o600)
            temporary.replace(pdf)
            report['downloaded'].append(f'{year}Q{quarter}')
        if db.execute("SELECT 1 FROM observations WHERE series_id='gta_condo_leased' AND period=?",
                      (period,)).fetchone():
            continue  # Revisions need a separately reviewed source, not a replay.
        rows = parse_report(pdf, year, quarter)
        backup = root / 'data/backups' / f'trreb-rental-before-{datetime.now().strftime("%Y%m%dT%H%M%S%f")}.sqlite3'
        backup.parent.mkdir(parents=True, exist_ok=True)
        target = sqlite3.connect(backup)
        try:
            db.backup(target)
        finally:
            target.close()
        backup.chmod(0o600)
        result = ingest(db, SOURCE, pdf, url, period, 'quarterly PDF; All TRREB Areas apartment row', rows)
        report['inserted'] += result.get('inserted', 0)
    return report
