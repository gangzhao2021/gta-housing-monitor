"""Auditable type comparisons read from the already saved official source files.

These views retain their own population and provenance. HPI classifications are
not substituted for transaction-table home types or CMHC construction types.
"""
import csv
import hashlib
import io
import re
import unicodedata
import zipfile
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import pymupdf
from pypdf import PdfReader


@lru_cache(maxsize=128)
def _hpi_pdf_rows(path, modified_ns):
    return trreb_hpi_breakdown(Path(path))


CONSTRUCTION_TYPES = {
    "Total units": ("total", "全部住宅"),
    "Single-detached units": ("detached", "独立屋"),
    "Semi-detached units": ("semi_detached", "半独立屋"),
    "Row units": ("row", "排屋"),
    "Apartment and other unit types": ("apartment_other", "公寓及其他住宅"),
}
CONSTRUCTION_METRICS = {
    "Housing starts": "starts",
    "Housing completions": "completions",
    "Housing under construction": "under_construction",
}
HPI_TYPES = (
    ("composite", "综合", "Composite"),
    ("detached", "独立式住宅", "Single Family Detached"),
    ("attached", "附连式住宅", "Single Family Attached"),
    ("townhouse", "镇屋", "Townhouse"),
    ("apartment", "公寓", "Apartment"),
)


