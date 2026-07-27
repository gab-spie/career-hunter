"""
Connecteur source : La Bonne Alternance (API officielle apprentissage.beta.gouv.fr).

GET /api/job/v1/search?latitude=..&longitude=..&radius=..
Header: Authorization: Bearer <token>

Renvoie une liste d'offres normalisees (dicts) pretes pour le scoring et la DB.
France + alternance uniquement.
"""

import requests

BASE = "https://api.apprentissage.beta.gouv.fr/api/job/v1/search"


def _pick(*vals):
    for v in vals:
        if v:
            return v
    return None


def normalize(job: dict, profil: str) -> dict | None:
    """Transforme une offre brute API en offre normalisee. None si inutilisable."""
    offer = job.get("offer") or {}
    workplace = job.get("workplace") or {}
    apply_ = job.get("apply") or {}
    contract = job.get("contract") or {}
    ident = job.get("identifier") or {}

    url = apply_.get("url")
    titre = offer.get("title")
    if not url or not titre:
        return None  # sans lien ou sans titre, inexploitable

    loc = (workplace.get("location") or {}).get("address")
    diplome_eu = (offer.get("target_diploma") or {}).get("european")
    try:
        diplome_eu = int(diplome_eu) if diplome_eu is not None else None
    except (ValueError, TypeError):
        diplome_eu = None

    ctype = contract.get("type")
    if isinstance(ctype, list):
        ctype = ", ".join(str(x) for x in ctype) or None

    return {
        "url": url,
        "source": "labonnealternance",
        "external_id": ident.get("partner_job_id") or ident.get("id"),
        "profil": profil,
        "entreprise": _pick(workplace.get("brand"),
                            workplace.get("legal_name"),
                            workplace.get("name")),
        "titre": titre,
        "contrat": ctype or "alternance",
        "lieu": loc,
        "date_debut": contract.get("start"),
        "diplome_eu": diplome_eu,
        "description": offer.get("description") or "",
    }


def fetch(profil_cfg: dict, profil_nom: str, token: str,
          timeout: int = 30) -> list[dict]:
    """Interroge l'API pour chaque lieu du profil, renvoie les offres normalisees."""
    headers = {"Authorization": f"Bearer {token}"}
    seen = set()
    offres = []
    for lieu in profil_cfg.get("lieux", []):
        params = {
            "latitude": lieu["latitude"],
            "longitude": lieu["longitude"],
            "radius": lieu.get("rayon_km", 30),
        }
        # une erreur sur un lieu ne doit pas perdre les offres des autres lieux
        try:
            r = requests.get(BASE, headers=headers, params=params, timeout=timeout)
            r.raise_for_status()
            data = r.json()
        except Exception as e:  # noqa: BLE001
            print(f"  lba lieu {lieu.get('nom', '?')} KO: {e}")
            continue
        for job in data.get("jobs", []):
            o = normalize(job, profil_nom)
            if not o:
                continue
            if o["url"] in seen:
                continue
            seen.add(o["url"])
            offres.append(o)
    return offres
