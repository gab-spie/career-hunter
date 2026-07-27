"""
Fichier de suivi Excel local, regenere depuis la base.

UN seul fichier vivant (Suivi_Alternance.xlsx / Suivi_Stage.xlsx), toujours
a jour, jamais 40 versions. Couleur de ligne selon le Resultat :
  Refuse -> rouge, Entretien/positif -> vert, Sans reponse -> gris.
"""

from pathlib import Path
import db
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

ROOT = Path(__file__).resolve().parent.parent

HEADERS = ["Date ajout", "Entreprise", "Titre", "Lieu", "Date debut", "Score",
           "Lien", "Source", "Statut", "Date candidature", "Resultat", "Notes"]

STATUT = {"kept": "A postuler", "applied": "Postule"}

FILL_ROUGE = PatternFill("solid", fgColor="F4CCCC")
FILL_VERT = PatternFill("solid", fgColor="D9EAD3")
FILL_GRIS = PatternFill("solid", fgColor="D9D9D9")
FILL_ENTETE = PatternFill("solid", fgColor="1F2A44")


def _fill_for(resultat: str):
    r = (resultat or "").lower()
    if "refus" in r:
        return FILL_ROUGE
    if "entretien" in r or "positif" in r or "accept" in r:
        return FILL_VERT
    if "sans reponse" in r or "sans réponse" in r:
        return FILL_GRIS
    return None


def export(conn, profil: str, nom_fichier: str) -> Path:
    rows = db.list_for_sheet(conn, profil)
    wb = Workbook()
    ws = wb.active
    ws.title = profil.capitalize()

    ws.append(HEADERS)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = FILL_ENTETE
        c.alignment = Alignment(horizontal="center")

    for r in rows:
        date_ajout = (r["found_at"] or "")[:10]
        resultat = ""  # a remplir a la main dans le Sheet
        ligne = [
            date_ajout,
            r["entreprise"],
            r["titre"],
            r["lieu"],
            (r["date_debut"] or ""),
            r["score"],
            r["url"],
            r["source"],
            STATUT.get(r["queue_status"], r["queue_status"]),
            (r["applied_at"] or ""),
            resultat,
            "",  # Notes
        ]
        ws.append(ligne)
        fill = _fill_for(resultat)
        if fill:
            for c in ws[ws.max_row]:
                c.fill = fill

    widths = [12, 22, 46, 24, 12, 7, 40, 16, 12, 14, 16, 20]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w
    ws.freeze_panes = "A2"

    path = ROOT / nom_fichier
    wb.save(path)
    return path


if __name__ == "__main__":
    c = db.connect()
    p = export(c, "alternance", "Suivi_Alternance.xlsx")
    print("Ecrit:", p, "|", len(db.list_for_sheet(c, "alternance")), "offres")
