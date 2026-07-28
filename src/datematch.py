"""
Intake-date filter: keep only offers targeting the right intake (e.g. September
2027), from the start date (reliable source) or, failing that, from the year and
month read in the title.
"""

import re
import unicodedata

# French month names, matched against (mostly French) job titles like
# "Alternance M&A - Janvier 2027". Kept in French on purpose: this is data to
# match, not code vocabulary.
SPRING_MONTHS_FR = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet"]


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def passes(offer: dict, intake: dict) -> bool:
    """True if the offer targets the wanted intake.
    intake = {year: 2027, months: [8,9,10,11], strict: true}."""
    year = int(intake.get("year", 2027))
    months_ok = set(intake.get("months", [8, 9, 10, 11]))
    strict = intake.get("strict", True)

    # 1) known start date (e.g. official API: "2027-09-01")
    start = (offer.get("date_debut") or "")[:10]
    m = re.match(r"(\d{4})-(\d{2})", start)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        return y == year and mo in months_ok

    # 2) otherwise, look for years in the title (+ description if present)
    txt = _norm((offer.get("titre") or "") + " " + (offer.get("description") or ""))
    years = [int(y) for y in re.findall(r"20\d{2}", txt)]
    if years:
        if any(y < year for y in years):
            return False  # an earlier year means an earlier start (e.g. 2026-2027)
        if year not in years:
            return False  # mentions another year only (e.g. 2028)
        if any(mp in txt for mp in SPRING_MONTHS_FR):
            return False  # spring intake (e.g. "janvier 2027"), not the target
        return True

    # 3) no date at all: strict mode rejects
    return not strict
