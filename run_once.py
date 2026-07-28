"""
One full pass, for scheduling: scan the sources, and if new offers clear the
filters, send the Telegram digest.

Usage: python3 run_once.py [alternance|stage]
"""

import sys
sys.path.insert(0, "src")

import scan  # noqa: E402  (scan.py adds src to the path and imports the sources)
import notify  # noqa: E402


def main():
    profil = sys.argv[1] if len(sys.argv) > 1 else "alternance"
    try:
        new, pending = scan.scan_profil(profil)
    except Exception as e:  # noqa: BLE001
        print("scan failed:", e)
        return
    print(f"{profil}: {new} new, {pending} queued")
    if new > 0:
        try:
            notify.send_digest(profil)
            print("digest sent")
        except Exception as e:  # noqa: BLE001
            print("digest not sent:", e)


if __name__ == "__main__":
    main()
