"""
Scan statistics for the daily debrief.

Every scan appends one JSON line to logs/scan_stats.jsonl (the funnel of that
pass). Each bot reads the lines of the day at 20:30 to send a recap. A small
per-profile state file makes sure the debrief is sent once per evening, even
across restarts.
"""

import json
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
STATS_FILE = LOGS / "scan_stats.jsonl"


def _debrief_file(profil: str) -> Path:
    # one state file PER profile, otherwise one bot would block the other's debrief
    return LOGS / f"last_debrief_{profil}.txt"


def record_scan(profil: str, raw: int, wrong_contract: int, off_intake: int,
                skipped: int, new: int, pending: int) -> None:
    """Append the funnel of the current scan. Never raises (best effort)."""
    try:
        LOGS.mkdir(exist_ok=True)
        row = {"ts": datetime.now().isoformat(timespec="seconds"), "profil": profil,
               "raw": raw, "wrong_contract": wrong_contract, "off_intake": off_intake,
               "skipped": skipped, "new": new, "pending": pending}
        with STATS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as e:  # noqa: BLE001
        print("  stats not recorded:", e)


def today_summary(profil: str) -> dict:
    """Aggregate today's scans for a profile (scans=0 if none)."""
    today = date.today().isoformat()
    s = {"scans": 0, "raw": 0, "wrong_contract": 0, "off_intake": 0,
         "skipped": 0, "new": 0, "pending": 0}
    if not STATS_FILE.exists():
        return s
    for line in STATS_FILE.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("profil") != profil or not r.get("ts", "").startswith(today):
            continue
        s["scans"] += 1
        for k in ("raw", "wrong_contract", "off_intake", "skipped", "new"):
            s[k] += r.get(k, 0)
        s["pending"] = r.get("pending", s["pending"])  # last known value of the day
    return s


def debrief_sent(profil: str, day: str | None = None) -> bool:
    day = day or date.today().isoformat()
    try:
        return _debrief_file(profil).read_text(encoding="utf-8").strip() == day
    except Exception:  # noqa: BLE001
        return False


def mark_debrief_sent(profil: str, day: str | None = None) -> None:
    try:
        LOGS.mkdir(exist_ok=True)
        _debrief_file(profil).write_text(day or date.today().isoformat(), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        print("  debrief state not written:", e)