def _provenance(path):
    path = Path(path)
    return {
        "source_path": str(path.resolve()),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def construction_breakdown(path, period=None):
    """Return all saved Toronto CMA 2011 type observations, or one month.

    Missing/suppressed values stay None. Reconciliation is reported, not repaired:
    two historical rows in the saved official file do not sum to its own total.
    """
    provenance = _provenance(path)
    result = []
    with zipfile.ZipFile(path) as archive:
        with archive.open("34100154.csv") as binary:
            rows = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8-sig"))
            required = {"REF_DATE", "GEO", "DGUID", "Housing estimates", "Type of unit",
                        "UOM", "SCALAR_FACTOR", "VALUE", "STATUS"}
            if not required.issubset(rows.fieldnames or ()):
                raise ValueError("Construction source schema is missing required columns")
            for row in rows:
                if (row["GEO"] != "Toronto, Ontario" or row["DGUID"] != "2011S0503535"
                        or row["Housing estimates"] not in CONSTRUCTION_METRICS
                        or row["Type of unit"] not in CONSTRUCTION_TYPES
                        or (period is not None and row["REF_DATE"] != period)):
                    continue
                if row["UOM"] != "Units" or row["SCALAR_FACTOR"] != "units":
                    raise ValueError("Construction type observations changed units")
                value = float(row["VALUE"]) if row["VALUE"] and not row["STATUS"] else None
                if value is not None and (value < 0 or not value.is_integer()):
                    raise ValueError("Construction counts must be nonnegative whole units")
                type_id, type_label = CONSTRUCTION_TYPES[row["Type of unit"]]
                result.append({
                    "period": row["REF_DATE"], "type_id": type_id, "type_label": type_label,
                    "source_type": row["Type of unit"],
                    "metric": CONSTRUCTION_METRICS[row["Housing estimates"]],
                    "value": value, "unit": "units", "geography": "Toronto CMA 2011 boundary",
                    "source_page": None, "source_status": row["STATUS"], **provenance,
                })
    if not result:
        raise ValueError("No matching Toronto CMA 2011 construction breakdown found")
    groups = defaultdict(list)
    for row in result:
        groups[(row["period"], row["metric"])].append(row)
    for group in groups.values():
        values = {row["type_id"]: row["value"] for row in group}
        if len(group) != len(values):
            raise ValueError("Duplicate construction type observation in source")
        complete = len(values) == len(CONSTRUCTION_TYPES) and all(v is not None for v in values.values())
        difference = values["total"] - sum(v for k, v in values.items() if k != "total") if complete else None
        for row in group:
            row["reconciliation_ok"] = difference == 0 if complete else None
            row["reconciliation_difference"] = difference
            row["quality_note"] = ("" if difference == 0 else "原表分项与总数不一致" if complete
                                   else "原表部分房型缺失，无法核对合计")
    return result


def _hpi_rows(period, triplets, page_index, provenance):
    if len(triplets) != len(HPI_TYPES):
        raise ValueError("TRREB HPI total row has missing or shifted type columns")
    result = []
    for (type_id, label, source_type), triplet in zip(HPI_TYPES, triplets):
        for metric, raw_value, unit in zip(("index", "benchmark", "source_yoy"), triplet,
                                           ("index", "CAD", "%")):
            value = float(raw_value.replace(",", ""))
            if metric != "source_yoy" and value <= 0:
                raise ValueError("TRREB HPI levels must be positive")
            result.append({
                "period": period, "type_id": type_id, "type_label": label,
                "source_type": source_type, "metric": metric, "value": value, "unit": unit,
                "geography": "All TRREB Areas", "source_page": page_index + 1, **provenance,
            })
    return result


def _dashboard_hpi(path, period, provenance):
    """Read the HPI page of the layout TRREB introduced with September 2026.

    That layout drops ligatures in pypdf text, so its word boxes are read with
    PyMuPDF. The title must name All TRREB Areas and the file's month.
    """
    reference_label = datetime.strptime(period, "%Y-%m").strftime("%B %Y")
    with pymupdf.open(path) as document:
        for page_index, page in enumerate(document):
            words = [(*w[:4], unicodedata.normalize("NFKC", w[4])) for w in page.get_text("words")]
            flat = " ".join(" ".join(w[4] for w in words).split())
            if "MLS® Home Price Index" not in flat or "All TRREB Areas," not in flat:
                continue
            if f"All TRREB Areas, {reference_label}" not in flat:
                raise ValueError("TRREB filename and HPI reference month differ")
            if not all(source_type in flat for _, _, source_type in HPI_TYPES):
                raise ValueError("TRREB HPI home-type header changed")
            rows = defaultdict(list)
            for word in words:
                rows[round(word[1] / 3)].append(word)
            for key in sorted(rows):
                line = " ".join(w[4] for w in sorted(rows[key], key=lambda w: w[0]))
                match = re.match(r"^All TRREB Areas\s+(\d.*)$", line)
                if match:
                    triplets = re.findall(r"(\d+(?:\.\d+)?)\s+\$([\d,]+)\s+(-?\d+(?:\.\d+)?)%",
                                          match.group(1))
                    return _hpi_rows(period, triplets, page_index, provenance)
            raise ValueError("TRREB HPI page has no All TRREB Areas row")
    return None


def trreb_hpi_breakdown(pdf_path):
    """Read the source report's All TRREB Areas HPI comparison, with page proof.

    The source's published YoY is returned as source_yoy. It is not recomputed
    from a separate month report, which may contain a different revision.
    """
    path = Path(pdf_path)
    filename = re.fullmatch(r"mw(\d{2})(0[1-9]|1[0-2])\.pdf", path.name)
    if not filename:
        raise ValueError("TRREB filename must identify its reference month: mwYYMM.pdf")
    period = "20" + filename.group(1) + "-" + filename.group(2)
    provenance = _provenance(path)
    reader = PdfReader(path)
    # The archived reports use page 25. Verify its heading; search if that moves.
    candidates = [24] if len(reader.pages) > 24 else []
    candidates += [i for i in range(len(reader.pages)) if i not in candidates]
    for page_index in candidates:
        text = reader.pages[page_index].extract_text(extraction_mode="layout") or ""
        normalized = " ".join(text.split())
        if "FOCUS ON THE MLS" not in normalized or "HOME PRICE INDEX" not in normalized:
            continue
        reference_label = datetime.strptime(period, "%Y-%m").strftime("%B %Y")
        if reference_label not in normalized:
            raise ValueError("TRREB filename and HPI reference month differ")
        if not all(source_type in normalized for _, _, source_type in HPI_TYPES):
            raise ValueError("TRREB HPI home-type header changed")
        for line in text.splitlines():
            match = re.match(r"^\s*All\s+TRREB\s+Areas\s+(.*)$", line, re.I)
            if not match:
                continue
            # Exact triplets make a suppressed/shifted column fail closed.
            triplets = re.findall(r"(\d+(?:\.\d+)?)\s+\$([\d,]+)\s+(-?\d+(?:\.\d+)?)%", match.group(1))
            return _hpi_rows(period, triplets, page_index, provenance)
    rows = _dashboard_hpi(path, period, provenance)
    if rows is None:
        raise ValueError("TRREB report has no verified HPI All TRREB Areas type comparison")
    return rows


def trreb_hpi_for_observation(db, period, root):
    """Resolve HPI types through the selected aggregate's recorded source chain.

    A newer file for the same month is not automatically authoritative. The
    aggregate observation identifies a CSV by hash; that exact row identifies
    its PDF by hash. Both files and their composite values must still agree.
    """
    observation = db.execute("""SELECT id, value, version, raw_sha256 FROM observations
        WHERE series_id='trreb_hpi_benchmark' AND period=?
        ORDER BY version DESC LIMIT 1""", (period,)).fetchone()
    if observation is None:
        raise ValueError("No HPI benchmark observation for the selected month")
    observation_id, benchmark, version, csv_sha = observation

    def verified_source(sha, expected_suffix):
        source = db.execute("SELECT path, source, reference_period FROM raw_files WHERE sha256=?", (sha,)).fetchone()
        if source is None or source[1] != "TRREB":
            raise ValueError("HPI source hash is not registered as a TRREB source")
        path = Path(source[0])
        if not path.is_absolute():
            path = Path(root) / path
        if path.suffix.lower() != expected_suffix or not path.is_file():
            raise ValueError("HPI registered source file is missing or has an unexpected type")
        if _provenance(path)["source_sha256"] != sha:
            raise ValueError("HPI source file checksum differs from the observation's recorded source")
        return path, source[2]

    csv_path, _ = verified_source(csv_sha, ".csv")
    with csv_path.open(newline="", encoding="utf-8-sig") as source:
        matches = [row for row in csv.DictReader(source)
                   if row.get("period") == period and row.get("geography") == "All TRREB Areas"
                   and row.get("home_type") == "All Home Types"]
    if len(matches) != 1:
        raise ValueError("HPI source CSV must contain one exact month and population row")
    source_row = matches[0]
    try:
        csv_benchmark = float(source_row["hpi_benchmark"])
        csv_index = float(source_row["hpi_composite"])
        csv_page = int(source_row["hpi_page"])
        pdf_sha = source_row["source_pdf_sha256"]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("HPI source CSV is missing valid amount, page or PDF provenance") from error
    if csv_benchmark != benchmark:
        raise ValueError("HPI source CSV composite benchmark differs from the selected observation")
    pdf_path, pdf_period = verified_source(pdf_sha, ".pdf")
    if pdf_period != period:
        raise ValueError("HPI registered PDF period differs from the selected observation")
    # The provenance chain and hashes are checked on every call. Cache only
    # PDF parsing, then copy rows before attaching observation-specific IDs.
    rows = [dict(row) for row in _hpi_pdf_rows(str(pdf_path), pdf_path.stat().st_mtime_ns)]
    composite = {row["metric"]: row["value"] for row in rows if row["type_id"] == "composite"}
    if composite.get("benchmark") != benchmark or composite.get("index") != csv_index:
        raise ValueError("HPI PDF composite values differ from the selected CSV and observation")
    if any(row["period"] != period or row["source_page"] != csv_page or row["source_sha256"] != pdf_sha for row in rows):
        raise ValueError("HPI PDF period, page or hash differs from its CSV provenance")
    for row in rows:
        row.update(anchor_observation_id=observation_id, anchor_version=version,
                   anchor_source_sha256=csv_sha)
    return rows
