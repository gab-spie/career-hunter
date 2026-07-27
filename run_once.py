"""
Un passage complet, pour la planification : scanne les sources, et si de
nouvelles offres passent les filtres, envoie le digest Telegram.

Usage : python3 run_once.py [alternance|stage]
"""

import sys
sys.path.insert(0, "src")

import scan  # noqa: E402  (scan.py ajoute src au path et importe les sources)
import notify  # noqa: E402


def main():
    profil = sys.argv[1] if len(sys.argv) > 1 else "alternance"
    try:
        new, pending = scan.scan_profil(profil)
    except Exception as e:  # noqa: BLE001
        print("scan en echec:", e)
        return
    print(f"{profil} : {new} nouvelle(s), {pending} en file")
    if new > 0:
        try:
            notify.send_digest(profil)
            print("digest envoye")
        except Exception as e:  # noqa: BLE001
            print("digest non envoye:", e)


if __name__ == "__main__":
    main()
