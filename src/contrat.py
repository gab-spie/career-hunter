"""
Filtre de type de contrat, STRICT.

Le bot alternance ne garde QUE de l'alternance/apprentissage.
Le bot stage ne garde QUE du stage.
Tout le reste (CDI, graduate program, VIE...) est ecarte.

Signal utilise, par ordre de fiabilite :
  - source alternance-only (La Bonne Alternance) -> alternance
  - label de contrat de la source (eFinancialCareers) -> mot exact
  - a defaut, mots dans le titre
"""

import unicodedata

ALT = ("altern", "apprenti")
STG = ("stage", "stagiaire", "internship", "summer intern", "off-cycle", "summer analyst")


def _n(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def type_ok(offer: dict, profil: str) -> bool:
    label = _n(offer.get("contrat_label") or "")
    titre = _n(offer.get("titre") or "")
    src = offer.get("source") or ""
    blob = label + " " + titre

    is_alt = (src == "labonnealternance") or any(w in blob for w in ALT)
    is_stg = any(w in blob for w in STG)

    if profil == "alternance":
        return is_alt
    return is_stg  # profil stage
