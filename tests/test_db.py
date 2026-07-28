import db


def _offer(url, entreprise, titre):
    return {"url": url, "source": "x", "profil": "alternance",
            "entreprise": entreprise, "titre": titre}


def test_dedup_by_url(tmp_path):
    c = db.connect(tmp_path / "t.sqlite3")
    assert db.add_offer(c, _offer("u1", "BNP Paribas", "Analyste M&A"))
    assert not db.add_offer(c, _offer("u1", "BNP Paribas", "Analyste M&A"))


def test_cross_source_dedup(tmp_path):
    c = db.connect(tmp_path / "t.sqlite3")
    assert db.add_offer(c, _offer("u1", "Rothschild & Co", "Analyste M&A"))
    # same offer via another source (different URL, different case) -> rejected
    assert not db.add_offer(c, _offer("u2", "ROTHSCHILD & CO", "analyste m&a"))


def test_unknown_company_is_not_falsely_deduped(tmp_path):
    c = db.connect(tmp_path / "t.sqlite3")
    # two genuinely distinct offers with no company parsed must both survive
    assert db.add_offer(c, _offer("u1", None, "Stagiaire M&A"))
    assert db.add_offer(c, _offer("u2", None, "Stagiaire M&A"))
