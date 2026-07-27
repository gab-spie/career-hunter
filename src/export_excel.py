"""
Fichier de suivi Excel local, regenere depuis la base.

UN seul fichier vivant (Suivi_Alternance.xlsx / Suivi_Stage.xlsx), toujours
a jour, jamais 40 versions. Couleur de ligne selon le Resultat :
  Refuse -> rouge, Entretien/positif -> vert, Sans reponse -> gris.
"""

import os
from pathlib import Path
import db
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment

ROOT = Path(__file__).resolve().parent.parent

HEADERS = ["Date ajout", "Entreprise", "Titre", "Lieu", "Date debut", "Score",
           "Lien", "Source", "Statut", "Date candidature", "Resultat", "Notes"]
COL_LIEN = 6
COL_RESULTAT = 10

STATUT = {"kept": "A postuler", "applied": "Postule"}


def _read_existing(path: Path):
    """Recupere les saisies manuelles d'un xlsx existant : {lien: (resultat, notes)}
    + lignes sans lien. Pour ne rien ecraser au prochain export."""
    by_url, keyless = {}, []
    if not path.exists():
        return by_url, keyless
    try:
        ws = load_workbook(path).active
    except Exception:
        return by_url, keyless
    for row in ws.iter_rows(min_row=2, values_only=True):
        cells = ["" if c is None else str(c) for c in row]
        if len(cells) > COL_LIEN and cells[COL_LIEN]:
            by_url[cells[COL_LIEN]] = cells   # ligne complete (pas seulement res/notes)
        elif any(c.strip() for c in cells):
            keyless.append(cells)
    return by_url, keyless

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


def _append_colored(ws, ligne):
    ws.append(ligne)
    fill = _fill_for(ligne[COL_RESULTAT] if len(ligne) > COL_RESULTAT else "")
    if fill:
        for c in ws[ws.max_row]:
            c.fill = fill


def export(conn, profil: str, nom_fichier: str) -> Path:
    path = ROOT / nom_fichier
    by_url, keyless = _read_existing(path)   # preserve les saisies manuelles
    rows = db.list_for_sheet(conn, profil)

    wb = Workbook()
    ws = wb.active
    ws.title = profil.capitalize()
    ws.append(HEADERS)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = FILL_ENTETE
        c.alignment = Alignment(horizontal="center")

    def _res_notes(cells):
        res = cells[COL_RESULTAT] if len(cells) > COL_RESULTAT else ""
        notes = cells[COL_RESULTAT + 1] if len(cells) > COL_RESULTAT + 1 else ""
        return res, notes

    db_urls = set()
    for r in rows:
        url = r["url"]
        db_urls.add(url)
        res, notes = _res_notes(by_url.get(url, []))
        _append_colored(ws, [
            (r["found_at"] or "")[:10], r["entreprise"], r["titre"], r["lieu"],
            (r["date_debut"] or ""), r["score"], url, r["source"],
            STATUT.get(r["queue_status"], r["queue_status"]),
            (r["applied_at"] or ""), res, notes,
        ])
    # lignes manuelles (lien absent de la DB, ou sans lien) : preservees en entier
    for url, cells in by_url.items():
        if url not in db_urls:
            _append_colored(ws, (list(cells) + [""] * len(HEADERS))[:len(HEADERS)])
    for cells in keyless:
        _append_colored(ws, (list(cells) + [""] * len(HEADERS))[:len(HEADERS)])

    widths = [12, 22, 46, 24, 12, 7, 40, 16, 12, 14, 16, 20]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w
    ws.freeze_panes = "A2"

    tmp = path.with_suffix(".xlsx.tmp")
    wb.save(tmp)
    os.replace(tmp, path)   # ecriture atomique
    return path


if __name__ == "__main__":
    c = db.connect()
    p = export(c, "alternance", "Suivi_Alternance.xlsx")
    print("Ecrit:", p, "|", len(db.list_for_sheet(c, "alternance")), "offres")
