import json
import mimetypes
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings
from app.db.database import get_connection
from app.models.video import (
    ChatHistoryResponse,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    VideoCreateRequest,
    VideoResponse,
    VideoUpdateRequest,
)
from app.services.audio_extractor import extract_audio
from app.services.chat_service import answer_from_transcript
from app.services.web_search import search_web
from app.services.library_storage import (
    delete_library_folder,
    save_to_library,
    update_metadata_file,
    update_transcript_file,
)
from app.services.transcriber import detect_content_type, transcribe_audio
from app.services.video_downloader import download_video

router = APIRouter(prefix="/videos", tags=["videos"])


def _video_has_file(row) -> bool:
    path = row["local_video_path"]
    return bool(path and Path(path).exists())


def _row_to_video_response(row, transcript_row=None) -> VideoResponse:
    transcript = None
    if transcript_row:
        segments = None
        if transcript_row["segments_json"]:
            segments = json.loads(transcript_row["segments_json"])
        transcript = {
            "language": transcript_row["language"],
            "full_text": transcript_row["full_text"],
            "segments": segments,
        }

    video_url = f"/api/videos/{row['id']}/stream" if _video_has_file(row) else None

    return VideoResponse(
        id=row["id"],
        source_url=row["source_url"],
        platform=row["platform"],
        title=row["title"],
        description=row["description"],
        uploader=row["uploader"],
        duration_seconds=row["duration_seconds"],
        thumbnail_url=row["thumbnail_url"],
        storage_stamp=row["storage_stamp"],
        storage_folder=row["storage_folder"],
        status=row["status"],
        content_type=row["content_type"] if row["content_type"] else "unknown",
        error_message=row["error_message"],
        video_url=video_url,
        transcript=transcript,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _validate_instagram_url(url: str) -> None:
    if "instagram.com" not in url.lower():
        raise HTTPException(status_code=400, detail="URL must be an Instagram link")


def _mark_video_failed(video_id: int, error_message: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE videos SET status = ?, error_message = ? WHERE id = ?",
            ("failed", error_message, video_id),
        )


def process_video(video_id: int) -> None:
    """Download video, extract audio, transcribe, and persist to the library."""
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT source_url FROM videos WHERE id = ?",
                (video_id,),
            ).fetchone()
            if not row:
                return
            source_url = row["source_url"]
            conn.execute(
                "UPDATE videos SET status = ? WHERE id = ?",
                ("processing", video_id),
            )

        download_result = download_video(
            source_url,
            settings.download_path,
            video_id,
        )

        video_path = Path(download_result["local_video_path"])
        audio_path = extract_audio(video_path, settings.audio_path)
        transcript_result = transcribe_audio(audio_path)

        content_type = detect_content_type(
            transcript_result["full_text"],
            download_result.get("duration_seconds"),
        )

        library_result = save_to_library(
            settings.library_path,
            title=download_result["title"] or f"video-{video_id}",
            source_url=source_url,
            video_path=video_path,
            audio_path=audio_path,
            transcript=transcript_result,
            metadata={
                "uploader": download_result["uploader"],
                "duration_seconds": download_result["duration_seconds"],
                "thumbnail_url": download_result["thumbnail_url"],
                "description": download_result["description"],
                "video_id": video_id,
            },
        )

        with get_connection() as conn:
            conn.execute(
                """
                UPDATE videos
                SET platform = ?, title = ?, description = ?, uploader = ?,
                    duration_seconds = ?, thumbnail_url = ?,
                    local_video_path = ?, local_audio_path = ?,
                    storage_stamp = ?, storage_folder = ?, local_transcript_path = ?,
                    content_type = ?
                WHERE id = ?
                """,
                (
                    "instagram",
                    download_result["title"],
                    download_result["description"],
                    download_result["uploader"],
                    download_result["duration_seconds"],
                    download_result["thumbnail_url"],
                    library_result["local_video_path"],
                    library_result["local_audio_path"],
                    library_result["storage_stamp"],
                    library_result["storage_folder"],
                    library_result["local_transcript_path"],
                    content_type,
                    video_id,
                ),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO transcripts (video_id, language, full_text, segments_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    video_id,
                    transcript_result["language"],
                    transcript_result["full_text"],
                    json.dumps(transcript_result["segments"]),
                ),
            )
            conn.execute(
                "UPDATE videos SET status = ?, error_message = NULL WHERE id = ?",
                ("ready", video_id),
            )
    except Exception as exc:
        _mark_video_failed(video_id, str(exc))


@router.post("", response_model=VideoResponse, status_code=201)
def create_video(payload: VideoCreateRequest, background_tasks: BackgroundTasks) -> VideoResponse:
    url = str(payload.url)
    _validate_instagram_url(url)

    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO videos (source_url, status) VALUES (?, ?)",
            (url, "processing"),
        )
        video_id = cursor.lastrowid

    background_tasks.add_task(process_video, video_id)
    return get_video(video_id)


