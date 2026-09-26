"""Extract district / municipality level monthly aggregates from TRREB Market Watch PDFs.

Reads data/raw/trreb/mwYYMM.pdf and parses the "SUMMARY OF EXISTING HOME
TRANSACTIONS" tables, which break every month down by TRREB district /
municipality for all home types plus each major home type
(detached, semi-detached, townhouse, condo townhouse, condo apartment, ...).

Why this exists: the headline extractor (extract_trreb.py) only keeps the
"All TRREB Areas" row. The per-district tables were previously ignored even
though they are the cheapest source of district-level monthly aggregates
(no MLS login needed, public-report definitions).

Method: PyMuPDF word boxes (``pip install pymupdf``). Words are grouped into
rows by y-coordinate and assigned to columns by x-coordinate using the table
header, so the parse does not depend on fragile text-line reconstruction.
Every row is cross-checked (dollar_volume / sales must round to
average_price) and top-level regions must sum to the All TRREB Areas total.

Output: data/manual/trreb-districts-<from>-to-<to>-<digest>.csv
"""

import argparse
import csv
import hashlib
import io
from datetime import datetime
import re
from pathlib import Path

import pymupdf  # PyMuPDF  (pip install pymupdf)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/trreb"
OUT = ROOT / "data/manual"

MARKER = "SUMMARY OF EXISTING HOME TRANSACTIONS"
SUBTITLE = "CITY OF TORONTO MUNICIPAL BREAKDOWN"

# Header text -> (csv field, value kind), in table order.
COLUMNS = [
    ("Sales", "sales", "int"),
    ("Dollar Volume", "dollar_volume", "money"),
    ("Average Price", "average_price", "money"),
    ("Median Price", "median_price", "money"),
    ("New Listings", "new_listings", "int"),
    ("SNLR Trend", "snlr_trend", "pct"),
    ("Active Listings", "active_listings", "int"),
    ("Mos Inv (Trend)", "moi_trend", "float"),
    ("Avg. SP/LP", "avg_sp_lp", "pct"),
    ("Avg. LDOM", "avg_ldom", "int"),
    ("Avg. PDOM", "avg_pdom", "int"),
]

HOME_TYPE_SLUGS = {
    "DETACHED": "detached",
    "SEMI-DETACHED": "semi_detached",
    "ATT/ROW/TOWNHOUSE": "townhouse",
    "CONDO TOWNHOUSE": "condo_townhouse",
    "CONDO APARTMENT": "condo_apartment",
    "LINK": "link",
    "CO-OP APARTMENT": "coop_apartment",
    "DETACHED CONDO": "detached_condo",
    "CO-OWNERSHIP APARTMENT": "coownership_apartment",
}

TOP_LEVEL_AREAS = {
    "City of Toronto",
    "Halton Region",
    "Peel Region",
    "York Region",
    "Durham Region",
    "Dufferin County",
    "Simcoe County",
}

LABEL_DENY = ("Copyright", "Source", "Note:", "www.trreb.ca")

NUM_FULL = re.compile(r"\$[\d,]+|[\d,]+\.\d+%?|[\d,]+%?")
FOOTNOTE = re.compile(r"^Abc", re.IGNORECASE)

MONTHS = {
    "JANUARY": "01", "FEBRUARY": "02", "MARCH": "03", "APRIL": "04",
    "MAY": "05", "JUNE": "06", "JULY": "07", "AUGUST": "08",
    "SEPTEMBER": "09", "OCTOBER": "10", "NOVEMBER": "11", "DECEMBER": "12",
}


def months_between(start, end):
    datetime.strptime(start, "%Y-%m")
    datetime.strptime(end, "%Y-%m")
    if start > end:
        raise ValueError("Start month must not follow end month")
    year, month = map(int, start.split("-"))
    final = tuple(map(int, end.split("-")))
    while (year, month) <= final:
        yield year, month
        month += 1
        if month == 13:
            year, month = year + 1, 1


def norm(text):
    return " ".join(text.upper().split())


def parse_value(raw, kind):
    raw = raw.strip()
    if kind == "money":
        return int(raw.replace("$", "").replace(",", ""))
    if kind == "int":
        return int(raw.replace(",", ""))
    if kind == "pct":
        return float(raw.replace("%", ""))
    if kind == "float":
        return float(raw.replace(",", ""))
    raise ValueError(kind)


def row_ok(row):
    """Cross-check: dollar_volume / sales must round to average_price."""
    sales = row.get("sales")
    if not sales:
        return True
    vol = row.get("dollar_volume")
    avg = row.get("average_price")
    if vol is None or avg is None:
        return False
    return abs(vol / sales - avg) <= 0.500001


def page_text(page):
    return page.get_text()


