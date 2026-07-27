"""
Filtre de date de rentree : ne garder que les offres visant la bonne rentree
(ex : septembre 2027), a partir de la date de debut (source fiable) ou, a
defaut, de l'annee/mois lus dans le titre.
"""

import re
import unicodedata

MOIS_PRINTEMPS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet"]


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def passe(offer: dict, rentree: dict) -> bool:
    """True si l'offre vise la rentree cible.
    rentree = {annee: 2027, mois: [8,9,10,11], strict: true}."""
    annee = int(rentree.get("annee", 2027))
    mois_ok = set(rentree.get("mois", [8, 9, 10, 11]))
    strict = rentree.get("strict", True)

    # 1) date de debut connue (ex La Bonne Alternance : "2027-09-01")
    dd = (offer.get("date_debut") or "")[:10]
    m = re.match(r"(\d{4})-(\d{2})", dd)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        return y == annee and mo in mois_ok

    # 2) sinon, chercher des annees dans le titre (+ description si dispo)
    txt = _norm((offer.get("titre") or "") + " " + (offer.get("description") or ""))
    annees = [int(y) for y in re.findall(r"20\d{2}", txt)]
    if annees:
        if any(y < annee for y in annees):
            return False  # une annee anterieure = depart plus tot (ex 2026-2027)
        if annee not in annees:
            return False  # parle d'une autre annee (ex 2028 seul)
        if any(mp in txt for mp in MOIS_PRINTEMPS):
            return False  # rentree de printemps (ex "janvier 2027"), pas la cible
        return True

    # 3) aucune date : strict -> on rejette
    return not strict
