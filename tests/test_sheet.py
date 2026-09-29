import sheet


def _row(status):
    row = [""] * sheet.NCOLS
    row[sheet.COL_STATUS] = status
    return row


def test_applied_typed_by_hand_is_detected():
    assert sheet._typed_applied(_row("Applied"))
    assert sheet._typed_applied(_row("Postulé"))


def test_to_apply_is_not_applied():
    assert not sheet._typed_applied(_row("To apply"))
    assert not sheet._typed_applied(_row("A postuler"))
    assert not sheet._typed_applied(_row(""))
