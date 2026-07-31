"""Loading of config.yaml and secrets."""

import re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"

PROFIL_RE = re.compile(r"^[a-z0-9_-]+$")

# matches a Telegram-style "/bot<token>" URL path segment, whatever the token
# looks like, so it can be stripped out before anything is printed or logged
_BOT_TOKEN_RE = re.compile(r"(/bot)[^/\s]+")


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_secret(rel_path: str) -> str:
    """Read a secret file (e.g. secrets/lba_token.txt) and return its content."""
    p = ROOT / rel_path
    return p.read_text(encoding="utf-8").strip()


def validate_profil(profil: str) -> str:
    """Reject anything that isn't a plain slug, so a PROFIL value can never be
    used to escape the secrets/data directories (path traversal)."""
    if not profil or not PROFIL_RE.match(profil):
        raise ValueError(f"invalid profil {profil!r}: expected ^[a-z0-9_-]+$")
    return profil


def scrub(text: str) -> str:
    """Strip a Telegram bot token (or any /bot<...>/ path segment) from a
    string before it is printed or logged. requests exceptions embed the
    full request URL, token included, so this must be applied to every
    exception message that may come from a Telegram API call."""
    return _BOT_TOKEN_RE.sub(r"\1<redacted>", str(text))
