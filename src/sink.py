"""
Miroir CSV local des offres retenues (en attendant le Google Sheet).

Regenere data/kept_<profil>.csv depuis la base a chaque changement.
Memes colonnes que le futur onglet Google Sheet, pour une bascule sans douleur.
"""

import csv
from pathlib import Path

import db

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

HEADERS = ["Date ajout", "Entreprise", "Titre", "Lieu", "Date debut", "Score",
           "Lien", "Source", "Statut", "Date candidature", "Resultat", "Notes"]

STATUT = {"kept": "A postuler", "applied": "Postule"}


def _csv_path(profil: str) -> Path:
    DATA.mkdir(exist_ok=True)
    return DATA / f"kept_{profil}.csv"


def regenerate(conn, profil: str) -> Path:
    rows = db.list_for_sheet(conn, profil)
    path = _csv_path(profil)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HEADERS)
        for r in rows:
            found = (r["found_at"] or "")[:10]
            applied = (r["applied_at"] or "")[:10]
            w.writerow([found, r["entreprise"], r["titre"], r["lieu"],
                        (r["date_debut"] or ""), r["score"], r["url"],
                        r["source"], STATUT.get(r["queue_status"], r["queue_status"]),
                        applied, "", ""])
    return path
