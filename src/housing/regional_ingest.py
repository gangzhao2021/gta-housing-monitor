"""Regional sources: explicit scope, period and duplicate validation."""
import csv
import html
import json
import re
from datetime import datetime
from pathlib import Path
from .regions import MONTHLY_REGIONS, CMHC_REGIONS, asking_id
from .ingest import validate_rows, parse_cmhc_rental_details


def parse_regional_csv(csv_path, chart_path):
    text = Path(chart_path).read_text()
    marker = 'window.__DW_SVELTE_PROPS__ = JSON.parse('
    if marker not in text:
        raise ValueError('Missing chart metadata')
    encoded = json.JSONDecoder().raw_decode(text.split(marker, 1)[1])[0]
    chart = json.loads(encoded)['chart']
    title = html.unescape(chart['title'])
    desc = chart['metadata']['describe']
    intro = html.unescape(desc['intro'])
    if 'Rentals.ca' not in desc.get('source-name', ''):
        raise ValueError('Wrong publisher')
    url = chart['publicUrl']
    if not re.fullmatch(r'https://datawrapper\.dwcdn\.net/[A-Za-z0-9]+/\d+/', url):
        raise ValueError('Unexpected source URL')
    with Path(csv_path).open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers, records = reader.fieldnames, list(reader)
    is_city = title == 'Average Rent for Apartments & Condos Only — Top Canadian Markets'
    is_top = title == 'Highest Avg. Asking Rent for Purpose-built & Condo Rental Apts'
    if is_city:
        period = datetime.strptime(intro, '%B %Y').strftime('%Y-%m')
        total = next((h for h in ['Total Avg.', 'Total Avg'] if h in headers), None)
        if not total or any(headers.count(h) != 1 for h in ['City', total, '1 Bed', '2 Bed']):
            raise ValueError('Unexpected city table columns')
        city_key, mapping = 'City', {'total': total, '1br': '1 Bed', '2br': '2 Bed'}
    elif is_top:
        match = re.fullmatch(r'Top 25 Markets \(Outside of 6 Largest\): ([A-Za-z]+ \d{4})', intro)
        if not match or headers != ['Market', 'Province', 'Avg Rent']:
            raise ValueError('Unexpected top-market metadata or columns')
        period = datetime.strptime(match[1], '%B %Y').strftime('%Y-%m')
        city_key, mapping = 'Market', {'total': 'Avg Rent'}
    else:
        raise ValueError('Requires apartment/condo city table; all-property tables are incompatible')
    names = {name: region for region, name in MONTHLY_REGIONS.items()}
    result, seen = [], set()
    for item in records:
        name = item[city_key]
        if name not in names:
            continue
        region = names[name]
        if name in seen:
            raise ValueError('Duplicate region: ' + name)
        seen.add(name)
        # Same apartment/condo scope; rankings supply totals only, never bedrooms.
        if is_top and item['Province'] != 'ON':
            raise ValueError('Wrong province for ' + name)
        for room, column in mapping.items():
            # Regional totals consistently use the Top 25 series. April 2026
            # city-table totals disagree with that chart; do not alternate sources.
            if is_city and region != 'toronto' and room == 'total':
                continue
            raw = item[column].strip()
            if raw in ('', '-', '—', 'N/A', '**'):
                continue
            result.append((asking_id(region, room), period, float(raw.replace(',', '').replace('$', ''))))
    if not result:
        raise ValueError('No requested regions found')
    validate_rows(result)
    return result, url, intro


def regional_cmhc_details(path):
    return [{**item, 'region': region, 'source_zone': label}
            for region, label in CMHC_REGIONS.items()
            for item in parse_cmhc_rental_details(path, label, 'regional_cmhc_' + region, True)]


def import_regional_csv(db, csv_path, chart_path, report_url):
    from .ingest import register_raw, ingest, record_parse_failure
    try:
        if not (re.fullmatch(r'https://rentals\.ca/blog/rentals-ca-[a-z]+-\d{4}-rent-report', report_url)
                or report_url == 'https://rentals.ca/national-rent-report'):
            raise ValueError('Rentals.ca report URL required')
        rows, url, intro = parse_regional_csv(csv_path, chart_path)
    except Exception as exc:
        with db:
            if Path(chart_path).is_file():
                register_raw(db, chart_path, 'Rentals.ca / Urbanation', report_url, None, 'rejected regional chart metadata')
        record_parse_failure(db, 'Rentals.ca / Urbanation', csv_path, exc, report_url)
        raise
    period = rows[0][1]
    with db:
        register_raw(db, chart_path, 'Rentals.ca / Urbanation', url, period, 'regional chart metadata; report: ' + report_url)
    return ingest(db, 'Rentals.ca / Urbanation', csv_path, url + 'dataset.csv', period,
                  'apartment/condo regional CSV; ' + intro + '; report: ' + report_url, rows)
