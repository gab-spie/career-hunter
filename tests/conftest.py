import pytest


@pytest.fixture
def cfg():
    """Minimal scoring config for tests."""
    return {
        "mots_cles": {
            "forts": ["m&a", "private equity", "corporate finance"],
            "moyens": ["analyste financier"],
            "exclus_durs": ["avocat", "juridique"],
            "exclus": ["vente", "commercial", "comptable"],
        },
        "entreprises_cibles": {"bonus": 3.5, "noms": ["rothschild", "bnp paribas"]},
        "diplome": {"cible_europeen": 7, "bonus_si_cible": 2.0, "malus_si_trop_bas": 3.0},
    }
