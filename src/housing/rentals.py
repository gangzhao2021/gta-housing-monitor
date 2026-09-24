"""Import public Rentals.ca charts with report scope retained alongside each CSV."""
import csv
import html
import json
import re
from datetime import datetime
from pathlib import Path

from .ingest import ingest, register_raw, validate_rows
from .presentation import calendar_periods

SOURCE = "Rentals.ca / Urbanation"
PREFIX = "toronto_asking_rent_"


def parse_dataset(csv_path, chart_path):
    text = Path(chart_path).read_text()
    marker = 'window.__DW_SVELTE_PROPS__ = JSON.parse('
    if marker not in text:
        raise ValueError("Missing public chart metadata")
    encoded = json.JSONDecoder().raw_decode(text.split(marker, 1)[1])[0]
    chart = json.loads(encoded)["chart"]
    description = chart["metadata"]["describe"]
    intro = html.unescape(description["intro"])
    if "Rentals.ca" not in description.get("source-name", "") or "Condo" not in intro or "Purpose-built" not in intro:
        raise ValueError("Unverified publisher or apartment/condo scope")
    url = chart["publicUrl"]
    if not re.fullmatch(r"https://datawrapper\.dwcdn\.net/[A-Za-z0-9]+/\d+/", url):
        raise ValueError("Unexpected public chart URL")
    with Path(csv_path).open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        headers, records = reader.fieldnames, list(reader)
    result = []
    if chart["title"] == "Average Asking Rent for Canada's 6 Largest Markets":
        if headers != ["Date", "Toronto", "Calgary", "Edmonton", "Montreal", "Ottawa", "Vancouver"]:
            raise ValueError("Unexpected historical CSV columns")
        match = re.fullmatch(r"Purpose-built and Condo Apartments: ([A-Za-z]+ \d{4}) to ([A-Za-z]+ \d{4})", intro)
        if not match:
            raise ValueError("Missing history period coverage")
        first, last = (datetime.strptime(v, "%B %Y").strftime("%Y-%m") for v in match.groups())
        for row in records:
            raw_date = row["Date"]
            try:
                dt = datetime.strptime(raw_date, "%Y-%m-%d")
                if dt.day != 1:
                    raise ValueError("Monthly chart date must be the first day")
            except ValueError:
                dt = datetime.strptime(raw_date, "%b-%y")
            result.append((PREFIX + "total", dt.strftime("%Y-%m"), float(row["Toronto"].replace(",", ""))))
        if [r[1] for r in result] != calendar_periods(first, last):
            raise ValueError("History must match metadata with no duplicate or missing months")
    elif chart["title"] == "Average Asking Rent by Bedroom Type for the 6 Largest Markets":
        if headers != ["Market", "1 Bed", "2 Bed", "3 Bed"]:
            raise ValueError("Unexpected bedroom CSV columns")
        match = re.fullmatch(r"Purpose-built & Condo Rental Apartments: ([A-Za-z]+ \d{4})", intro)
        if not match:
            raise ValueError("Missing bedroom snapshot period")
        period = datetime.strptime(match[1], "%B %Y").strftime("%Y-%m")
        toronto = [r for r in records if r["Market"] == "Toronto"]
        if len(toronto) != 1:
            raise ValueError("Expected exactly one Toronto row")
        result = [(PREFIX + room, period, float(toronto[0][column].replace(",", "")))
                  for room, column in [("1br", "1 Bed"), ("2br", "2 Bed"), ("3br", "3 Bed")]]
    else:
        raise ValueError("Unsupported chart title")
    validate_rows(result)
    return result, url, intro


def import_dataset(db, csv_path, chart_path, report_url):
    if not re.fullmatch(r"https://rentals\.ca/blog/rentals-ca-[a-z]+-\d{4}-rent-report", report_url):
        raise ValueError("An archived Rentals.ca report URL is required")
    rows, chart_url, intro = parse_dataset(csv_path, chart_path)
    span = f"{min(r[1] for r in rows)}/{max(r[1] for r in rows)}"
    with db:
        register_raw(db, chart_path, SOURCE, chart_url, span, "public chart metadata; report: " + report_url)
    return ingest(db, SOURCE, csv_path, chart_url + "dataset.csv", span,
                  "public chart CSV; " + intro + "; report: " + report_url, rows)
