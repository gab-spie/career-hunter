"""
Career Hunter Telegram bot (raw API + long polling, light and reliable).

Flow:
  Startup -> digest "N offers, [Start]"
  Start   -> one card at a time
  Card    -> [Keep] [Skip] [Pause]
  Keep    -> written to the CSV/Sheet mirror, card becomes [Apply] [Mark applied]
  Skip    -> never proposed again, next card
  Pause   -> stops, /resume to continue

Health: a green ping at startup, a red ping on a clean stop, /status on
demand, and a debrief every evening at 20:30 sent by the bot itself (no
debrief = the bot is down).

Usage: python3 telegram_bot.py [alternance|stage]
Two bots = two instances (one token per profile).
"""

import sys
import html
import time
import signal
from datetime import date, datetime

import requests

sys.path.insert(0, "src")
import appconfig  # noqa: E402
import db  # noqa: E402
import sink  # noqa: E402
import sheet  # noqa: E402
import stats  # noqa: E402

PROFIL = appconfig.validate_profil(sys.argv[1] if len(sys.argv) > 1 else "alternance")
TOKEN = appconfig.read_secret(f"secrets/telegram_{PROFIL}_token.txt")
CHAT_ID = appconfig.read_secret("secrets/telegram_chat_id.txt")
API = f"https://api.telegram.org/bot{TOKEN}"

paused = False
START = datetime.now()

DEBRIEF_HOUR, DEBRIEF_MINUTE = 20, 30

# Menu shown when the user types "/" in Telegram
COMMANDS = [
    {"command": "go", "description": "Review the queued offers"},
    {"command": "status", "description": "Bot health and today's numbers"},
    {"command": "resume", "description": "Resume after a pause"},
    {"command": "start", "description": "Help"},
]


def api(method: str, **params):
    """Resilient Telegram call: never raises, returns {} on a network failure.
    Retries 3 times: a network blip must not swallow a card, an Apply link or
    the next card (the DB would move on while the chat stays still)."""
    for attempt in range(3):
        try:
            r = requests.post(f"{API}/{method}", json=params, timeout=20)
            return r.json()
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                print(f"  api {method} failed (3 tries): "
                      f"{type(e).__name__}: {appconfig.scrub(str(e))}")
                return {}
            time.sleep(1.5)
    return {}


def kb(rows):
    return {"inline_keyboard": rows}


def card_text(o) -> str:
    title = html.escape(o["titre"] or "")
    company = html.escape(o["entreprise"] or "?")
    location = html.escape(o["lieu"] or "?")
    contract = html.escape(o["contrat"] or "")
    start = o["date_debut"] or ""
    start_line = ("📅 start date to check (offer unreadable)\n" if start == "to check"
                  else f"📅 starts {html.escape(start)}\n" if start else "")
    return (f"🎯 <b>{title}</b>\n"
            f"🏢 {company} · 📍 {location}\n"
            f"📄 {contract}\n"
            f"{start_line}"
            f"⭐ {o['score']}/10")


def send_card(conn, o):
    markup = kb([
        [{"text": "✅ Keep", "callback_data": f"keep:{o['id']}"},
         {"text": "❌ Skip", "callback_data": f"pass:{o['id']}"}],
        [{"text": "⏸️ Pause", "callback_data": "pause"}],
    ])
    res = api("sendMessage", chat_id=CHAT_ID, text=card_text(o),
              parse_mode="HTML", reply_markup=markup)
    mid = res.get("result", {}).get("message_id")
    # if the send failed (no message_id), leave the offer 'pending' to re-propose
    # it, rather than losing it as 'proposed'
    if mid:
        db.set_status(conn, o["id"], "proposed", tg_message_id=mid)


def send_next(conn):
    if paused:
        return
    o = db.next_pending(conn, PROFIL)
    if not o:
        api("sendMessage", chat_id=CHAT_ID,
            text="✅ Queue empty, all done. Nice work.")
        return
    send_card(conn, o)


def send_digest(conn):
    n = db.count_pending(conn, PROFIL)
    if n == 0:
        api("sendMessage", chat_id=CHAT_ID,
            text=f"☀️ Nothing new for {PROFIL}. Standing by.")
        return
    api("sendMessage", chat_id=CHAT_ID,
        text=f"☀️ {n} {PROFIL} offer(s) to review.",
        reply_markup=kb([[{"text": "▶️ Start", "callback_data": "begin"}]]))


def _sync_sheet():
    """Push the Google Sheet tab. Silent if offline: the DB and CSV stay the
    source of truth, the Sheet re-syncs on the next scan."""
    try:
        sheet.quick_push(PROFIL)
    except Exception as e:  # noqa: BLE001
        print("  (Google Sheet not updated now:", e, ")")


def on_keep(conn, oid, chat_id, mid):
    o = db.get_offer(conn, oid)
    if not o:
        return
    db.set_status(conn, oid, "kept")
    sink.regenerate(conn, PROFIL)
    _sync_sheet()
    txt = f"✅ <b>Kept</b>\n🏢 {html.escape(o['entreprise'] or '?')} · {html.escape(o['titre'] or '')}"
    markup = kb([
        [{"text": "🔗 Apply", "url": o["url"]}],
        [{"text": "✔️ Mark applied", "callback_data": f"applied:{oid}"}],
    ])
    api("editMessageText", chat_id=chat_id, message_id=mid, text=txt,
        parse_mode="HTML", reply_markup=markup)
    send_next(conn)


def on_pass(conn, oid, chat_id, mid):
    o = db.get_offer(conn, oid)
    db.set_status(conn, oid, "passed")
    title = html.escape(o["titre"] or "") if o else ""
    api("editMessageText", chat_id=chat_id, message_id=mid,
        text=f"❌ Skipped · {title}", parse_mode="HTML")
    send_next(conn)


