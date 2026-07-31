"""
One full pass, for scheduling: scan the sources, and if new offers clear the
filters, send the Telegram digest.

Usage: python3 run_once.py [alternance|stage]
"""

import sys
sys.path.insert(0, "src")

import scan  # noqa: E402  (scan.py adds src to the path and imports the sources)
import notify  # noqa: E402
import appconfig  # noqa: E402


def main():
    profil = sys.argv[1] if len(sys.argv) > 1 else "alternance"
    try:
        profil = appconfig.validate_profil(profil)
    except ValueError as e:
        print("invalid profil:", e)
        return
    try:
        new, pending = scan.scan_profil(profil)
    except Exception as e:  # noqa: BLE001
        print(f"scan failed: {type(e).__name__}: {appconfig.scrub(str(e))}")
        return
    print(f"{profil}: {new} new, {pending} queued")
    if new > 0:
        try:
            notify.send_digest(profil)
            print("digest sent")
        except Exception as e:  # noqa: BLE001
            # notify.send_digest already scrubs the token from its own
            # exceptions; scrub again here in case of any other failure mode
            print(f"digest not sent: {type(e).__name__}: {appconfig.scrub(str(e))}")


if __name__ == "__main__":
    main()
