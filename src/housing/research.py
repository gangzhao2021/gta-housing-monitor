"""Point-in-time research gate: unknown publication dates are never backfilled."""
from datetime import datetime

CORE_SERIES = (
    "boc_policy_rate", "goc_5y_yield", "mortgage_uninsured_fixed_5plus",
    "trreb_sales", "trreb_new_listings", "trreb_active_listings",
    "trreb_hpi_benchmark", "toronto_unemployment_rate", "toronto_employment_rate",
    "toronto_participation_rate",
)


def audit_availability(db, series_ids=CORE_SERIES):
    rows = []
    for series in series_ids:
        count, published, evidenced, first, last = db.execute(
            "SELECT COUNT(*), SUM(published_at IS NOT NULL), SUM(availability_evidence IS NOT NULL), "
            "MIN(period), MAX(period) FROM observations WHERE series_id=?", (series,)
        ).fetchone()
        rows.append({"series_id": series, "observations": count,
                     "published_at_known": published or 0, "evidence_known": evidenced or 0,
                     "first_period": first, "last_period": last})
    return rows


def as_known_at(db, series_id, period, cutoff):
    """Select the newest version actually public by cutoff; fail closed on unknown dates."""
    if not isinstance(cutoff, datetime) or cutoff.tzinfo is None:
        raise ValueError("cutoff must be timezone-aware")
    rows = db.execute(
        "SELECT * FROM observations WHERE series_id=? AND period=? AND published_at IS NOT NULL "
        "AND availability_evidence IS NOT NULL ORDER BY version DESC", (series_id, period)
    ).fetchall()
    eligible = []
    for row in rows:
        published = datetime.fromisoformat(row["published_at"])
        if published.tzinfo is None:
            raise ValueError("published_at must include a timezone")
        if published <= cutoff:
            eligible.append(row)
    return eligible[0] if eligible else None
