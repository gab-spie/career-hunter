"""
Relevance score (out of 10) for an offer, based on the config keywords and
the target degree level.

Rule: the TITLE matters more than the description. An offer whose title holds
an excluded word (sales, retail, accountant...) WITHOUT any strong finance
keyword is dropped (score 0).
"""

import unicodedata


def _norm(s: str) -> str:
    """Lowercase + accent-stripped, for robust matching."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()


def score_offer(title: str, description: str, degree_eu, cfg: dict,
                company: str = "") -> dict:
    """
    Return {score: float 0..10, excluded: bool, signals: list[str]}.
    degree_eu : European level (5=Bac+2, 6=Bac+3, 7=Master) or None.
    company   : employer name, for the target-employer bonus.
    """
    kw = cfg["keywords"]
    strong = [_norm(x) for x in kw["strong"]]
    medium = [_norm(x) for x in kw["medium"]]
    exclude = [_norm(x) for x in kw["exclude"]]
    hard_exclude = [_norm(x) for x in kw.get("hard_exclude", [])]

    t = _norm(title)
    d = _norm(description)
    signals = []

    # HARD exclusions: always drop (legal, lawyer...), even with a strong keyword
    for e in hard_exclude:
        if e in t:
            return {"score": 0.0, "excluded": True, "signals": ["hard_exclude:" + e.strip()]}

    strong_title = [f for f in strong if f in t]
    strong_desc = [f for f in strong if f in d]
    medium_title = [m for m in medium if m in t]
    medium_desc = [m for m in medium if m in d]
    exclude_title = [e for e in exclude if e in t]

    # Dropped: excluded word in the title and no strong keyword anywhere
    if exclude_title and not strong_title and not strong_desc:
        return {"score": 0.0, "excluded": True,
                "signals": ["exclude:" + exclude_title[0]]}

    score = 0.0
    if strong_title:
        score += 6.0
        signals.append("strong/title:" + strong_title[0])
        # bonus for several strong signals
        extra = min(len(set(strong_title + strong_desc)) - 1, 3)
        score += 0.5 * extra
    elif strong_desc:
        score += 3.5
        signals.append("strong/desc:" + strong_desc[0])
    elif medium_title:
        score += 4.0
        signals.append("medium/title:" + medium_title[0])
    elif medium_desc:
        score += 2.0
        signals.append("medium/desc:" + medium_desc[0])

    # Target-employer bonus (bank / boutique / fund)
    te = cfg.get("target_employers", {})
    comp = _norm(company)
    if comp:
        for name in te.get("names", []):
            if _norm(name) in comp:
                score += te.get("bonus", 3.5)
                signals.append("employer:" + name)
                break

    # Degree
    deg = cfg.get("degree", {})
    target = deg.get("target_eu", 7)
    if degree_eu is not None:
        if degree_eu >= target:
            score += deg.get("bonus_if_target", 2.0)
            signals.append("degree:target")
        elif degree_eu <= 5:
            score -= deg.get("penalty_if_low", 3.0)
            signals.append("degree:too_low")
        else:
            score += 0.5

    score = max(0.0, min(10.0, score))
    return {"score": round(score, 1), "excluded": False, "signals": signals}
