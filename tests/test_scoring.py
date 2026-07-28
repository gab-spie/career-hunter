import scoring


def test_strong_title_scores_high(cfg):
    r = scoring.score_offer("M&A Analyst", "", 7, cfg, company="Rothschild")
    assert not r["excluded"]
    assert r["score"] >= 6


def test_hard_exclusion_wins_over_strong(cfg):
    # "lawyer" is a hard exclusion: dropped even though the title says "M&A"
    r = scoring.score_offer("Lawyer - Corporate M&A", "", 7, cfg, company="X")
    assert r["excluded"]
    assert r["score"] == 0


def test_soft_exclusion_without_strong(cfg):
    # "sales" is a soft exclusion and there is no strong keyword -> dropped
    r = scoring.score_offer("Sales representative B2B", "", 7, cfg, company="X")
    assert r["excluded"]


def test_employer_bonus_raises_score(cfg):
    hit = scoring.score_offer("M&A Analyst", "", 7, cfg, company="Rothschild")["score"]
    miss = scoring.score_offer("M&A Analyst", "", 7, cfg, company="Unknown")["score"]
    assert hit > miss


def test_missing_degree_is_handled(cfg):
    r = scoring.score_offer("M&A Analyst", "", None, cfg)
    assert not r["excluded"]
