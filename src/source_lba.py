"""
Source connector: La Bonne Alternance (official API, apprentissage.beta.gouv.fr).

GET /api/job/v1/search?latitude=..&longitude=..&radius=..
Header: Authorization: Bearer <token>

Returns a list of normalized offers (dicts) ready for scoring and the DB.
France + work-study only.
"""

import requests

BASE = "https://api.apprentissage.beta.gouv.fr/api/job/v1/search"


def _pick(*vals):
    for v in vals:
        if v:
            return v
    return None


def normalize(job: dict, profile: str) -> dict | None:
    """Turn a raw API job into a normalized offer. None if unusable."""
    offer = job.get("offer") or {}
    workplace = job.get("workplace") or {}
    apply_ = job.get("apply") or {}
    contract = job.get("contract") or {}
    ident = job.get("identifier") or {}

    url = apply_.get("url")
    title = offer.get("title")
    if not url or not title:
        return None  # no link or no title: unusable

    loc = (workplace.get("location") or {}).get("address")
    degree_eu = (offer.get("target_diploma") or {}).get("european")
    try:
        degree_eu = int(degree_eu) if degree_eu is not None else None
    except (ValueError, TypeError):
        degree_eu = None

    ctype = contract.get("type")
    if isinstance(ctype, list):
        ctype = ", ".join(str(x) for x in ctype) or None

    return {
        "url": url,
        "source": "labonnealternance",
        "external_id": ident.get("partner_job_id") or ident.get("id"),
        "profil": profile,
        "entreprise": _pick(workplace.get("brand"),
                            workplace.get("legal_name"),
                            workplace.get("name")),
        "titre": title,
        "contrat": ctype or "alternance",
        "lieu": loc,
        "date_debut": contract.get("start"),
        "diplome_eu": degree_eu,
        "description": offer.get("description") or "",
    }


def fetch(profile_cfg: dict, profile_name: str, token: str,
          timeout: int = 30) -> list[dict]:
    """Query the API for each of the profile's locations; return normalized offers."""
    headers = {"Authorization": f"Bearer {token}"}
    seen = set()
    offers = []
    for loc in profile_cfg.get("locations", []):
        params = {
            "latitude": loc["latitude"],
            "longitude": loc["longitude"],
            "radius": loc.get("radius_km", 30),
        }
        # an error on one location must not drop offers from the others
        try:
            r = requests.get(BASE, headers=headers, params=params, timeout=timeout)
            r.raise_for_status()
            data = r.json()
        except Exception as e:  # noqa: BLE001
            print(f"  official API location {loc.get('name', '?')} failed: {e}")
            continue
        for job in data.get("jobs", []):
            o = normalize(job, profile_name)
            if not o:
                continue
            if o["url"] in seen:
                continue
            seen.add(o["url"])
            offers.append(o)
    return offers
