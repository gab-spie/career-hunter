import contrat


def test_work_study_title_kept():
    o = {"source": "x", "titre": "Alternance Analyste M&A", "contrat_label": ""}
    assert contrat.type_ok(o, "alternance")


def test_graduate_role_rejected_from_work_study():
    o = {"source": "efc", "titre": "M&A Analyst - Graduate Programme", "contrat_label": "CDI"}
    assert not contrat.type_ok(o, "alternance")


def test_official_api_is_work_study():
    o = {"source": "labonnealternance", "titre": "Analyste M&A", "contrat_label": None}
    assert contrat.type_ok(o, "alternance")


def test_internship_feed_is_strict():
    assert contrat.type_ok({"source": "x", "titre": "Stage M&A", "contrat_label": ""}, "stage")
    assert not contrat.type_ok({"source": "x", "titre": "Alternance M&A", "contrat_label": ""}, "stage")
