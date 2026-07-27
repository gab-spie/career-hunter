"""Chargement du config.yaml et des secrets."""

from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_secret(rel_path: str) -> str:
    """Lit un fichier secret (ex: secrets/lba_token.txt) et renvoie son contenu."""
    p = ROOT / rel_path
    return p.read_text(encoding="utf-8").strip()
