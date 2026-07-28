import scoring


def test_strong_title_scores_high(cfg):
    r = scoring.score_offer("Analyste M&A", "", 7, cfg, entreprise="Rothschild")
    assert not r["exclue"]
    assert r["score"] >= 6


def test_hard_exclusion_wins_over_strong(cfg):
    # "avocat" is a hard exclusion: dropped even though the title says "M&A"
    r = scoring.score_offer("Avocat - Corporate M&A", "", 7, cfg, entreprise="X")
    assert r["exclue"]
    assert r["score"] == 0


def test_soft_exclusion_without_strong(cfg):
    # "commercial" is a soft exclusion and there is no strong keyword -> dropped
    r = scoring.score_offer("Commercial terrain B2B", "", 7, cfg, entreprise="X")
    assert r["exclue"]


def test_employer_bonus_raises_score(cfg):
    hit = scoring.score_offer("Analyste M&A", "", 7, cfg, entreprise="Rothschild")["score"]
    miss = scoring.score_offer("Analyste M&A", "", 7, cfg, entreprise="Inconnu")["score"]
    assert hit > miss


def test_missing_diploma_is_handled(cfg):
    r = scoring.score_offer("Analyste M&A", "", None, cfg)
    assert not r["exclue"]
