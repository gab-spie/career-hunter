import stats


def test_daily_summary_and_debrief_state(tmp_path, monkeypatch):
    monkeypatch.setattr(stats, "LOGS", tmp_path)
    monkeypatch.setattr(stats, "STATS_FILE", tmp_path / "scan_stats.jsonl")
    stats.record_scan("stage", raw=100, wrong_contract=60, off_intake=30, skipped=0, new=4, pending=4)
    stats.record_scan("stage", raw=50, wrong_contract=30, off_intake=15, skipped=1, new=1, pending=5)
    stats.record_scan("alternance", raw=10, wrong_contract=5, off_intake=5, skipped=0, new=0, pending=0)
    s = stats.today_summary("stage")
    assert s["scans"] == 2 and s["raw"] == 150 and s["new"] == 5 and s["pending"] == 5

    assert not stats.debrief_sent("stage")
    stats.mark_debrief_sent("stage")
    assert stats.debrief_sent("stage")
    assert not stats.debrief_sent("alternance")  # one state per profile
