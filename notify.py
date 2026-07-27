"""
Envoi du digest Telegram ("N offres [Commencer]") pour un profil.
Utilise par le scan planifie : apres un scan, si de nouvelles offres sont
en file, on previent. Le bot (qui tourne en continu) gere le bouton Commencer.
"""

import sys
sys.path.insert(0, "src")

import requests  # noqa: E402
import appconfig  # noqa: E402
import db  # noqa: E402


def send_digest(profil: str) -> int:
    token = appconfig.read_secret(f"secrets/telegram_{profil}_token.txt")
    chat = appconfig.read_secret("secrets/telegram_chat_id.txt")
    conn = db.connect()
    n = db.count_pending(conn, profil)
    if n == 0:
        return 0
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat,
            "text": f"☀️ {n} nouvelle(s) offre(s) {profil} a passer en revue.",
            "reply_markup": {"inline_keyboard": [
                [{"text": "▶️ Commencer", "callback_data": "begin"}]]},
        }, timeout=30)
    return n


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "alternance"
    print("digest envoye pour", p, ":", send_digest(p), "offre(s)")
