"""SQLite FTS5 full-text search over saved videos, transcripts, and notes."""

from __future__ import annotations

import re
import sqlite3


FTS_TABLE_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS library_fts USING fts5(
    video_id UNINDEXED,
    title,
    description,
    uploader,
    notes,
    tags,
    transcript,
    tokenize = 'porter unicode61'
);
"""


def ensure_fts_table(conn: sqlite3.Connection) -> None:
    conn.execute(FTS_TABLE_SQL)


def _strip_html(text: str | None) -> str:
    if not text:
        return ""
    # Notes may contain rich HTML from the editor
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def _row_document(row: sqlite3.Row) -> tuple:
    tags = row["tags"] or ""
    if tags.startswith("["):
        try:
            import json

            tags = " ".join(json.loads(tags))
        except Exception:
            pass

    transcript_parts = [
        row["full_text"] or "",
        row["cleaned_text"] or "",
        row["translation_ar"] or "",
        row["cleaned_translation_ar"] or "",
        row["professional_review"] or "",
    ]
    transcript = "\n".join(part for part in transcript_parts if part)

    return (
        row["id"],
        row["title"] or "",
        row["description"] or "",
        row["uploader"] or "",
        _strip_html(row["notes"]),
        tags,
        transcript,
    )


def upsert_video_fts(conn: sqlite3.Connection, video_id: int) -> None:
    """Insert or replace one video document in the FTS index."""
    ensure_fts_table(conn)
    row = conn.execute(
        """
        SELECT v.id, v.title, v.description, v.uploader, v.notes, v.tags, v.deleted_at,
               t.full_text, t.cleaned_text, t.translation_ar, t.cleaned_translation_ar,
               t.professional_review
        FROM videos v
        LEFT JOIN transcripts t ON t.video_id = v.id
        WHERE v.id = ?
        """,
        (video_id,),
    ).fetchone()

    conn.execute("DELETE FROM library_fts WHERE video_id = ?", (video_id,))
    if not row or row["deleted_at"]:
        return

    conn.execute(
        """
        INSERT INTO library_fts
            (video_id, title, description, uploader, notes, tags, transcript)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        _row_document(row),
    )


def remove_video_fts(conn: sqlite3.Connection, video_id: int) -> None:
    ensure_fts_table(conn)
    conn.execute("DELETE FROM library_fts WHERE video_id = ?", (video_id,))


def rebuild_library_fts(conn: sqlite3.Connection) -> int:
    """Rebuild the full FTS index. Returns number of indexed videos."""
    ensure_fts_table(conn)
    conn.execute("DELETE FROM library_fts")
    rows = conn.execute(
        """
        SELECT v.id, v.title, v.description, v.uploader, v.notes, v.tags, v.deleted_at,
               t.full_text, t.cleaned_text, t.translation_ar, t.cleaned_translation_ar,
               t.professional_review
        FROM videos v
        LEFT JOIN transcripts t ON t.video_id = v.id
        WHERE v.deleted_at IS NULL
        """
    ).fetchall()
    for row in rows:
        conn.execute(
            """
            INSERT INTO library_fts
                (video_id, title, description, uploader, notes, tags, transcript)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            _row_document(row),
        )
    return len(rows)


def build_fts_match_query(raw: str) -> str | None:
    """Turn free text into a safe FTS5 MATCH query (prefix terms)."""
    terms = re.findall(r"[\w\u0600-\u06FF]+", raw or "", flags=re.UNICODE)
    if not terms:
        return None
    # Cap terms to keep queries cheap
    pieces = []
    for term in terms[:12]:
        if len(term) >= 2:
            pieces.append(f'"{term}"*')
        else:
            pieces.append(f'"{term}"')
    return " ".join(pieces)


def search_library(conn: sqlite3.Connection, query: str, limit: int = 50) -> list[dict]:
    """
    Search library FTS index.

    Returns list of {video_id, snippet, rank} ordered by relevance.
    Falls back to LIKE scan if FTS MATCH fails.
    """
    ensure_fts_table(conn)
    match = build_fts_match_query(query)
    if not match:
        return []

    try:
        rows = conn.execute(
            """
            SELECT video_id,
                   rank,
                   snippet(library_fts, 6, '«', '»', '…', 14) AS snippet
            FROM library_fts
            WHERE library_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (match, limit),
        ).fetchall()
        return [
            {
                "video_id": int(row["video_id"]),
                "snippet": (row["snippet"] or "").strip(),
                "rank": float(row["rank"]) if row["rank"] is not None else 0.0,
            }
            for row in rows
        ]
    except sqlite3.OperationalError:
        # Fallback for odd queries / empty index
        like = f"%{query.strip()}%"
        rows = conn.execute(
            """
            SELECT v.id AS video_id,
                   COALESCE(substr(t.full_text, 1, 120), v.description, v.title, '') AS snippet
            FROM videos v
            LEFT JOIN transcripts t ON t.video_id = v.id
            WHERE v.deleted_at IS NULL
              AND (
                v.title LIKE ? OR v.description LIKE ? OR v.uploader LIKE ?
                OR v.notes LIKE ? OR v.tags LIKE ?
                OR t.full_text LIKE ? OR t.cleaned_text LIKE ?
                OR t.translation_ar LIKE ?
              )
            ORDER BY v.created_at DESC
            LIMIT ?
            """,
            (like, like, like, like, like, like, like, like, limit),
        ).fetchall()
        return [
            {
                "video_id": int(row["video_id"]),
                "snippet": (row["snippet"] or "").strip(),
                "rank": 0.0,
            }
            for row in rows
        ]
