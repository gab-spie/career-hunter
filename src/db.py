"""
Local SQLite store: deduplication + Telegram queue.

Source of truth. An offer is stored here BEFORE being proposed on Telegram.
Even if Telegram crashes or everything is closed, nothing is lost and nothing
is proposed twice.

Offer states (queue_status column):
  pending   -> found, not yet proposed
  proposed  -> card sent on Telegram, awaiting your click
  kept      -> you clicked "Keep" (written to the Google Sheet)
  passed    -> you clicked "Skip" (never proposed again)
  applied   -> you clicked "Mark applied" (status Applied + date)

Note: table columns and dict keys keep the author's French naming
(entreprise, titre, lieu...). See the language note in the README.
"""

import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "career_hunter.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS offers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    url           TEXT UNIQUE NOT NULL,   -- dedup key
    source        TEXT NOT NULL,          -- e.g. labonnealternance
    external_id   TEXT,                   -- source-side id if available
    profil        TEXT NOT NULL,          -- alternance | stage
    entreprise    TEXT,                   -- company
    titre         TEXT,                   -- title
    contrat       TEXT,                   -- contract
    lieu          TEXT,                   -- location
    score         REAL,
    date_debut    TEXT,                   -- contract start date
    dedup_key     TEXT,                   -- normalized company+title (cross-source dedup)
    queue_status  TEXT NOT NULL DEFAULT 'pending',
    tg_message_id INTEGER,                -- Telegram message id
    sheet_row     INTEGER,                -- row in the Google Sheet
    applied_at    TEXT,                   -- application date (Applied click)
    found_at      TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_offers_status ON offers(profil, queue_status);
"""

# Columns added later: soft migration for existing databases
_MIGRATIONS = {
    "date_debut": "ALTER TABLE offers ADD COLUMN date_debut TEXT",
    "applied_at": "ALTER TABLE offers ADD COLUMN applied_at TEXT",
    "dedup_key": "ALTER TABLE offers ADD COLUMN dedup_key TEXT",
}


def dedup_key(entreprise, titre) -> str:
    """Cross-source dedup key: normalized company+title."""
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
    # timeout: wait up to 30 s if the DB is locked (scan + bot in parallel)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    # WAL: concurrent readers and one writer without "database is locked"
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def offer_exists(conn: sqlite3.Connection, url: str) -> bool:
    cur = conn.execute("SELECT 1 FROM offers WHERE url = ? LIMIT 1", (url,))
    return cur.fetchone() is not None


def dup_exists(conn: sqlite3.Connection, key: str, profil: str) -> bool:
    """Same offer already present via another source (same company+title)."""
    if not key or key == "|":
        return False
    cur = conn.execute(
        "SELECT 1 FROM offers WHERE dedup_key = ? AND profil = ? LIMIT 1",
        (key, profil))
    return cur.fetchone() is not None


def add_offer(conn: sqlite3.Connection, offer: dict) -> bool:
    """Add an offer if new (by URL and by company+title). Return True if inserted."""
    if offer_exists(conn, offer["url"]):
        return False
    key = dedup_key(offer.get("entreprise"), offer.get("titre"))
    # cross-source dedup ONLY when the company is known: otherwise two distinct
    # offers with no parsed employer + a generic title would share the same key
    # and one would be silently lost.
    if offer.get("entreprise") and dup_exists(conn, key, offer.get("profil")):
        return False  # already proposed via another source
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
    """Next offer to propose, highest score first."""
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
    """Kept or applied offers, for the Google Sheet / CSV mirror."""
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
        "url": "https://example.test/offer/1",
        "source": "test",
        "profil": "alternance",
        "entreprise": "ACME",
        "titre": "M&A Analyst",
        "contrat": "apprenticeship",
        "lieu": "Paris",
        "score": 8.5,
    })
    print("inserted:", ok)
    print("pending:", count_pending(c, "alternance"))
    row = next_pending(c, "alternance")
    print("next:", dict(row) if row else None)
