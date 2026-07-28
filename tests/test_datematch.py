import datematch

INTAKE = {"annee": 2027, "mois": [8, 9, 10, 11], "strict": True}


def test_year_in_title_kept():
    assert datematch.passe({"titre": "Alternance M&A rentree 2027", "description": ""}, INTAKE)


def test_earlier_year_rejected():
    assert not datematch.passe({"titre": "Alternance 2026-2027", "description": ""}, INTAKE)


def test_spring_month_rejected():
    assert not datematch.passe({"titre": "Alternance M&A - Janvier 2027", "description": ""}, INTAKE)


def test_known_start_date_kept():
    assert datematch.passe({"titre": "x", "date_debut": "2027-09-01"}, INTAKE)


def test_known_start_date_wrong_year_rejected():
    assert not datematch.passe({"titre": "x", "date_debut": "2026-09-01"}, INTAKE)


def test_no_date_rejected_when_strict():
    assert not datematch.passe({"titre": "Analyste M&A", "description": ""}, INTAKE)
