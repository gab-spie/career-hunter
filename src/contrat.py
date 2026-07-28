"""
STRICT contract-type filter.

The work-study feed keeps ONLY work-study / apprenticeship offers.
The internship feed keeps ONLY internships.
Everything else (permanent, graduate program, VIE...) is dropped.

Signal used, in order of reliability:
  - work-study-only source (official API) -> work-study
  - contract label from the source -> exact word
  - otherwise, words found in the title
"""

import unicodedata

WORK_STUDY = ("altern", "apprenti")
INTERNSHIP = ("stage", "stagiaire", "internship", "summer intern",
              "off-cycle", "summer analyst")


def _n(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def type_ok(offer: dict, profile: str) -> bool:
    label = _n(offer.get("contrat_label") or "")
    title = _n(offer.get("titre") or "")
    src = offer.get("source") or ""
    blob = label + " " + title

    is_work_study = (src == "labonnealternance") or any(w in blob for w in WORK_STUDY)
    is_internship = any(w in blob for w in INTERNSHIP)

    if profile == "alternance":
        return is_work_study
    return is_internship  # internship profile
