"""
Base locale SQLite : anti-doublon + file d'attente Telegram.

Source de verite. Une offre est stockee ici AVANT d'etre proposee sur
Telegram. Meme si Telegram plante ou que tu fermes tout, rien n'est perdu
et rien n'est propose deux fois.

Etats d'une offre (colonne queue_status) :
  pending   -> trouvee, pas encore proposee
  proposed  -> carte envoyee sur Telegram, en attente de ton clic
  kept      -> tu as clique "Retenir" (ecrite dans le Google Sheet)
  passed    -> tu as clique "Passer" (jamais reproposee)
  applied   -> tu as clique "Marquer postule" (statut Postule + date)
"""

import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "career_hunter.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS offers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    url           TEXT UNIQUE NOT NULL,   -- cle anti-doublon
    source        TEXT NOT NULL,          -- ex: labonnealternance, wttj
    external_id   TEXT,                   -- id cote source si dispo
    profil        TEXT NOT NULL,          -- alternance | stage
    entreprise    TEXT,
    titre         TEXT,
    contrat       TEXT,
    lieu          TEXT,
    score         REAL,
    date_debut    TEXT,                   -- date de debut du contrat (contract.start)
    dedup_key     TEXT,                   -- entreprise+titre normalises (anti-doublon inter-sources)
    queue_status  TEXT NOT NULL DEFAULT 'pending',
    tg_message_id INTEGER,                -- id du message Telegram
    sheet_row     INTEGER,                -- ligne dans le Google Sheet
    applied_at    TEXT,                   -- date de candidature (clic Postule)
    found_at      TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_offers_status ON offers(profil, queue_status);
"""

# Colonnes ajoutees apres coup : migration douce pour les bases existantes
_MIGRATIONS = {
    "date_debut": "ALTER TABLE offers ADD COLUMN date_debut TEXT",
    "applied_at": "ALTER TABLE offers ADD COLUMN applied_at TEXT",
    "dedup_key": "ALTER TABLE offers ADD COLUMN dedup_key TEXT",
}


def dedup_key(entreprise, titre) -> str:
    """Cle anti-doublon inter-sources : entreprise+titre normalises."""
    def norm(s):
        s = unicodedata.normalize("NFD", str(s or ""))
        s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
        return " ".join(s.split())
    return norm(entreprise) + "|" + norm(titre)


def _migrate(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(offers)")}
    for name, sql in _MIGRATIONS.items():
        if name not in cols:
            conn.execute(sql)
    conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    # timeout : attend jusqu'a 30 s si la base est verrouillee (scan + bot en //)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    # WAL : lecteurs et ecrivain simultanes sans "database is locked"
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def offer_exists(conn: sqlite3.Connection, url: str) -> bool:
    cur = conn.execute("SELECT 1 FROM offers WHERE url = ? LIMIT 1", (url,))
    return cur.fetchone() is not None


def dup_exists(conn: sqlite3.Connection, key: str, profil: str) -> bool:
    """Meme offre deja presente via une autre source (meme entreprise+titre)."""
    if not key or key == "|":
        return False
    cur = conn.execute(
        "SELECT 1 FROM offers WHERE dedup_key = ? AND profil = ? LIMIT 1",
        (key, profil))
    return cur.fetchone() is not None


def add_offer(conn: sqlite3.Connection, offer: dict) -> bool:
    """Ajoute une offre si nouvelle (URL et paire entreprise+titre). Renvoie True si insere."""
    if offer_exists(conn, offer["url"]):
        return False
    key = dedup_key(offer.get("entreprise"), offer.get("titre"))
    # dedup inter-sources UNIQUEMENT si l'entreprise est connue : sinon deux
    # offres distinctes sans nom d'employeur (parsing rate) + intitule generique
    # auraient la meme cle et l'une serait perdue en silence.
    if offer.get("entreprise") and dup_exists(conn, key, offer.get("profil")):
        return False  # deja proposee via une autre source
    now = _now()
    conn.execute(
        """
        INSERT INTO offers
            (url, source, external_id, profil, entreprise, titre, contrat,
             lieu, score, date_debut, dedup_key, queue_status, found_at, updated_at)
        VALUES
            (:url, :source, :external_id, :profil, :entreprise, :titre,
             :contrat, :lieu, :score, :date_debut, :dedup_key, 'pending', :found_at, :updated_at)
        """,
        {
            "external_id": None,
            "entreprise": None,
            "titre": None,
            "contrat": None,
            "lieu": None,
            "score": None,
            "date_debut": None,
            "dedup_key": key,
            **offer,
            "found_at": now,
            "updated_at": now,
        },
    )
    conn.commit()
    return True


def next_pending(conn: sqlite3.Connection, profil: str) -> sqlite3.Row | None:
    """Prochaine offre a proposer, la mieux notee d'abord."""
    cur = conn.execute(
        """
        SELECT * FROM offers
        WHERE profil = ? AND queue_status = 'pending'
        ORDER BY score DESC, found_at ASC
        LIMIT 1
        """,
        (profil,),
    )
    return cur.fetchone()


def count_pending(conn: sqlite3.Connection, profil: str) -> int:
    cur = conn.execute(
        "SELECT COUNT(*) FROM offers WHERE profil = ? AND queue_status = 'pending'",
        (profil,),
    )
    return cur.fetchone()[0]


def set_status(conn: sqlite3.Connection, offer_id: int, status: str,
               tg_message_id: int | None = None,
               sheet_row: int | None = None) -> None:
    fields = ["queue_status = ?", "updated_at = ?"]
    params: list = [status, _now()]
    if tg_message_id is not None:
        fields.append("tg_message_id = ?")
        params.append(tg_message_id)
    if sheet_row is not None:
        fields.append("sheet_row = ?")
        params.append(sheet_row)
    params.append(offer_id)
    conn.execute(f"UPDATE offers SET {', '.join(fields)} WHERE id = ?", params)
    conn.commit()


def get_offer(conn: sqlite3.Connection, offer_id: int) -> sqlite3.Row | None:
    cur = conn.execute("SELECT * FROM offers WHERE id = ?", (offer_id,))
    return cur.fetchone()


def set_applied(conn: sqlite3.Connection, offer_id: int, when: str) -> None:
    conn.execute(
        "UPDATE offers SET queue_status='applied', applied_at=?, updated_at=? WHERE id=?",
        (when, _now(), offer_id),
    )
    conn.commit()


def list_for_sheet(conn: sqlite3.Connection, profil: str) -> list[sqlite3.Row]:
    """Offres retenues ou postulees, pour le Google Sheet / CSV miroir."""
    cur = conn.execute(
        """
        SELECT * FROM offers
        WHERE profil = ? AND queue_status IN ('kept', 'applied')
        ORDER BY found_at ASC
        """,
        (profil,),
    )
    return cur.fetchall()


if __name__ == "__main__":
    c = connect()
    ok = add_offer(c, {
        "url": "https://exemple.test/offre/1",
        "source": "test",
        "profil": "alternance",
        "entreprise": "ACME",
        "titre": "Analyste M&A",
        "contrat": "apprentissage",
        "lieu": "Paris",
        "score": 8.5,
    })
    print("insere:", ok)
    print("pending:", count_pending(c, "alternance"))
    row = next_pending(c, "alternance")
    print("next:", dict(row) if row else None)
