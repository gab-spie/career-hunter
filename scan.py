"""
Scan : recupere les offres, les score, et met en file (DB) celles qui
depassent le seuil du profil. A lancer 1x/jour (ou a la main).

Usage : python3 scan.py [alternance|stage]
"""

import sys
sys.path.insert(0, "src")

import appconfig
import source_lba
import scoring
import datematch
import contrat
import db


def _collect(profil_nom, pcfg, cfg):
    """Recupere les offres de toutes les sources actives.
    Les sources complementaires sont optionnelles : si leur module n'est pas
    present, on continue avec l'API officielle seule."""
    offres = []
    # 1) La Bonne Alternance (API officielle, France, alternance)
    try:
        token = appconfig.read_secret("secrets/lba_token.txt")
        offres += source_lba.fetch(pcfg, profil_nom, token)
    except Exception as e:
        print("  source La Bonne Alternance KO:", e)
    # 2+) Sources complementaires listees dans le config (chargees si presentes)
    for mod_nom in cfg.get("sources_extra", []):
        try:
            mod = __import__(mod_nom)
        except ImportError:
            continue
        try:
            offres += mod.fetch(profil_nom, cfg)
        except Exception as e:
            print(f"  source {mod_nom} KO:", e)
    return offres


def scan_profil(profil_nom: str) -> tuple[int, int]:
    cfg = appconfig.load_config()
    pcfg = cfg["profils"][profil_nom]
    seuil = pcfg["score_min_alerte"]

    offres = _collect(profil_nom, pcfg, cfg)
    rentree = pcfg.get("rentree")
    conn = db.connect()
    nouvelles = 0
    hors_date = 0
    hors_contrat = 0
    ignorees = 0
    for o in offres:
        # une offre malformee (cle manquante, source future) ne casse pas le scan
        try:
            if not o.get("url") or not o.get("titre"):
                ignorees += 1
                continue
            # filtre type de contrat STRICT (alternance-only ou stage-only)
            if not contrat.type_ok(o, profil_nom):
                hors_contrat += 1
                continue
            # filtre rentree visee (ex septembre 2027)
            if rentree and not datematch.passe(o, rentree):
                hors_date += 1
                continue
            r = scoring.score_offer(o.get("titre") or "", o.get("description") or "",
                                    o.get("diplome_eu"), cfg,
                                    entreprise=o.get("entreprise") or "")
            if r["exclue"] or r["score"] < seuil:
                continue
            rec = {
                "url": o["url"],
                "source": o.get("source") or "inconnue",
                "external_id": o.get("external_id"),
                "profil": profil_nom,
                "entreprise": o.get("entreprise"),
                "titre": o["titre"],
                "contrat": o.get("contrat"),
                "lieu": o.get("lieu"),
                "score": r["score"],
                "date_debut": (o.get("date_debut") or "")[:10] or None,
            }
            if db.add_offer(conn, rec):
                nouvelles += 1
        except Exception as e:  # noqa: BLE001
            ignorees += 1
            print("  offre ignoree (erreur):", e)
    print(f"  ({len(offres)} brutes, {hors_contrat} mauvais contrat, "
          f"{hors_date} hors rentree cible, {ignorees} ignorees)")
    return nouvelles, db.count_pending(conn, profil_nom)


if __name__ == "__main__":
    profil = sys.argv[1] if len(sys.argv) > 1 else "alternance"
    new, pending = scan_profil(profil)
    print(f"{profil} : {new} nouvelle(s) offre(s), {pending} en attente dans la file")
