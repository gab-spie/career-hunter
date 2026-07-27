"""
Score de pertinence /10 d'une offre, base sur les mots-cles du config
et le niveau de diplome vise.

Regle : le TITRE compte plus que la description. Une offre dont le titre
contient un mot exclu (vente, commercial, comptable...) SANS aucun mot
fort finance est ecartee (score 0).
"""

import unicodedata


def _norm(s: str) -> str:
    """minuscule + sans accents, pour matcher de facon robuste."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()


def score_offer(titre: str, description: str, diplome_eu, cfg: dict,
                entreprise: str = "") -> dict:
    """
    Renvoie {score: float 0..10, exclue: bool, signaux: list[str]}.
    diplome_eu : niveau europeen (5=Bac+2, 6=Bac+3, 7=Bac+5) ou None.
    entreprise : nom employeur, pour le bonus employeurs cibles.
    """
    mc = cfg["mots_cles"]
    forts = [_norm(x) for x in mc["forts"]]
    moyens = [_norm(x) for x in mc["moyens"]]
    exclus = [_norm(x) for x in mc["exclus"]]
    exclus_durs = [_norm(x) for x in mc.get("exclus_durs", [])]

    t = _norm(titre)
    d = _norm(description)
    td = t + " " + d
    signaux = []

    # Exclusions DURES : ecartent toujours (droit, avocat...), meme avec mot fort
    for e in exclus_durs:
        if e in t:
            return {"score": 0.0, "exclue": True, "signaux": ["exclu_dur:" + e.strip()]}

    forts_titre = [f for f in forts if f in t]
    forts_desc = [f for f in forts if f in d]
    moyens_titre = [m for m in moyens if m in t]
    moyens_desc = [m for m in moyens if m in d]
    exclus_titre = [e for e in exclus if e in t]

    # Ecartee : mot exclu dans le titre et aucun mot fort nulle part
    if exclus_titre and not forts_titre and not forts_desc:
        return {"score": 0.0, "exclue": True,
                "signaux": ["exclu:" + exclus_titre[0]]}

    score = 0.0
    if forts_titre:
        score += 6.0
        signaux.append("fort/titre:" + forts_titre[0])
        # bonus si plusieurs signaux forts
        extra = min(len(set(forts_titre + forts_desc)) - 1, 3)
        score += 0.5 * extra
    elif forts_desc:
        score += 3.5
        signaux.append("fort/desc:" + forts_desc[0])
    elif moyens_titre:
        score += 4.0
        signaux.append("moyen/titre:" + moyens_titre[0])
    elif moyens_desc:
        score += 2.0
        signaux.append("moyen/desc:" + moyens_desc[0])

    # Bonus employeur cible (banque / boutique / fonds)
    ec = cfg.get("entreprises_cibles", {})
    ent = _norm(entreprise)
    if ent:
        for nom in ec.get("noms", []):
            if _norm(nom) in ent:
                score += ec.get("bonus", 3.5)
                signaux.append("employeur:" + nom)
                break

    # Diplome
    dip = cfg.get("diplome", {})
    cible = dip.get("cible_europeen", 7)
    if diplome_eu is not None:
        if diplome_eu >= cible:
            score += dip.get("bonus_si_cible", 2.0)
            signaux.append("diplome:cible")
        elif diplome_eu <= 5:
            score -= dip.get("malus_si_trop_bas", 3.0)
            signaux.append("diplome:trop_bas")
        else:
            score += 0.5

    score = max(0.0, min(10.0, score))
    return {"score": round(score, 1), "exclue": False, "signaux": signaux}
