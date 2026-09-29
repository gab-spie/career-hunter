"""
Intake-date filter: keep only offers targeting the wanted period (e.g.
September 2027 for work-study, March 2027 for an internship).

Signals, most reliable first:
  1. a known start date from the source ("2027-09-01")
  2. "month year" or named periods ("March 2027", "H1 2027") read in the title
     or in the full description, when a source provides one
  3. a bare year in the title
The target months come from the config, not from a hard-coded season, so the
same filter works for an autumn intake and a spring one.
"""

import re
import unicodedata

# Month names -> number, French + English (job titles and descriptions come in
# both languages). Kept in French on purpose: this is data to match, not code
# vocabulary. English "may" is left out on purpose: too ambiguous (modal verb).
MONTH_NAMES = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "decembre": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}
_MONTH_RE = re.compile(r"\b(" + "|".join(MONTH_NAMES) + r")\b")

# "month ... year" in free text: every month takes the first year that follows
# within 25 characters, so "January or March 2027" yields both months.
_PAIR_RE = re.compile(r"\b(" + "|".join(MONTH_NAMES) + r")\b(?=[^.\n]{0,25}?\b(20\d{2})\b)")

# Named periods -> covered months ("H1 2027", "printemps 2027", "spring 2027")
_PERIODS = {
    "h1": range(1, 7), "s1": range(1, 7), "q1": range(1, 4),
    "h2": range(7, 13), "s2": range(7, 13),
    "printemps": range(3, 6), "spring": range(3, 6),
    "ete": range(6, 9), "summer": range(6, 9),
    "automne": range(9, 12), "fall": range(9, 12), "autumn": range(9, 12),
    "debut": range(1, 4), "early": range(1, 4),
}
_PERIOD_RE = re.compile(r"\b(" + "|".join(_PERIODS) + r")\b\W{0,3}(20\d{2})\b")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def _pairs(txt: str) -> set[tuple[int, int]]:
    """Every (month, year) readable in an already normalized text."""
    out = {(MONTH_NAMES[m], int(y)) for m, y in _PAIR_RE.findall(txt)}
    for p, y in _PERIOD_RE.findall(txt):
        out |= {(m, int(y)) for m in _PERIODS[p]}
    return out


def _all_text(offer: dict) -> str:
    return " \n ".join(_norm(offer.get(k) or "")
                       for k in ("titre", "description", "page_text"))


def passes(offer: dict, intake: dict) -> bool:
    """True if the offer targets the wanted period.
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

    # 2) "month year" or named periods in the title or the description. One hit
    # in the target is enough: a description often also quotes an application
    # deadline, hence the "any".
    pairs = _pairs(_all_text(offer))
    if pairs:
        return any(y == year and mo in months_ok for mo, y in pairs)

    # 3) bare years, in the TITLE only (a description holds unrelated years:
    # "founded in 2015", "since 2020"...)
    title = _norm(offer.get("titre") or "")
    years = [int(y) for y in re.findall(r"20\d{2}", title)]
    if years:
        if any(y < year for y in years):
            return False  # an earlier year means an earlier start (e.g. 2026-2027)
        if year not in years:
            return False  # mentions another year only (e.g. 2028)
        named = {MONTH_NAMES[n] for n in _MONTH_RE.findall(title)}
        if named:
            return bool(named & months_ok)
        return True  # right year, month unknown: keep

    # 4) no date at all. If the full offer could not even be read (blocked
    # page, timeout), keep it: it is flagged "to check" for the user.
    if offer.get("unreadable"):
        return True
    return not strict


def found_date(offer: dict, intake: dict) -> str | None:
    """First target date read in the offer ("2027-03"), to show on the card."""
    year = int(intake.get("year", 2027))
    months_ok = set(intake.get("months", []))
    good = sorted(mo for mo, y in _pairs(_all_text(offer)) if y == year and mo in months_ok)
    return f"{year}-{good[0]:02d}" if good else None
