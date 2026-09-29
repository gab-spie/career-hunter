import datematch

INTAKE = {"year": 2027, "months": [8, 9, 10, 11], "strict": True}
SPRING = {"year": 2027, "months": [3, 4, 5], "strict": True}


def test_year_in_title_kept():
    assert datematch.passes({"titre": "Alternance M&A rentree 2027", "description": ""}, INTAKE)


def test_earlier_year_rejected():
    assert not datematch.passes({"titre": "Alternance 2026-2027", "description": ""}, INTAKE)


def test_spring_month_rejected_for_autumn_intake():
    assert not datematch.passes({"titre": "Alternance M&A - Janvier 2027", "description": ""}, INTAKE)


def test_known_start_date_kept():
    assert datematch.passes({"titre": "x", "date_debut": "2027-09-01"}, INTAKE)


def test_known_start_date_wrong_year_rejected():
    assert not datematch.passes({"titre": "x", "date_debut": "2026-09-01"}, INTAKE)


def test_no_date_rejected_when_strict():
    assert not datematch.passes({"titre": "Analyste M&A", "description": ""}, INTAKE)


def test_spring_target_from_title():
    assert datematch.passes({"titre": "Stage Corporate Finance - Mars 2027"}, SPRING)


def test_date_read_in_description():
    offer = {"titre": "M&A Intern", "description": "Start date: January 2027 and March 2027."}
    assert datematch.passes(offer, SPRING)
    assert datematch.found_date(offer, SPRING) == "2027-03"


def test_or_between_months_in_description():
    offer = {"titre": "Stage M&A", "description": "Stage de 6 mois a partir de janvier ou mars 2027"}
    assert datematch.passes(offer, SPRING)


def test_named_period():
    assert datematch.passes({"titre": "Investment Banking H1-2027 Off-Cycle"}, SPRING)


def test_unrelated_year_in_description_ignored():
    offer = {"titre": "Stage Private Equity", "description": "Firm founded in 2015, 6-month internship"}
    assert not datematch.passes(offer, SPRING)  # no start date anywhere: strict drop


def test_wrong_start_in_description_rejected():
    offer = {"titre": "Stage PE", "description": "Debut du stage : septembre 2026."}
    assert not datematch.passes(offer, SPRING)


def test_unreadable_offer_kept_for_manual_check():
    assert datematch.passes({"titre": "Stage Private Equity", "unreadable": True}, SPRING)
