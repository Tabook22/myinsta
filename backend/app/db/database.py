import sqlite3
from pathlib import Path

from app.core.config import settings

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

MIGRATIONS = [
    "ALTER TABLE videos ADD COLUMN storage_stamp TEXT",
    "ALTER TABLE videos ADD COLUMN storage_folder TEXT",
    "ALTER TABLE videos ADD COLUMN local_transcript_path TEXT",
    "ALTER TABLE videos ADD COLUMN content_type TEXT NOT NULL DEFAULT 'unknown'",
    "ALTER TABLE videos ADD COLUMN creator_url TEXT",
]


def get_connection() -> sqlite3.Connection:
    settings.database_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.database_file)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _run_migrations(conn: sqlite3.Connection) -> None:
    for statement in MIGRATIONS:
        try:
            conn.execute(statement)
        except sqlite3.OperationalError:
            pass


def init_db() -> None:
    settings.download_path.mkdir(parents=True, exist_ok=True)
    settings.audio_path.mkdir(parents=True, exist_ok=True)
    settings.library_path.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        _run_migrations(conn)
