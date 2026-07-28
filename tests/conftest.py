import pytest


@pytest.fixture
def cfg():
    """Minimal scoring config for tests."""
    return {
        "keywords": {
            "strong": ["m&a", "private equity", "corporate finance"],
            "medium": ["financial analyst"],
            "hard_exclude": ["lawyer", "legal"],
            "exclude": ["sales", "retail", "accountant"],
        },
        "target_employers": {"bonus": 3.5, "names": ["rothschild", "bnp paribas"]},
        "degree": {"target_eu": 7, "bonus_if_target": 2.0, "penalty_if_low": 3.0},
    }
