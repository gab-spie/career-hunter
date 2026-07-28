"""
Bot Telegram Job Radar (raw API + long polling, leger et fiable).

Flux :
  Demarrage -> digest "N offres, [Commencer]"
  Commencer -> 1 carte a la fois
  Carte     -> [Retenir] [Passer] [Pause]
  Retenir   -> ecrit dans le miroir CSV/Sheet, carte devient [Postuler] [Marquer postule]
  Passer    -> jamais reproposee, carte suivante
  Pause     -> stoppe, /reprendre pour continuer

Usage : python3 telegram_bot.py [alternance|stage]
Deux bots = deux instances (un token par profil).
"""

import sys
import html
import time
from datetime import date

import requests

sys.path.insert(0, "src")
import appconfig  # noqa: E402
import db  # noqa: E402
import sink  # noqa: E402
import sheet  # noqa: E402

PROFIL = sys.argv[1] if len(sys.argv) > 1 else "alternance"
TOKEN = appconfig.read_secret(f"secrets/telegram_{PROFIL}_token.txt")
CHAT_ID = appconfig.read_secret("secrets/telegram_chat_id.txt")
API = f"https://api.telegram.org/bot{TOKEN}"

paused = False


def api(method: str, **params):
    """Appel Telegram resilient : ne leve jamais, renvoie {} en cas de souci reseau."""
    try:
        r = requests.post(f"{API}/{method}", json=params, timeout=40)
        return r.json()
    except Exception as e:  # noqa: BLE001
        print(f"  api {method} KO: {e}")
        return {}


def kb(rows):
    return {"inline_keyboard": rows}


def card_text(o) -> str:
    titre = html.escape(o["titre"] or "")
    ent = html.escape(o["entreprise"] or "?")
    lieu = html.escape(o["lieu"] or "?")
    contrat = html.escape(o["contrat"] or "")
    return (f"🎯 <b>{titre}</b>\n"
            f"🏢 {ent} · 📍 {lieu}\n"
            f"📄 {contrat}\n"
            f"⭐ {o['score']}/10")


def send_card(conn, o):
    markup = kb([
        [{"text": "✅ Retenir", "callback_data": f"keep:{o['id']}"},
         {"text": "❌ Passer", "callback_data": f"pass:{o['id']}"}],
        [{"text": "⏸️ Pause", "callback_data": "pause"}],
    ])
    res = api("sendMessage", chat_id=CHAT_ID, text=card_text(o),
              parse_mode="HTML", reply_markup=markup)
    mid = res.get("result", {}).get("message_id")
    # si l'envoi a echoue (pas de message_id), on laisse l'offre en 'pending'
    # pour la reproposer, plutot que de la perdre en 'proposed'
    if mid:
        db.set_status(conn, o["id"], "proposed", tg_message_id=mid)


def send_next(conn):
    if paused:
        return
    o = db.next_pending(conn, PROFIL)
    if not o:
        api("sendMessage", chat_id=CHAT_ID,
            text="✅ File vide, tout est traite. Beau boulot.")
        return
    send_card(conn, o)


def send_digest(conn):
    n = db.count_pending(conn, PROFIL)
    if n == 0:
        api("sendMessage", chat_id=CHAT_ID,
            text=f"☀️ Rien de nouveau cote {PROFIL}. Je reste en veille.")
        return
    api("sendMessage", chat_id=CHAT_ID,
        text=f"☀️ {n} offre(s) {PROFIL} a passer en revue.",
        reply_markup=kb([[{"text": "▶️ Commencer", "callback_data": "begin"}]]))


def _sync_sheet():
    """Pousse l'onglet Google Sheet. Silencieux si hors-ligne : la DB et le
    CSV restent la source de verite, la Sheet se resynchronisera au scan suivant."""
    try:
        sheet.quick_push(PROFIL)
    except Exception as e:
        print("  (Google Sheet non mis a jour maintenant:", e, ")")


def on_keep(conn, oid, chat_id, mid):
    o = db.get_offer(conn, oid)
    if not o:
        return
    db.set_status(conn, oid, "kept")
    sink.regenerate(conn, PROFIL)
    _sync_sheet()
    txt = f"✅ <b>Retenue</b>\n🏢 {html.escape(o['entreprise'] or '?')} · {html.escape(o['titre'] or '')}"
    markup = kb([
        [{"text": "🔗 Postuler", "url": o["url"]}],
        [{"text": "✔️ Marquer postule", "callback_data": f"applied:{oid}"}],
    ])
    api("editMessageText", chat_id=chat_id, message_id=mid, text=txt,
        parse_mode="HTML", reply_markup=markup)
    send_next(conn)


def on_pass(conn, oid, chat_id, mid):
    o = db.get_offer(conn, oid)
    db.set_status(conn, oid, "passed")
    titre = html.escape(o["titre"] or "") if o else ""
    api("editMessageText", chat_id=chat_id, message_id=mid,
        text=f"❌ Passee · {titre}", parse_mode="HTML")
    send_next(conn)


def on_applied(conn, oid, chat_id, mid):
    o = db.get_offer(conn, oid)
    if not o:
        return
    db.set_applied(conn, oid, date.today().isoformat())
    sink.regenerate(conn, PROFIL)
    _sync_sheet()
    txt = (f"✔️ <b>Postule</b> le {date.today().isoformat()}\n"
           f"🏢 {html.escape(o['entreprise'] or '?')} · {html.escape(o['titre'] or '')}")
    api("editMessageText", chat_id=chat_id, message_id=mid, text=txt, parse_mode="HTML")


def handle_callback(conn, cq):
    global paused
    data = cq.get("data", "")
    msg = cq.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    mid = msg.get("message_id")
    api("answerCallbackQuery", callback_query_id=cq["id"])

    if data == "begin":
        send_next(conn)
    elif data == "pause":
        paused = True
        api("sendMessage", chat_id=chat_id,
            text="⏸️ En pause. Tape /reprendre quand tu veux continuer.")
    elif data.startswith("keep:"):
        on_keep(conn, int(data[5:]), chat_id, mid)
    elif data.startswith("pass:"):
        on_pass(conn, int(data[5:]), chat_id, mid)
    elif data.startswith("applied:"):
        on_applied(conn, int(data[8:]), chat_id, mid)


def handle_message(conn, msg):
    global paused
    text = (msg.get("text") or "").strip().lower()
    if text in ("/go", "/reprendre", "/start"):
        paused = False
        if text == "/start":
            api("sendMessage", chat_id=msg["chat"]["id"],
                text="Bot Job Radar pret. Tape /go pour voir les offres.")
        send_digest(conn) if text == "/start" else send_next(conn)


def main():
    conn = db.connect()
    # demarrage protege : un hoquet reseau ou un verrou ne doit pas tuer le bot
    try:
        api("deleteWebhook")
        send_digest(conn)
    except Exception as e:  # noqa: BLE001
        print("erreur demarrage:", e)
    offset = None
    while True:
        try:
            params = {"timeout": 25}
            if offset is not None:
                params["offset"] = offset
            res = requests.get(f"{API}/getUpdates", params=params, timeout=35).json()
            for u in res.get("result", []):
                offset = u["update_id"] + 1
                # un update qui plante ne doit pas casser le traitement des suivants
                try:
                    if "callback_query" in u:
                        handle_callback(conn, u["callback_query"])
                    elif "message" in u:
                        handle_message(conn, u["message"])
                except Exception as e:  # noqa: BLE001
                    print("erreur update:", e)
        except Exception as e:  # noqa: BLE001
            print("erreur boucle:", e)
            time.sleep(3)


if __name__ == "__main__":
    main()