def section_home_type(text):
    """Return home-type slug, 'INHERIT' (municipal-breakdown continuation page),
    or None for year-to-date pages."""
    flat = norm(text)
    if "YEAR-TO-DATE" in flat:
        return None
    m = re.search(
        re.escape(norm(MARKER))
        + r"\s*(.*?)\s*(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)",
        flat,
    )
    label = (m.group(1).strip(" ,") if m else "")
    has_subtitle = SUBTITLE in flat
    label = label.replace(SUBTITLE, "").strip(" ,")
    if not label:
        # A bare municipal-breakdown page inherits the previous page's section;
        # a plain untitled table is the all-types section.
        return "INHERIT" if has_subtitle else "all_types"
    if label == "ALL HOME TYPES":
        return "all_types"
    slug = HOME_TYPE_SLUGS.get(label)
    if slug is None:
        # A bare municipal-breakdown page with no type label inherits the
        # previous page's section.
        if "MUNICIPAL BREAKDOWN" in flat:
            return "INHERIT"
        raise ValueError(f"unknown home-type section: {label!r}")
    return slug


def title_period(text):
    flat = norm(text)
    m = re.search(
        r"(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+(20\d\d)",
        flat,
    )
    if not m:
        return None
    return f"{m.group(2)}-{MONTHS[m.group(1)]}"


def y_groups(words, tol=3.0):
    groups = {}
    for w in words:
        key = round(w[1] / tol)
        groups.setdefault(key, []).append(w)
    return groups


def header_columns(page):
    """Find the table header row; return (header_y, [(field, kind, xc, x0)])."""
    words = page.get_text("words")
    for key in sorted(y_groups(words)):
        ws = sorted(y_groups(words)[key], key=lambda w: w[0])
        txt = " ".join(w[4] for w in ws)
        if "Sales" in txt and "Dollar" in txt:
            header_y = sum(w[1] for w in ws) / len(ws)
            cols = []
            i = 0
            for title, field, kind in COLUMNS:
                parts = title.split(" ")
                if [w[4] for w in ws[i : i + len(parts)]] == parts:
                    span = ws[i : i + len(parts)]
                    xc = sum((w[0] + w[2]) / 2 for w in span) / len(span)
                    cols.append((field, kind, xc, span[0][0]))
                    i += len(parts)
                # else: column absent on this page; keep going
            if not cols or cols[0][0] != "sales":
                raise ValueError(f"unrecognized table header: {txt[:120]!r}")
            return header_y, cols
    return None, []


def data_rows(page, header_y, columns, page_no, problems):
    """Parse data rows below the header using word-box geometry."""
    words = [
        w
        for w in page.get_text("words")
        if not FOOTNOTE.match(w[4])
    ]
    groups = y_groups(words)
    header_key = round(header_y / 3.0)
    sales_x0 = columns[0][3]
    rows = []
    for key in sorted(groups):
        if key <= header_key:
            continue
        ws = sorted(groups[key], key=lambda w: w[0])
        label_words = [w for w in ws if w[2] <= sales_x0 - 2]
        value_words = [w for w in ws if w[2] > sales_x0 - 2]
        label = " ".join(w[4] for w in label_words).strip()
        if not label or label.startswith(LABEL_DENY):
            continue
        buckets = {c[0]: [] for c in columns}
        for w in value_words:
            xc = (w[0] + w[2]) / 2
            field = min(columns, key=lambda c: abs(c[2] - xc))[0]
            buckets[field].append(w[4])
        row = {"area": label}
        for field, kind, _xc, _x0 in columns:
            val = None
            for tok in buckets[field]:
                if NUM_FULL.fullmatch(tok):
                    try:
                        val = parse_value(tok, kind)
                    except ValueError:
                        val = None
                    break
            row[field] = val
        if row.get("sales") is None:
            continue  # footnote / stray line without data
        if not row_ok(row):
            problems.append(
                f"p{page_no}: row failed validation, dropped: {label!r}"
            )
            continue
        rows.append(row)
    return rows


