"""
Send the Telegram digest ("N offers [Start]") for a profile.
Used by the scheduled scan: after a scan, if new offers are queued, we ping.
The bot (running continuously) handles the Start button.
"""

import sys
sys.path.insert(0, "src")

import requests  # noqa: E402
import appconfig  # noqa: E402
import db  # noqa: E402


def send_digest(profil: str) -> int:
    profil = appconfig.validate_profil(profil)
    token = appconfig.read_secret(f"secrets/telegram_{profil}_token.txt")
    chat = appconfig.read_secret("secrets/telegram_chat_id.txt")
    conn = db.connect()
    n = db.count_pending(conn, profil)
    if n == 0:
        return 0
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat,
                "text": f"☀️ {n} new {profil} offer(s) to review.",
                "reply_markup": {"inline_keyboard": [
                    [{"text": "▶️ Start", "callback_data": "begin"}]]},
            }, timeout=30)
    except Exception as e:  # noqa: BLE001
        # requests exceptions embed the full request URL (token included):
        # never let the raw exception surface, here or to a caller's traceback
        raise RuntimeError(f"sendMessage failed: {type(e).__name__}") from None
    return n


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "alternance"
    print("digest sent for", p, ":", send_digest(p), "offer(s)")
