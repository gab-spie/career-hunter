"""
Local CSV mirror of kept offers (a fallback next to the Google Sheet).

Rebuilds data/kept_<profil>.csv from the DB on every change.
Same columns as the Google Sheet tab, for a painless switch.
"""

import csv
import os
from pathlib import Path

import db

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

HEADERS = ["Added", "Company", "Title", "Location", "Start date", "Score",
           "Link", "Source", "Status", "Applied on", "Outcome", "Notes"]

STATUS = {"kept": "To apply", "applied": "Applied"}


_FORMULA_LEAD_CHARS = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe(value):
    """Prefix a string cell that would be read as a formula (Excel/Sheets CSV
    import) with a single quote, so scraped titles/URLs stay inert text."""
    if isinstance(value, str) and value.startswith(_FORMULA_LEAD_CHARS):
        return "'" + value
    return value


def _csv_path(profil: str) -> Path:
    DATA.mkdir(exist_ok=True)
    return DATA / f"kept_{profil}.csv"


def regenerate(conn, profil: str) -> Path:
    rows = db.list_for_sheet(conn, profil)
    path = _csv_path(profil)
    tmp = path.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HEADERS)
        for r in rows:
            found = (r["found_at"] or "")[:10]
            applied = (r["applied_at"] or "")[:10]
            w.writerow([found,
                        _csv_safe(r["entreprise"]), _csv_safe(r["titre"]), _csv_safe(r["lieu"]),
                        (r["date_debut"] or ""), r["score"], _csv_safe(r["url"]),
                        r["source"], STATUS.get(r["queue_status"], r["queue_status"]),
                        applied, "", ""])
    os.replace(tmp, path)   # atomic replace (never a truncated file)
    return path
