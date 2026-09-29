"""
Scan: collect offers, score them, and queue (in the DB) those above the
profile threshold. Run once a day (or by hand).

Usage: python3 scan.py [alternance|stage]
"""

import sys
import time
sys.path.insert(0, "src")

import appconfig
import source_lba
import scoring
import datematch
import contrat
import db
import stats


def _collect(profile_name, pcfg, cfg):
    """Collect offers from every active source.
    Extra sources are optional: if a module is missing, we keep going with the
    official API alone."""
    offers = []
    # 1) official API (La Bonne Alternance, France, work-study)
    try:
        token = appconfig.read_secret("secrets/lba_token.txt")
        offers += source_lba.fetch(pcfg, profile_name, token)
    except Exception as e:  # noqa: BLE001
        print("  official API source failed:", e)
    # 2+) extra sources listed in the config (loaded if present)
    for mod_name in cfg.get("extra_sources", []):
        try:
            mod = __import__(mod_name)
        except ImportError:
            continue
        try:
            batch = mod.fetch(profile_name, cfg)
        except Exception as e:  # noqa: BLE001
            print(f"  source {mod_name} failed:", e)
            continue
        # remember which module produced each offer, for the optional
        # describe() hook (full offer text, see sources/base.py)
        describe = getattr(mod, "describe", None)
        for o in batch:
            o["_describe"] = describe
        offers += batch
    return offers


def _read_full_offer(o: dict, pause: float) -> None:
    """Optional step: ask the source for the full offer text, so the start
    date ("from March 2027") is found even when the title says nothing."""
    describe = o.get("_describe")
    if not describe:
        return
    try:
        text, readable, clean = describe(o)
    except Exception as e:  # noqa: BLE001
        print("  full offer not read:", e)
        text, readable, clean = "", False, False
    time.sleep(pause)
    if clean and text:
        o["description"] = text      # the offer alone: used for date AND score
    elif text:
        o["page_text"] = text        # a whole page: used for the date only
    if not readable and not o.get("description"):
        o["unreadable"] = True


def _shown_date(o: dict, intake: dict | None) -> str | None:
    if o.get("date_debut"):
        return o["date_debut"][:10]
    if intake:
        d = datematch.found_date(o, intake)
        if d:
            return d
    return "to check" if o.get("unreadable") else None


def scan_profil(profile_name: str) -> tuple[int, int]:
    cfg = appconfig.load_config()
    pcfg = cfg["profiles"][profile_name]
    threshold = pcfg["min_score"]
    read_full = pcfg.get("read_full_offers", False)
    pause = pcfg.get("read_pause_seconds", 2)

    offers = _collect(profile_name, pcfg, cfg)
    intake = pcfg.get("intake")
    conn = db.connect()
    new_count = 0
    off_intake = 0
    wrong_contract = 0
    skipped = 0
    already_seen = 0
    for o in offers:
        # a malformed offer (missing key, future source) must not break the scan
        try:
            if not o.get("url") or not o.get("titre"):
                skipped += 1
                continue
            # already in the DB: no need to read it again
            if db.offer_exists(conn, o["url"]):
                already_seen += 1
                continue
            # STRICT contract-type filter (work-study-only or internship-only)
            if not contrat.type_ok(o, profile_name):
                wrong_contract += 1
                continue
            if read_full:
                _read_full_offer(o, pause)
            # target-intake filter (e.g. September 2027, March 2027)
            if intake and not datematch.passes(o, intake):
                off_intake += 1
                continue
            r = scoring.score_offer(o.get("titre") or "", o.get("description") or "",
                                    o.get("diplome_eu"), cfg,
                                    company=o.get("entreprise") or "")
            if r["excluded"] or r["score"] < threshold:
                continue
            rec = {
                "url": o["url"],
                "source": o.get("source") or "unknown",
                "external_id": o.get("external_id"),
                "profil": profile_name,
                "entreprise": o.get("entreprise"),
                "titre": o["titre"],
                "contrat": o.get("contrat"),
                "lieu": o.get("lieu"),
                "score": r["score"],
                "date_debut": _shown_date(o, intake),
            }
            if db.add_offer(conn, rec):
                new_count += 1
        except Exception as e:  # noqa: BLE001
            skipped += 1
            print("  offer skipped (error):", e)
    pending = db.count_pending(conn, profile_name)
    print(f"  ({len(offers)} raw, {already_seen} already seen, {wrong_contract} wrong contract, "
          f"{off_intake} off-intake, {skipped} skipped)")
    stats.record_scan(profile_name, len(offers), wrong_contract, off_intake,
                      skipped, new_count, pending)
    return new_count, pending


if __name__ == "__main__":
    profil = sys.argv[1] if len(sys.argv) > 1 else "alternance"
    new, pending = scan_profil(profil)
    print(f"{profil}: {new} new offer(s), {pending} waiting in the queue")
