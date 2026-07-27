"""
Integration Google Sheet.

- onglets Alternance / Stage 2 alimentes par les bots
- onglet Stage 1 = archive (import de Stages.xlsx AVEC ses couleurs)
- colonne Resultat = menu deroulant, coloriage auto de la ligne
- les saisies manuelles (Resultat, Notes) sont preservees a chaque sync
- passage auto en "Plus de 3 semaines" 21 jours apres la candidature
"""

from datetime import date
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials

import appconfig
import db

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

# Ordre des colonnes (Type et Contrat supprimes, Date debut + Notes ajoutees)
HEADERS = ["Date ajout", "Entreprise", "Titre", "Lieu", "Date debut", "Score",
           "Lien", "Source", "Statut", "Date candidature", "Resultat", "Notes"]
NCOLS = len(HEADERS)
COL_LIEN = 6        # index 0-based de "Lien"
COL_RESULTAT = 10   # index 0-based de "Resultat" (colonne K)

STATUT = {"kept": "A postuler", "applied": "Postule"}

# Options du menu deroulant Resultat
RESULTAT_OPTIONS = ["Plus de 3 semaines", "Non", "Entretien", "Accepte", "En cours"]


def client(cfg):
    gs = cfg["google_sheet"]
    creds = Credentials.from_service_account_file(
        str(appconfig.ROOT / gs["credentials_file"]), scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(gs["spreadsheet_id"])


def ensure_ws(sh, title, rows=200, cols=NCOLS):
    try:
        return sh.worksheet(title)
    except gspread.WorksheetNotFound:
        return sh.add_worksheet(title=title, rows=rows, cols=cols)


def _read_manual(ws):
    """Lignes deja dans l'onglet : {lien: ligne} + lignes sans lien mais non vides.
    Tout est preserve, pour ne jamais ecraser une saisie manuelle."""
    by_url, keyless = {}, []
    try:
        vals = ws.get_all_values()
    except Exception:
        return by_url, keyless
    for r in vals[1:]:
        if len(r) > COL_LIEN and r[COL_LIEN]:
            by_url[r[COL_LIEN]] = r
        elif any((c or "").strip() for c in r):
            keyless.append(r)  # ligne ajoutee a la main sans lien (ex: candidature spontanee)
    return by_url, keyless


def _res_notes(row):
    """Resultat + Notes d'une ligne existante (liste de cellules)."""
    res = row[COL_RESULTAT] if len(row) > COL_RESULTAT else ""
    notes = row[COL_RESULTAT + 1] if len(row) > COL_RESULTAT + 1 else ""
    return res, notes


def _rows_from_db(conn, profil, manual, keyless, delai_jours):
    today = date.today()
    out = []
    db_urls = set()
    for r in db.list_for_sheet(conn, profil):
        url = r["url"]
        db_urls.add(url)
        res, notes = _res_notes(manual.get(url, []))
        # auto "Plus de 3 semaines" si postule depuis > delai et resultat vide
        if not res and r["queue_status"] == "applied" and r["applied_at"]:
            try:
                jours = (today - date.fromisoformat(r["applied_at"][:10])).days
                if jours >= delai_jours:
                    res = "Plus de 3 semaines"
            except ValueError:
                pass
        out.append([
            (r["found_at"] or "")[:10],
            r["entreprise"], r["titre"], r["lieu"],
            (r["date_debut"] or ""), r["score"], url, r["source"],
            STATUT.get(r["queue_status"], r["queue_status"]),
            (r["applied_at"] or ""), res, notes,
        ])
    # lignes ajoutees a la main dans l'onglet (URL absente de la DB) : preservees
    for url, row in manual.items():
        if url not in db_urls:
            out.append((list(row) + [""] * NCOLS)[:NCOLS])
    # lignes manuelles sans lien : preservees aussi
    for row in keyless:
        out.append((list(row) + [""] * NCOLS)[:NCOLS])
    return out


def _dropdown_request(ws):
    return {"setDataValidation": {
        "range": {"sheetId": ws.id, "startRowIndex": 1,
                  "startColumnIndex": COL_RESULTAT, "endColumnIndex": COL_RESULTAT + 1},
        "rule": {
            "condition": {"type": "ONE_OF_LIST",
                          "values": [{"userEnteredValue": v} for v in RESULTAT_OPTIONS]},
            "showCustomUi": True, "strict": False,
        }}}


def _color_rules(ws, sep=";"):
    """Ligne entiere coloree selon Resultat (col K) : rouge = mort, vert = positif."""
    rng = {"sheetId": ws.id, "startRowIndex": 1, "startColumnIndex": 0,
           "endColumnIndex": NCOLS}
    def rule(regex, r, g, b):
        return {"addConditionalFormatRule": {"index": 0, "rule": {
            "ranges": [rng],
            "booleanRule": {
                "condition": {"type": "CUSTOM_FORMULA", "values": [
                    {"userEnteredValue": f'=REGEXMATCH($K2{sep}"{regex}")'}]},
                "format": {"backgroundColor": {"red": r, "green": g, "blue": b}},
            }}}}
    return [
        rule("(?i)^non|refus|plus de 3|sans r", 0.96, 0.80, 0.80),  # rouge = mort
        rule("(?i)entretien|accept|positif|oui", 0.85, 0.92, 0.83),  # vert = positif
    ]


def sync_values(sh, conn, cfg, profil):
    """Reecrit les valeurs en preservant Resultat/Notes ; pose le menu deroulant."""
    onglet = cfg["profils"][profil]["onglet"]
    delai = cfg.get("comportement", {}).get("delai_sans_reponse_jours", 21)
    ws = ensure_ws(sh, onglet)
    manual, keyless = _read_manual(ws)
    data = [HEADERS] + _rows_from_db(conn, profil, manual, keyless, delai)
    ws.clear()
    ws.update(values=data, range_name="A1")
    ws.format("A1:L1", {"textFormat": {"bold": True,
              "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
              "backgroundColor": {"red": 0.12, "green": 0.16, "blue": 0.27},
              "horizontalAlignment": "CENTER"})
    ws.freeze(rows=1)
    try:
        sh.batch_update({"requests": [_dropdown_request(ws)]})
    except Exception as e:
        print("  (menu deroulant ignore:", e, ")")
    return ws


def push_profile(sh, conn, cfg, profil):
    """Setup complet d'un onglet : valeurs + menu + regles de couleur (une fois)."""
    ws = sync_values(sh, conn, cfg, profil)
    locale = (sh.fetch_sheet_metadata().get("properties", {})
              .get("locale", "en_US"))
    sep = ";" if str(locale).lower().startswith("fr") else ","
    try:
        sh.batch_update({"requests": _color_rules(ws, sep)})
    except Exception as e:
        print("  (couleurs conditionnelles ignorees:", e, ")")
    return ws


def quick_push(profil):
    """Pour le bot : connexion + reecriture de l'onglet du profil."""
    cfg = appconfig.load_config()
    conn = db.connect()
    sh = client(cfg)
    return sync_values(sh, conn, cfg, profil)


# --------------------------------------------------------------------------
# Import de l'archive Stages.xlsx avec ses couleurs
# --------------------------------------------------------------------------
def _excel_fill(cell):
    """Couleur de fond d'une cellule Excel -> (r,g,b) 0..1, ou None."""
    if cell.fill is None or cell.fill.patternType != "solid":
        return None
    fg = cell.fill.fgColor
    if fg is None:
        return None
    if fg.type == "rgb" and isinstance(fg.rgb, str) and fg.rgb not in ("00000000", "FFFFFFFF"):
        h = fg.rgb[-6:]
        return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)
    if fg.type == "theme":
        # approximations (theme Office par defaut)
        return {9: (0.80, 0.90, 0.75), 6: (0.80, 0.90, 0.75),
                5: (0.99, 0.85, 0.70), 4: (0.99, 0.85, 0.70)}.get(fg.theme)
    return None


def import_archive(sh, cfg, xlsx_path: Path):
    from openpyxl import load_workbook
    onglet = cfg["google_sheet"]["onglet_archive"]
    wb = load_workbook(xlsx_path)
    src = wb.active

    values, colors = [], []
    for row in src.iter_rows():
        values.append([("" if c.value is None else str(c.value)) for c in row])
        colors.append(_excel_fill(row[0]))  # couleur = fond de la colonne A

    ncols = max((len(r) for r in values), default=10)
    ws = ensure_ws(sh, onglet, rows=max(len(values) + 5, 50), cols=max(ncols, 10))
    ws.clear()
    if not values:
        return ws, 0
    ws.update(values=values, range_name="A1")
    ws.format(f"A1:{chr(64 + ncols)}1", {"textFormat": {"bold": True}})
    ws.freeze(rows=1)

    # couleurs de ligne (par blocs pour limiter les requetes)
    reqs = []
    for i, col in enumerate(colors):
        if not col or i == 0:  # saute l'en-tete
            continue
        r, g, b = col
        reqs.append({"repeatCell": {
            "range": {"sheetId": ws.id, "startRowIndex": i, "endRowIndex": i + 1,
                      "startColumnIndex": 0, "endColumnIndex": ncols},
            "cell": {"userEnteredFormat": {"backgroundColor": {"red": r, "green": g, "blue": b}}},
            "fields": "userEnteredFormat.backgroundColor"}})
    for k in range(0, len(reqs), 200):
        sh.batch_update({"requests": reqs[k:k + 200]})
    return ws, len(values) - 1
