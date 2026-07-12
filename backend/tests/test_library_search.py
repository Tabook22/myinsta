import pytest
from fastapi.testclient import TestClient

from app.db.database import get_connection, init_db
from app.main import app
from app.services.library_search import rebuild_library_fts, search_library


@pytest.fixture()
def fts_env(tmp_path, monkeypatch):
    db_path = tmp_path / "fts.sqlite3"
    download_dir = tmp_path / "dl"
    audio_dir = tmp_path / "audio"
    library_dir = tmp_path / "lib"
    wiki_dir = tmp_path / "wiki"

    monkeypatch.setattr("app.core.config.settings.database_path", str(db_path))
    monkeypatch.setattr("app.core.config.settings.database_file", db_path)
    monkeypatch.setattr("app.core.config.settings.download_dir", str(download_dir))
    monkeypatch.setattr("app.core.config.settings.audio_dir", str(audio_dir))
    monkeypatch.setattr("app.core.config.settings.library_dir", str(library_dir))
    monkeypatch.setattr("app.core.config.settings.wiki_dir", str(wiki_dir))
    monkeypatch.setattr("app.core.config.settings.download_path", download_dir)
    monkeypatch.setattr("app.core.config.settings.audio_path", audio_dir)
    monkeypatch.setattr("app.core.config.settings.library_path", library_dir)
    monkeypatch.setattr("app.core.config.settings.wiki_path", wiki_dir)

    init_db()
    return TestClient(app)


def test_library_fts_finds_transcript_terms(fts_env):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO videos (source_url, status, title, uploader, notes) VALUES (?, ?, ?, ?, ?)",
            (
                "https://www.instagram.com/reel/FTS1/",
                "ready",
                "Cooking short",
                "chef_ali",
                "personal notes about meal prep",
            ),
        )
        video_id = cur.lastrowid
        conn.execute(
            "INSERT INTO transcripts (video_id, language, full_text, segments_json) VALUES (?, ?, ?, ?)",
            (video_id, "en", "We discuss spaced repetition and memory techniques.", "[]"),
        )
        rebuild_library_fts(conn)

        hits = search_library(conn, "spaced repetition")
        assert any(hit["video_id"] == video_id for hit in hits)

        note_hits = search_library(conn, "meal prep")
        assert any(hit["video_id"] == video_id for hit in note_hits)


def test_library_search_api(fts_env):
    client = fts_env
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO videos (source_url, status, title) VALUES (?, ?, ?)",
            ("https://www.instagram.com/reel/APISEARCH/", "ready", "Deep work habits"),
        )
        video_id = cur.lastrowid
        conn.execute(
            "INSERT INTO transcripts (video_id, language, full_text, segments_json) VALUES (?, ?, ?, ?)",
            (video_id, "en", "Focus blocks and deep work rituals for makers.", "[]"),
        )
        rebuild_library_fts(conn)

    response = client.get("/api/search/library", params={"q": "deep work"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert any(item["video_id"] == video_id for item in body["results"])