@router.get("", response_model=list[VideoResponse])
def list_videos() -> list[VideoResponse]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM videos ORDER BY created_at DESC LIMIT 100").fetchall()
        return [_row_to_video_response(row) for row in rows]


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(video_id: int) -> VideoResponse:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")
        transcript_row = conn.execute(
            "SELECT * FROM transcripts WHERE video_id = ?",
            (video_id,),
        ).fetchone()
        return _row_to_video_response(row, transcript_row)


@router.patch("/{video_id}", response_model=VideoResponse)
def update_video(video_id: int, payload: VideoUpdateRequest) -> VideoResponse:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")

        updates = {}
        metadata_updates = {}
        if payload.title is not None:
            updates["title"] = payload.title
            metadata_updates["title"] = payload.title
        if payload.description is not None:
            updates["description"] = payload.description
            metadata_updates["description"] = payload.description

        if updates:
            assignments = ", ".join(f"{key} = ?" for key in updates)
            conn.execute(
                f"UPDATE videos SET {assignments} WHERE id = ?",
                (*updates.values(), video_id),
            )

        if row["storage_folder"] and metadata_updates:
            folder = settings.library_path / row["storage_folder"]
            update_metadata_file(folder, metadata_updates)

        if payload.transcript_text is not None:
            existing = conn.execute(
                "SELECT id FROM transcripts WHERE video_id = ?",
                (video_id,),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE transcripts SET full_text = ? WHERE video_id = ?",
                    (payload.transcript_text, video_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO transcripts (video_id, language, full_text, segments_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (video_id, None, payload.transcript_text, "[]"),
                )
            if row["local_transcript_path"]:
                update_transcript_file(Path(row["local_transcript_path"]), payload.transcript_text)

    return get_video(video_id)


@router.delete("/{video_id}", status_code=204)
def delete_video(video_id: int) -> None:
    with get_connection() as conn:
        row = conn.execute("SELECT storage_folder FROM videos WHERE id = ?", (video_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")
        storage_folder = row["storage_folder"]
        conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))

    delete_library_folder(settings.library_path, storage_folder)


@router.get("/{video_id}/stream")
def stream_video(video_id: int) -> FileResponse:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT local_video_path, status FROM videos WHERE id = ?",
            (video_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")
        if not row["local_video_path"]:
            raise HTTPException(status_code=404, detail="Video file not available")

        video_path = Path(row["local_video_path"])
        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Video file not found on disk")

        media_type = mimetypes.guess_type(video_path.name)[0] or "video/mp4"
        return FileResponse(video_path, media_type=media_type, filename=video_path.name)


@router.get("/{video_id}/chat", response_model=ChatHistoryResponse)
def get_chat_history(video_id: int) -> ChatHistoryResponse:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM videos WHERE id = ?", (video_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")
        rows = conn.execute(
            """
            SELECT id, role, content, created_at
            FROM chat_messages
            WHERE video_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (video_id,),
        ).fetchall()

    return ChatHistoryResponse(
        video_id=video_id,
        messages=[
            ChatMessageResponse(
                id=item["id"],
                role=item["role"],
                content=item["content"],
                created_at=item["created_at"],
            )
            for item in rows
        ],
    )


@router.post("/{video_id}/chat", response_model=ChatResponse)
def chat_with_video(video_id: int, payload: ChatRequest) -> ChatResponse:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, status FROM videos WHERE id = ?",
            (video_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")
        if row["status"] != "ready":
            raise HTTPException(
                status_code=400,
                detail="Chat is available only after transcription finishes.",
            )

        transcript_row = conn.execute(
            "SELECT full_text, segments_json FROM transcripts WHERE video_id = ?",
            (video_id,),
        ).fetchone()
        video_row = conn.execute(
            "SELECT title, uploader FROM videos WHERE id = ?",
            (video_id,),
        ).fetchone()

        segments = None
        full_text = ""
        if transcript_row:
            full_text = transcript_row["full_text"] or ""
            if transcript_row["segments_json"]:
                segments = json.loads(transcript_row["segments_json"])

        if payload.mode == "web":
            answer = search_web(
                message,
                title=video_row["title"] if video_row else None,
                uploader=video_row["uploader"] if video_row else None,
            )
        else:
            answer = answer_from_transcript(message, full_text, segments)

        conn.execute(
            "INSERT INTO chat_messages (video_id, role, content) VALUES (?, ?, ?)",
            (video_id, "user", message),
        )
        assistant_cursor = conn.execute(
            "INSERT INTO chat_messages (video_id, role, content) VALUES (?, ?, ?)",
            (video_id, "assistant", answer),
        )

        assistant_row = conn.execute(
            "SELECT id, role, content, created_at FROM chat_messages WHERE id = ?",
            (assistant_cursor.lastrowid,),
        ).fetchone()

    return ChatResponse(
        video_id=video_id,
        answer=answer,
        message=ChatMessageResponse(
            id=assistant_row["id"],
            role=assistant_row["role"],
            content=assistant_row["content"],
            created_at=assistant_row["created_at"],
        ),
    )
