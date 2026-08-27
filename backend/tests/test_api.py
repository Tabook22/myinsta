import json
import zipfile
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
    wiki_dir = tmp_path / "mywiki"

    monkeypatch.setattr("app.core.config.settings.database_path", str(db_path))
    monkeypatch.setattr("app.core.config.settings.download_dir", str(download_dir))
    monkeypatch.setattr("app.core.config.settings.audio_dir", str(audio_dir))
    monkeypatch.setattr("app.core.config.settings.library_dir", str(library_dir))
    monkeypatch.setattr("app.core.config.settings.wiki_dir", str(wiki_dir))
    monkeypatch.setattr("app.core.config.settings.database_file", db_path)
    monkeypatch.setattr("app.core.config.settings.download_path", download_dir)
    monkeypatch.setattr("app.core.config.settings.audio_path", audio_dir)
    monkeypatch.setattr("app.core.config.settings.library_path", library_dir)
    monkeypatch.setattr("app.core.config.settings.wiki_path", wiki_dir)

    init_db()
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_video_rejects_unsupported_url(client):
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
    assert body["platform"] == "instagram"

    detail = client.get(f"/api/videos/{body['id']}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["status"] == "ready"
    assert detail_body["platform"] == "instagram"
    assert detail_body["transcript"]["full_text"] == "Hello world"
    assert detail_body["video_url"] == f"/api/videos/{body['id']}/stream"


def test_create_video_accepts_youtube_url(client, monkeypatch):
    def fake_process(video_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE videos SET status = ?, title = ? WHERE id = ?",
                ("ready", "YouTube test", video_id),
            )

    monkeypatch.setattr(videos_routes, "process_video", fake_process)

    response = client.post(
        "/api/videos",
        json={"url": "https://www.youtube.com/watch?v=abc123"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["platform"] == "youtube"

    detail = client.get(f"/api/videos/{body['id']}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["status"] == "ready"
    assert detail_body["platform"] == "youtube"


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


def test_full_backup_download_includes_database_library_and_manifest(client, tmp_path):
    from app.core.config import settings

    folder = settings.library_path / "2026" / "05" / "20260529_120000_backup-test"
    folder.mkdir(parents=True)
    video_file = folder / "video.mp4"
    video_file.write_bytes(b"fake-video")
    audio_file = folder / "audio.wav"
    audio_file.write_bytes(b"fake-audio")
    transcript_file = folder / "transcript.txt"
    transcript_file.write_text("Backup transcript", encoding="utf-8")

    settings.wiki_path.mkdir(parents=True, exist_ok=True)
    wiki_file = settings.wiki_path / "backup-test.md"
    wiki_file.write_text("# Backup test", encoding="utf-8")

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO videos (
                source_url, status, title, local_video_path, local_audio_path,
                storage_stamp, storage_folder, local_transcript_path, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                "https://www.youtube.com/watch?v=BACKUP",
                "ready",
                "Backup test",
                str(video_file),
                str(audio_file),
                folder.name,
                "2026/05/20260529_120000_backup-test",
                str(transcript_file),
            ),
        )
        video_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO transcripts (video_id, language, full_text, segments_json)
            VALUES (?, ?, ?, ?)
            """,
            (video_id, "en", "Backup transcript", "[]"),
        )
        conn.execute(
            "INSERT INTO chat_messages (video_id, role, content) VALUES (?, ?, ?)",
            (video_id, "user", "Save this?"),
        )
        conn.execute(
            """
            INSERT INTO wiki_documents (video_id, title, filename, file_path)
            VALUES (?, ?, ?, ?)
            """,
            (video_id, "Backup test", wiki_file.name, str(wiki_file)),
        )

    response = client.get("/api/videos/backup")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "myinsta-backup-" in response.headers["content-disposition"]

    archive_path = tmp_path / "backup.zip"
    archive_path.write_bytes(response.content)
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        assert "database/myinsta.sqlite3" in names
        assert "manifest.json" in names
        assert "data/videos.json" in names
        assert "data/transcripts.json" in names
        assert "data/chat_messages.json" in names
        assert "data/wiki_documents.json" in names
        assert "library/2026/05/20260529_120000_backup-test/video.mp4" in names
        assert "library/2026/05/20260529_120000_backup-test/audio.wav" in names
        assert "library/2026/05/20260529_120000_backup-test/transcript.txt" in names
        assert "mywiki/backup-test.md" in names
        assert not any("cookies" in name.lower() or name.endswith(".env") for name in names)

        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        assert manifest["database_included"] is True
        assert manifest["counts"]["videos"] == 1
        assert manifest["counts"]["transcripts"] == 1
        assert manifest["counts"]["chat_messages"] == 1
        assert manifest["counts"]["wiki_documents"] == 1


def test_backup_job_reports_progress_and_downloads(client, tmp_path):
    from app.core.config import settings

    folder = settings.library_path / "2026" / "08" / "20260828_130000_progress-test"
    folder.mkdir(parents=True)
    (folder / "video.mp4").write_bytes(b"video")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO videos (
                source_url, platform, status, title, local_video_path,
                storage_folder, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "https://www.instagram.com/reel/PROGRESS/",
                "instagram",
                "ready",
                "Progress test",
                str(folder / "video.mp4"),
                "2026/08/20260828_130000_progress-test",
                "2026-08-28 13:00:00",
                "2026-08-28 13:00:00",
            ),
        )

    started = client.post("/api/videos/backup/start")
    assert started.status_code == 200
    job_id = started.json()["job_id"]

    status = client.get(f"/api/videos/backup/jobs/{job_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "ready"
    assert body["percent"] == 100
    assert body["download_url"] == f"/api/videos/backup/jobs/{job_id}/download"

    download = client.get(body["download_url"])
    assert download.status_code == 200
    archive_path = tmp_path / "job-backup.zip"
    archive_path.write_bytes(download.content)
    with zipfile.ZipFile(archive_path) as archive:
        assert "manifest.json" in archive.namelist()

    missing_after_download = client.get(f"/api/videos/backup/jobs/{job_id}")
    assert missing_after_download.status_code == 404


def test_import_backup_merges_videos_files_and_messages(client, tmp_path):
    from app.core.config import settings

    backup_path = tmp_path / "myinsta-backup.zip"
    source_url = "https://www.youtube.com/watch?v=IMPORT"
    storage_folder = "2026/08/20260828_120000_import-test"
    remote_video_path = f"/opt/myinsta/backend/data/library/{storage_folder}/video.mp4"
    remote_audio_path = f"/opt/myinsta/backend/data/library/{storage_folder}/audio.wav"
    remote_transcript_path = f"/opt/myinsta/backend/data/library/{storage_folder}/transcript.txt"
    remote_wiki_path = "/opt/myinsta/backend/data/mywiki/import-test.md"

    with zipfile.ZipFile(backup_path, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"app": "MyInsta", "backup_version": 1}))
        archive.writestr(f"library/{storage_folder}/video.mp4", b"video")
        archive.writestr(f"library/{storage_folder}/audio.wav", b"audio")
        archive.writestr(f"library/{storage_folder}/transcript.txt", "Imported transcript")
        archive.writestr("mywiki/import-test.md", "# Imported wiki")
        archive.writestr(
            "data/videos.json",
            json.dumps([
                {
                    "id": 42,
                    "source_url": source_url,
                    "platform": "youtube",
                    "title": "Imported video",
                    "description": "Imported description",
                    "uploader": "creator",
                    "duration_seconds": 12,
                    "thumbnail_url": None,
                    "local_video_path": remote_video_path,
                    "local_audio_path": remote_audio_path,
                    "storage_stamp": "20260828_120000_import-test",
                    "storage_folder": storage_folder,
                    "local_transcript_path": remote_transcript_path,
                    "status": "ready",
                    "error_message": None,
                    "content_type": "speech",
                    "creator_url": None,
                    "notes": "Imported notes",
                    "tags": json.dumps(["sync"]),
                    "deleted_at": None,
                    "processing_step": None,
                    "created_at": "2026-08-28 12:00:00",
                    "updated_at": "2026-08-28 12:00:00",
                }
            ]),
        )
        archive.writestr(
            "data/transcripts.json",
            json.dumps([
                {
                    "id": 7,
                    "video_id": 42,
                    "language": "en",
                    "full_text": "Imported transcript",
                    "segments_json": "[]",
                    "created_at": "2026-08-28 12:00:00",
                    "updated_at": "2026-08-28 12:00:00",
                }
            ]),
        )
        archive.writestr(
            "data/chat_messages.json",
            json.dumps([
                {
                    "id": 9,
                    "video_id": 42,
                    "role": "user",
                    "content": "What is this?",
                    "created_at": "2026-08-28 12:01:00",
                }
            ]),
        )
        archive.writestr(
            "data/wiki_documents.json",
            json.dumps([
                {
                    "id": 3,
                    "video_id": 42,
                    "title": "Imported video",
                    "filename": "import-test.md",
                    "file_path": remote_wiki_path,
                    "created_at": "2026-08-28 12:02:00",
                    "updated_at": "2026-08-28 12:02:00",
                }
            ]),
        )

    response = client.post(
        "/api/videos/backup/import",
        files={"file": ("myinsta-backup.zip", backup_path.read_bytes(), "application/zip")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["videos_created"] == 1
    assert body["videos_updated"] == 0
    assert body["transcripts_imported"] == 1
    assert body["chat_messages_imported"] == 1
    assert body["wiki_documents_imported"] == 1
    assert body["files_imported"] == 4

    local_video_file = settings.library_path / storage_folder / "video.mp4"
    assert local_video_file.read_bytes() == b"video"
    assert (settings.wiki_path / "import-test.md").read_text(encoding="utf-8") == "# Imported wiki"

    with get_connection() as conn:
        row = conn.execute("SELECT * FROM videos WHERE source_url = ?", (source_url,)).fetchone()
        assert row is not None
        assert row["local_video_path"] == str(local_video_file.resolve())
        video_id = row["id"]
        transcript = conn.execute(
            "SELECT full_text FROM transcripts WHERE video_id = ?",
            (video_id,),
        ).fetchone()
        assert transcript["full_text"] == "Imported transcript"
        messages = conn.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE video_id = ?",
            (video_id,),
        ).fetchone()[0]
        assert messages == 1

    second_response = client.post(
        "/api/videos/backup/import",
        files={"file": ("myinsta-backup.zip", backup_path.read_bytes(), "application/zip")},
    )
    assert second_response.status_code == 200
    assert second_response.json()["videos_created"] == 0
    with get_connection() as conn:
        messages = conn.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0]
        assert messages == 1


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


def test_translate_description_to_arabic(client, monkeypatch):
    calls = []

    def fake_translate(text: str, source_language: str | None = None) -> str:
        calls.append((text, source_language))
        return "AR description"

    monkeypatch.setattr(videos_routes, "translate_to_arabic", fake_translate)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO videos (source_url, status, title, description)
            VALUES (?, ?, ?, ?)
            """,
            (
                "https://www.instagram.com/reel/DESCRIPTION/",
                "ready",
                "Description test",
                "A short English description",
            ),
        )
        video_id = cursor.lastrowid

    response = client.post(f"/api/videos/{video_id}/translate-description")
    assert response.status_code == 200
    assert response.json() == {
        "video_id": video_id,
        "target_language": "ar",
        "translated_text": "AR description",
    }
    assert calls == [("A short English description", None)]

    cached_response = client.post(f"/api/videos/{video_id}/translate-description")
    assert cached_response.status_code == 200
    assert len(calls) == 1

    detail = client.get(f"/api/videos/{video_id}")
    assert detail.status_code == 200
    assert detail.json()["description_translation_ar"] == "AR description"


def test_clean_transcript_to_english_and_arabic(client, monkeypatch):
    calls = []

    def fake_translate(text: str, source_language: str | None = None) -> str:
        calls.append((text, source_language))
        return "AR cleaned transcript"

    monkeypatch.setattr(videos_routes, "translate_to_arabic", fake_translate)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO videos (source_url, status, title)
            VALUES (?, ?, ?)
            """,
            ("https://www.instagram.com/reel/CLEAN/", "ready", "Cleanup test"),
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
                "hello hello this is useful useful then we explain cleanup",
                "[]",
            ),
        )

    english_response = client.post(f"/api/videos/{video_id}/cleanup?target_language=en")
    assert english_response.status_code == 200
    english_body = english_response.json()
    assert english_body["target_language"] == "en"
    assert "hello hello" not in english_body["cleaned_text"].lower()
    assert english_body["cleaned_text"].endswith(".")

    arabic_response = client.post(f"/api/videos/{video_id}/cleanup?target_language=ar")
    assert arabic_response.status_code == 200
    assert arabic_response.json() == {
        "video_id": video_id,
        "target_language": "ar",
        "cleaned_text": "AR cleaned transcript",
    }
    assert calls == [(english_body["cleaned_text"], "en")]

    cached_response = client.post(f"/api/videos/{video_id}/cleanup?target_language=ar")
    assert cached_response.status_code == 200
    assert len(calls) == 1

    detail = client.get(f"/api/videos/{video_id}")
    assert detail.status_code == 200
    transcript = detail.json()["transcript"]
    assert transcript["cleaned_text"] == english_body["cleaned_text"]
    assert transcript["cleaned_translation_ar"] == "AR cleaned transcript"


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


def test_chat_answer_language_modes(client, monkeypatch):
    calls = []

    def fake_translate(text: str, source_language: str | None = None) -> str:
        calls.append((text, source_language))
        return "إجابة عربية"

    monkeypatch.setattr(videos_routes, "translate_to_arabic", fake_translate)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO videos (source_url, status, title)
            VALUES (?, ?, ?)
            """,
            ("https://www.instagram.com/reel/CHATLANG/", "ready", "Chat language test"),
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

    arabic_response = client.post(
        f"/api/videos/{video_id}/chat",
        json={
            "message": "What is this video about?",
            "answer_language": "arabic",
        },
    )
    assert arabic_response.status_code == 200
    assert arabic_response.json()["answer"] == "إجابة عربية"

    bilingual_response = client.post(
        f"/api/videos/{video_id}/chat",
        json={
            "message": "What is this video about?",
            "answer_language": "bilingual",
        },
    )
    assert bilingual_response.status_code == 200
    bilingual_answer = bilingual_response.json()["answer"]
    assert bilingual_answer.startswith("English:\n")
    assert "\n\nArabic:\nإجابة عربية" in bilingual_answer
    assert len(calls) == 2


def test_retry_failed_video(client, monkeypatch):
    called = []

    def fake_process(video_id: int) -> None:
        called.append(video_id)
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE videos
                SET status = ?, error_message = NULL, processing_step = NULL, title = ?
                WHERE id = ?
                """,
                ("ready", "Retried video", video_id),
            )

    monkeypatch.setattr(videos_routes, "process_video", fake_process)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO videos (source_url, status, error_message, processing_step, title)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "https://www.instagram.com/reel/RETRY/",
                "failed",
                "Download failed: temporary error",
                "downloading",
                "Broken video",
            ),
        )
        video_id = cursor.lastrowid

    response = client.post(f"/api/videos/{video_id}/retry")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"processing", "ready"}
    assert called == [video_id]

    detail = client.get(f"/api/videos/{video_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "ready"
    assert detail.json()["title"] == "Retried video"
    assert detail.json()["error_message"] is None


def test_retry_rejects_ready_video(client):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO videos (source_url, status, title)
            VALUES (?, ?, ?)
            """,
            ("https://www.instagram.com/reel/READY-RETRY/", "ready", "Already ready"),
        )
        video_id = cursor.lastrowid

    response = client.post(f"/api/videos/{video_id}/retry")
    assert response.status_code == 400
    assert "failed" in response.json()["detail"].lower()