def scan_pdf(path, period, problems):
    """Parse all monthly district tables in one PDF.

    Returns {home_type: [rows]}.
    """
    doc = pymupdf.open(str(path))
    by_type = {}
    prev_type = None
    for i, page in enumerate(doc):
        text = page_text(page)
        if norm(MARKER) not in norm(text):
            continue
        home_type = section_home_type(text)
        if home_type is None:
            continue  # year-to-date page
        if home_type == "INHERIT":
            if prev_type is None:
                raise ValueError(f"p{i + 1}: municipal-breakdown page with no section")
            home_type = prev_type
        title_ym = title_period(text)
        if title_ym and title_ym != period:
            raise ValueError(
                f"p{i + 1}: period mismatch: file says {period}, page says {title_ym}"
            )
        header_y, columns = header_columns(page)
        if not columns:
            raise ValueError(f"p{i + 1}: district table header not found")
        rows = data_rows(page, header_y, columns, i + 1, problems)
        by_type.setdefault(home_type, []).extend(rows)
        prev_type = home_type
    doc.close()
    return by_type


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("from_ym")
    ap.add_argument("to_ym")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    problems = []
    for year, month in months_between(args.from_ym, args.to_ym):
        period = f"{year}-{month:02d}"
        pdf = RAW / f"mw{year % 100:02d}{month:02d}.pdf"
        if not pdf.exists():
            problems.append(f"{period}: missing {pdf.name}, skipped")
            continue
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
        try:
            by_type = scan_pdf(pdf, period, problems)
        except ValueError as exc:
            problems.append(f"{period}: {exc}")
            continue
        if not by_type:
            problems.append(f"{period}: no monthly district tables parsed")
        if set(by_type) != {'all_types', *HOME_TYPE_SLUGS.values()}:
            problems.append(f"{period}: incomplete home-type sections")
        for home_type, rows in by_type.items():
            # The 905 page and the Toronto page of a section both print the
            # All TRREB Areas / City of Toronto / Toronto West-Central-East
            # summary rows. Dedupe them; any value conflict is reported loudly.
            deduped = {}
            for row in rows:
                key = row["area"]
                if key in deduped:
                    if deduped[key] != row:
                        problems.append(
                            f"{period} {home_type}: CONFLICT for {key!r}: "
                            f"{deduped[key]} vs {row}"
                        )
                    continue
                deduped[key] = row
            rows = list(deduped.values())
            totals = {r["sales"] for r in rows if r["area"] == "All TRREB Areas"}
            if len(totals) > 1:
                problems.append(
                    f"{period} {home_type}: All TRREB Areas disagrees across "
                    f"pages: {sorted(totals)}"
                )
            if not totals:
                problems.append(f"{period} {home_type}: missing All TRREB Areas")
            if {r['area'] for r in rows} & TOP_LEVEL_AREAS != TOP_LEVEL_AREAS:
                problems.append(f"{period} {home_type}: missing top-level regions")
            if totals:
                all_sales = next(iter(totals))
                top = sum(
                    r["sales"]
                    for r in rows
                    if r["area"] in TOP_LEVEL_AREAS and isinstance(r.get("sales"), int)
                )
                if top != all_sales:
                    problems.append(
                        f"{period} {home_type}: top-level regions sum to {top:,} "
                        f"but All TRREB Areas reports {all_sales:,}"
                    )
            total_row = next((r for r in rows if r['area'] == 'All TRREB Areas'), None)
            # Seven separately printed whole-dollar subtotals and one total can
            # differ by at most $4 from independent rounding; keep source values.
            if total_row and abs(sum(r.get('dollar_volume') or 0 for r in rows
                                     if r['area'] in TOP_LEVEL_AREAS)
                                 - (total_row.get('dollar_volume') or 0)) > 4:
                problems.append(f"{period} {home_type}: regional dollar volumes do not sum to total")
            seen = set()
            for row in rows:
                assert row["area"] not in seen  # deduped above
                seen.add(row["area"])
                rec = {
                    "ym": period,
                    "house_type": home_type,
                    "region": row["area"],
                    "source_pdf": pdf.name,
                    "source_pdf_sha256": digest,
                }
                for _title, field, _kind in COLUMNS:
                    rec[field] = row.get(field, "")
                    if rec[field] is None:
                        rec[field] = ""
                records.append(rec)

    if problems:
        for problem in problems:
            print("PROBLEM:", problem)
        raise SystemExit(1)  # Never publish a partially parsed batch as successful.
    records.sort(key=lambda r: (r["ym"], r["house_type"], r["region"]))
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=["ym", "house_type", "region"]
                            + [f for _t, f, _k in COLUMNS]
                            + ["source_pdf", "source_pdf_sha256"])
    writer.writeheader()
    writer.writerows(records)
    payload = buffer.getvalue().encode("utf-8")
    out_digest = hashlib.sha256(payload).hexdigest()[:12]
    out_csv = OUT / f"trreb-districts-{args.from_ym}-to-{args.to_ym}-{out_digest}.csv"
    temporary = out_csv.with_suffix(".tmp")
    temporary.write_bytes(payload)
    temporary.replace(out_csv)
    print(f"periods with data : {len({r['ym'] for r in records})}")
    print(f"home types        : {sorted({r['house_type'] for r in records})}")
    print(f"rows written      : {len(records)}")
    print(f"output            : {out_csv}")
    print("validation        : passed")


if __name__ == "__main__":
    main()
