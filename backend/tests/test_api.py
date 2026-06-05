import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.database import get_connection, init_db
from app.main import app
from app.routes import videos as videos_routes


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite3"
    download_dir = tmp_path / "downloads"
    audio_dir = tmp_path / "audio"
    library_dir = tmp_path / "library"

    monkeypatch.setattr("app.core.config.settings.database_path", str(db_path))
    monkeypatch.setattr("app.core.config.settings.download_dir", str(download_dir))
    monkeypatch.setattr("app.core.config.settings.audio_dir", str(audio_dir))
    monkeypatch.setattr("app.core.config.settings.library_dir", str(library_dir))
    monkeypatch.setattr("app.core.config.settings.database_file", db_path)
    monkeypatch.setattr("app.core.config.settings.download_path", download_dir)
    monkeypatch.setattr("app.core.config.settings.audio_path", audio_dir)
    monkeypatch.setattr("app.core.config.settings.library_path", library_dir)

    init_db()
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_video_rejects_non_instagram_url(client):
    response = client.post(
        "/api/videos",
        json={"url": "https://example.com/video"},
    )
    assert response.status_code == 400


def test_create_video_starts_processing(client, monkeypatch):
    from app.core.config import settings

    def fake_process(video_id: int) -> None:
        folder = settings.library_path / "2026" / "05" / f"20260529_120000_video-{video_id}"
        folder.mkdir(parents=True, exist_ok=True)
        video_file = folder / "video.mp4"
        video_file.write_bytes(b"fake-video")
        transcript_file = folder / "transcript.txt"
        transcript_file.write_text("Hello world", encoding="utf-8")

        with get_connection() as conn:
            conn.execute(
                """
                UPDATE videos
                SET status = ?, title = ?, local_video_path = ?,
                    storage_stamp = ?, storage_folder = ?, local_transcript_path = ?
                WHERE id = ?
                """,
                (
                    "ready",
                    "Test video",
                    str(video_file),
                    folder.name,
                    str(folder.relative_to(settings.library_path)).replace("\\", "/"),
                    str(transcript_file),
                    video_id,
                ),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO transcripts (video_id, language, full_text, segments_json)
                VALUES (?, ?, ?, ?)
                """,
                (video_id, "en", "Hello world", "[]"),
            )

    monkeypatch.setattr(videos_routes, "process_video", fake_process)

    response = client.post(
        "/api/videos",
        json={"url": "https://www.instagram.com/reel/ABC123/"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "processing"

    detail = client.get(f"/api/videos/{body['id']}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["status"] == "ready"
    assert detail_body["transcript"]["full_text"] == "Hello world"
    assert detail_body["video_url"] == f"/api/videos/{body['id']}/stream"


def test_list_videos_returns_recent_items(client, monkeypatch):
    def fake_process(video_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE videos SET status = ?, title = ? WHERE id = ?",
                ("ready", f"Video {video_id}", video_id),
            )

    monkeypatch.setattr(videos_routes, "process_video", fake_process)

    client.post("/api/videos", json={"url": "https://www.instagram.com/reel/ONE/"})
    client.post("/api/videos", json={"url": "https://www.instagram.com/reel/TWO/"})

    response = client.get("/api/videos")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    titles = {item["title"] for item in items}
    assert titles == {"Video 1", "Video 2"}


def test_update_and_delete_video(client, monkeypatch, tmp_path):
    library_dir = tmp_path / "library"
    folder = library_dir / "2026" / "05" / "20260529_120000_test-video"
    folder.mkdir(parents=True)
    video_file = folder / "video.mp4"
    video_file.write_bytes(b"fake-video")
    transcript_file = folder / "transcript.txt"
    transcript_file.write_text("Original", encoding="utf-8")

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO videos (
                source_url, status, title, local_video_path,
                storage_stamp, storage_folder, local_transcript_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "https://www.instagram.com/reel/TEST/",
                "ready",
                "Original title",
                str(video_file),
                folder.name,
                "2026/05/20260529_120000_test-video",
                str(transcript_file),
            ),
        )
        video_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO transcripts (video_id, language, full_text, segments_json)
            VALUES (?, ?, ?, ?)
            """,
            (video_id, "en", "Original", "[]"),
        )

    patch_response = client.patch(
        f"/api/videos/{video_id}",
        json={"title": "Updated title", "transcript_text": "Updated transcript"},
    )
    assert patch_response.status_code == 200
    body = patch_response.json()
    assert body["title"] == "Updated title"
    assert body["transcript"]["full_text"] == "Updated transcript"
    assert transcript_file.read_text(encoding="utf-8") == "Updated transcript"

    stream_response = client.get(f"/api/videos/{video_id}/stream")
    assert stream_response.status_code == 200

    delete_response = client.delete(f"/api/videos/{video_id}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/videos/{video_id}").status_code == 404
    assert folder.exists()


def test_translate_transcript_to_arabic(client, monkeypatch):
    calls = []

    def fake_translate(text: str, source_language: str | None = None) -> str:
        calls.append((text, source_language))
        return "مرحبا بالعالم"

    monkeypatch.setattr(videos_routes, "translate_to_arabic", fake_translate)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO videos (source_url, status, title)
            VALUES (?, ?, ?)
            """,
            ("https://www.instagram.com/reel/TRANSLATE/", "ready", "Translate test"),
        )
        video_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO transcripts (video_id, language, full_text, segments_json)
            VALUES (?, ?, ?, ?)
            """,
            (video_id, "en", "Hello world", "[]"),
        )

    response = client.post(f"/api/videos/{video_id}/translate")
    assert response.status_code == 200
    assert response.json() == {
        "video_id": video_id,
        "target_language": "ar",
        "translated_text": "مرحبا بالعالم",
    }
    assert calls == [("Hello world", "en")]

    cached_response = client.post(f"/api/videos/{video_id}/translate")
    assert cached_response.status_code == 200
    assert len(calls) == 1

    detail = client.get(f"/api/videos/{video_id}")
    assert detail.status_code == 200
    assert detail.json()["transcript"]["translation_ar"] == "مرحبا بالعالم"


def test_chat_uses_transcript(client):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO videos (source_url, status, title)
            VALUES (?, ?, ?)
            """,
            ("https://www.instagram.com/reel/CHAT/", "ready", "Chat test"),
        )
        video_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO transcripts (video_id, language, full_text, segments_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                video_id,
                "en",
                "This reel explains how to batch cook healthy meals for the week.",
                "[]",
            ),
        )

    history = client.get(f"/api/videos/{video_id}/chat")
    assert history.status_code == 200
    assert history.json()["messages"] == []

    response = client.post(
        f"/api/videos/{video_id}/chat",
        json={"message": "What is this video about?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "batch cook" in body["answer"].lower()

    history = client.get(f"/api/videos/{video_id}/chat")
    assert len(history.json()["messages"]) == 2