def on_applied(conn, oid, chat_id, mid):
    o = db.get_offer(conn, oid)
    if not o:
        return
    db.set_applied(conn, oid, date.today().isoformat())
    sink.regenerate(conn, PROFIL)
    _sync_sheet()
    txt = (f"✔️ <b>Applied</b> on {date.today().isoformat()}\n"
           f"🏢 {html.escape(o['entreprise'] or '?')} · {html.escape(o['titre'] or '')}")
    api("editMessageText", chat_id=chat_id, message_id=mid, text=txt, parse_mode="HTML")


def handle_callback(conn, cq):
    global paused
    msg = cq.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    from_id = cq.get("from", {}).get("id")
    if str(chat_id) != str(CHAT_ID) or str(from_id) != str(CHAT_ID):
        return  # not the owner: ignore silently
    data = cq.get("data", "")
    mid = msg.get("message_id")
    api("answerCallbackQuery", callback_query_id=cq["id"])

    if data == "begin":
        send_next(conn)
    elif data == "pause":
        paused = True
        api("sendMessage", chat_id=chat_id,
            text="⏸️ Paused. Type /resume whenever you want to continue.")
    elif data.startswith("keep:"):
        on_keep(conn, int(data[5:]), chat_id, mid)
    elif data.startswith("pass:"):
        on_pass(conn, int(data[5:]), chat_id, mid)
    elif data.startswith("applied:"):
        on_applied(conn, int(data[8:]), chat_id, mid)


def handle_message(conn, msg):
    global paused
    if str(msg.get("chat", {}).get("id")) != str(CHAT_ID):
        return  # not the owner: ignore silently
    text = (msg.get("text") or "").strip().lower()
    if text == "/status":
        send_status(conn)
        return
    if text in ("/go", "/resume", "/start"):
        paused = False
        if text == "/start":
            api("sendMessage", chat_id=msg["chat"]["id"],
                text="Career Hunter bot ready. Type /go to see offers, "
                     "/status for the bot health.")
        send_digest(conn) if text == "/start" else send_next(conn)


def ping_online():
    now = datetime.now().strftime("%d/%m %H:%M")
    api("sendMessage", chat_id=CHAT_ID, text=f"🟢 {PROFIL} bot online · {now}")


def ping_offline(*_):
    """Stop handler (launchd SIGTERM, Ctrl+C): warn, then exit."""
    now = datetime.now().strftime("%d/%m %H:%M")
    api("sendMessage", chat_id=CHAT_ID, text=f"🔴 {PROFIL} bot stopped · {now}")
    sys.exit(0)


def _funnel(s) -> str:
    return (f"Scans today: {s['scans']}\n"
            f"Offers analysed: {s['raw']}\n"
            f"Dropped (wrong contract): {s['wrong_contract']}\n"
            f"Dropped (off target period): {s['off_intake']}\n"
            f"New offers kept: {s['new']}\n")


def send_debrief(conn):
    s = stats.today_summary(PROFIL)
    day = date.today().strftime("%d/%m/%Y")
    body = (_funnel(s) if s["scans"]
            else "No scan recorded today (Mac asleep at the scheduled times?)\n")
    api("sendMessage", chat_id=CHAT_ID,
        text=(f"📊 Debrief {day} · {PROFIL}\n🟢 Bot online\n{body}"
              f"Queued for review: {db.count_pending(conn, PROFIL)}"))


def send_status(conn):
    """Reply to /status: live state + today's numbers."""
    s = stats.today_summary(PROFIL)
    api("sendMessage", chat_id=CHAT_ID,
        text=(f"🟢 {PROFIL} bot online\n"
              f"Up since {START.strftime('%d/%m %H:%M')}\n{_funnel(s)}"
              f"Queued for review: {db.count_pending(conn, PROFIL)}"))


def check_debrief(conn):
    """Send the debrief once a day, from 20:30. The bot sends it itself, so
    a missing debrief means the bot is down."""
    now = datetime.now()
    too_early = (now.hour, now.minute) < (DEBRIEF_HOUR, DEBRIEF_MINUTE)
    if too_early or stats.debrief_sent(PROFIL):
        return
    send_debrief(conn)
    stats.mark_debrief_sent(PROFIL)


def main():
    signal.signal(signal.SIGTERM, ping_offline)
    signal.signal(signal.SIGINT, ping_offline)
    conn = db.connect()
    # protected startup: a network hiccup or a lock must not kill the bot
    try:
        api("deleteWebhook")
        api("setMyCommands", commands=COMMANDS)
        ping_online()
        send_digest(conn)
    except Exception as e:  # noqa: BLE001
        print(f"startup error: {type(e).__name__}: {appconfig.scrub(str(e))}")
    offset = None
    while True:
        try:
            params = {"timeout": 25}
            if offset is not None:
                params["offset"] = offset
            res = requests.get(f"{API}/getUpdates", params=params, timeout=35).json()
            for u in res.get("result", []):
                offset = u["update_id"] + 1
                # one failing update must not break processing of the next ones
                try:
                    if "callback_query" in u:
                        handle_callback(conn, u["callback_query"])
                    elif "message" in u:
                        handle_message(conn, u["message"])
                except Exception as e:  # noqa: BLE001
                    print(f"update error: {type(e).__name__}: {appconfig.scrub(str(e))}")
            check_debrief(conn)
        except Exception as e:  # noqa: BLE001
            print(f"loop error: {type(e).__name__}: {appconfig.scrub(str(e))}")
            time.sleep(3)


if __name__ == "__main__":
    main()
