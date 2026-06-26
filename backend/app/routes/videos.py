import csv
import io
import json
import mimetypes
import re
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, HTTPException, Response
from fastapi.responses import FileResponse

from app.core.config import settings
from app.db.database import get_connection
from app.models.video import (
    ChatHistoryResponse,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    DescriptionTranslationResponse,
    NotionExportRequest,
    TranscriptCleanupResponse,
    TranscriptReviewResponse,
    TranscriptTranslationResponse,
    VideoCreateRequest,
    VideoResponse,
    VideoUpdateRequest,
)
from app.services.audio_extractor import extract_audio, extract_audio_mp3
from app.services.video_compressor import compress_video
from app.services.chat_service import answer_from_transcript
from app.services.transcript_cleanup import clean_transcript_text
from app.services.transcript_review import build_professional_review
from app.services.web_search import search_web
from app.services.library_storage import (
    delete_library_folder,
    save_to_library,
    update_metadata_file,
    update_transcript_file,
)
from app.services.transcriber import detect_content_type, transcribe_audio
from app.services.translator import translate_to_arabic
from app.services.video_downloader import download_video

router = APIRouter(prefix="/videos", tags=["videos"])


def _video_has_file(row) -> bool:
    path = row["local_video_path"]
    return bool(path and Path(path).exists())


def _audio_has_file(row) -> bool:
    """Check if a playable audio file exists (MP3 preferred, WAV fallback)."""
    wav_path = row["local_audio_path"]
    if not wav_path:
        return False
    mp3_path = Path(wav_path).with_suffix(".mp3")
    return mp3_path.exists() or Path(wav_path).exists()


def _row_to_video_response(row, transcript_row=None) -> VideoResponse:
    transcript = None
    if transcript_row:
        segments = None
        if transcript_row["segments_json"]:
            segments = json.loads(transcript_row["segments_json"])
        transcript = {
            "language": transcript_row["language"],
            "full_text": transcript_row["full_text"],
            "translation_ar": transcript_row["translation_ar"] if "translation_ar" in transcript_row.keys() else None,
            "cleaned_text": transcript_row["cleaned_text"] if "cleaned_text" in transcript_row.keys() else None,
            "cleaned_translation_ar": transcript_row["cleaned_translation_ar"] if "cleaned_translation_ar" in transcript_row.keys() else None,
            "professional_review": transcript_row["professional_review"] if "professional_review" in transcript_row.keys() else None,
            "segments": segments,
        }

    video_url = f"/api/videos/{row['id']}/stream" if _video_has_file(row) else None
    audio_url = f"/api/videos/{row['id']}/audio" if _audio_has_file(row) else None

    return VideoResponse(
        id=row["id"],
        source_url=row["source_url"],
        platform=row["platform"],
        title=row["title"],
        description=row["description"],
        description_translation_ar=row["description_translation_ar"] if "description_translation_ar" in row.keys() else None,
        uploader=row["uploader"],
        duration_seconds=row["duration_seconds"],
        thumbnail_url=row["thumbnail_url"],
        storage_stamp=row["storage_stamp"],
        storage_folder=row["storage_folder"],
        status=row["status"],
        content_type=row["content_type"] if row["content_type"] else "unknown",
        creator_url=row["creator_url"],
        error_message=row["error_message"],
        video_url=video_url,
        audio_url=audio_url,
        notes=row["notes"] if "notes" in row.keys() else None,
        tags=json.loads(row["tags"]) if row["tags"] else [],
        deleted_at=row["deleted_at"] if "deleted_at" in row.keys() else None,
        processing_step=row["processing_step"] if "processing_step" in row.keys() else None,
        transcript=transcript,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _detect_supported_platform(url: str) -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if host == "instagram.com" or host.endswith(".instagram.com"):
        return "instagram"
    if host in {"youtube.com", "youtu.be"} or host.endswith(".youtube.com"):
        return "youtube"
    raise HTTPException(
        status_code=400,
        detail="URL must be an Instagram or YouTube link.",
    )


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
                "SELECT source_url, platform FROM videos WHERE id = ?",
                (video_id,),
            ).fetchone()
            if not row:
                return
            source_url = row["source_url"]
            platform = row["platform"] or _detect_supported_platform(source_url)
            conn.execute(
                "UPDATE videos SET status = ?, processing_step = ? WHERE id = ?",
                ("processing", "downloading", video_id),
            )

        download_result = download_video(
            source_url,
            settings.download_path,
            video_id,
            platform,
        )

        # Optional compression (large files only — silently skipped on failure)
        try:
            compress_video(Path(download_result["local_video_path"]))
        except Exception:
            pass

        # Mark: extracting audio
        with get_connection() as conn:
            conn.execute(
                "UPDATE videos SET processing_step = ? WHERE id = ?",
                ("extracting", video_id),
            )

        video_path = Path(download_result["local_video_path"])
        audio_path = extract_audio(video_path, settings.audio_path)           # WAV for Whisper
        try:
            extract_audio_mp3(video_path, settings.audio_path)                # MP3 for playback
        except Exception:
            pass  # MP3 is optional — transcription still works without it

        # Mark: transcribing
        with get_connection() as conn:
            conn.execute(
                "UPDATE videos SET processing_step = ? WHERE id = ?",
                ("transcribing", video_id),
            )

        transcript_result = transcribe_audio(audio_path)

        content_type = detect_content_type(
            transcript_result["full_text"],
            download_result.get("duration_seconds"),
        )
        professional_review = None
        if (transcript_result.get("full_text") or "").strip():
            try:
                professional_review = build_professional_review(
                    transcript_result["full_text"],
                    transcript_result.get("segments"),
                    title=download_result.get("title"),
                    description=download_result.get("description"),
                    platform=platform,
                    uploader=download_result.get("uploader"),
                    duration_seconds=download_result.get("duration_seconds"),
                )
            except Exception:
                professional_review = None

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
                "platform": platform,
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
                    content_type = ?, creator_url = ?
                WHERE id = ?
                """,
                (
                    platform,
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
                    download_result.get("uploader_url"),
                    video_id,
                ),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO transcripts
                    (video_id, language, full_text, professional_review, segments_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    video_id,
                    transcript_result["language"],
                    transcript_result["full_text"],
                    professional_review,
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
    platform = _detect_supported_platform(url)

    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO videos (source_url, platform, status) VALUES (?, ?, ?)",
            (url, platform, "processing"),
        )
        video_id = cursor.lastrowid

    background_tasks.add_task(process_video, video_id)
    return get_video(video_id)


@router.get("", response_model=list[VideoResponse])
def list_videos(
    response: Response,
    limit: int = 20,
    offset: int = 0,
) -> list[VideoResponse]:
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM videos WHERE deleted_at IS NULL"
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM videos WHERE deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    response.headers["X-Total-Count"] = str(total)
    return [_row_to_video_response(row) for row in rows]


@router.get("/export")
def export_videos() -> Response:
    """Download the entire active library as a CSV file."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT v.id, v.title, v.uploader, v.duration_seconds, v.status,
                   v.tags, v.created_at, v.source_url, v.creator_url, t.full_text
            FROM videos v
            LEFT JOIN transcripts t ON v.id = t.video_id
            WHERE v.deleted_at IS NULL
            ORDER BY v.created_at DESC
            """
        ).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "ID", "Title", "Creator", "Duration", "Status",
        "Tags", "Date", "Source URL", "Transcript Preview",
    ])

    for row in rows:
        tags    = ", ".join(json.loads(row["tags"])) if row["tags"] else ""
        text    = row["full_text"] or ""
        preview = (text[:200] + "…") if len(text) > 200 else text
        secs    = row["duration_seconds"] or 0
        dur     = f"{int(secs // 60)}:{int(secs % 60):02d}" if secs else ""
        writer.writerow([
            row["id"],
            row["title"] or "",
            row["uploader"] or "",
            dur,
            row["status"],
            tags,
            row["created_at"],
            row["source_url"],
            preview,
        ])

    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="myinsta-library.csv"'},
    )


@router.get("/stats")
def get_stats() -> dict:
    """Aggregate library statistics."""
    with get_connection() as conn:
        total   = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
        ready   = conn.execute("SELECT COUNT(*) FROM videos WHERE status = 'ready'").fetchone()[0]
        dur_row = conn.execute("SELECT SUM(duration_seconds) FROM videos WHERE status = 'ready'").fetchone()
        total_seconds = dur_row[0] or 0
        chats   = conn.execute("SELECT COUNT(*) FROM chat_messages WHERE role = 'user'").fetchone()[0]
    return {
        "total_videos": total,
        "ready_videos": ready,
        "total_duration_seconds": float(total_seconds),
        "total_chats": chats,
    }


@router.get("/trash", response_model=list[VideoResponse])
def list_trash() -> list[VideoResponse]:
    """Return soft-deleted videos from the last 30 days. Purge older items."""
    with get_connection() as conn:
        # Purge items older than 30 days — delete files + DB record
        expired = conn.execute(
            "SELECT storage_folder FROM videos WHERE deleted_at IS NOT NULL "
            "AND deleted_at < datetime('now', '-30 days')"
        ).fetchall()
        for row in expired:
            delete_library_folder(settings.library_path, row["storage_folder"])
        conn.execute(
            "DELETE FROM videos WHERE deleted_at IS NOT NULL "
            "AND deleted_at < datetime('now', '-30 days')"
        )
        # Return remaining trash (last 30 days)
        rows = conn.execute(
            "SELECT * FROM videos WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC"
        ).fetchall()
        return [_row_to_video_response(row) for row in rows]


@router.post("/{video_id}/restore", response_model=VideoResponse)
def restore_video(video_id: int) -> VideoResponse:
    """Restore a soft-deleted video back to the active library."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM videos WHERE id = ? AND deleted_at IS NOT NULL", (video_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video not found in trash")
        conn.execute("UPDATE videos SET deleted_at = NULL WHERE id = ?", (video_id,))
    return get_video(video_id)


@router.delete("/{video_id}/permanent", status_code=204)
def permanent_delete_video(video_id: int) -> None:
    """Permanently delete a trashed video and remove all its files."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT storage_folder FROM videos WHERE id = ? AND deleted_at IS NOT NULL",
            (video_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video not found in trash")
        storage_folder = row["storage_folder"]
        conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
    delete_library_folder(settings.library_path, storage_folder)


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(video_id: int) -> VideoResponse:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM videos WHERE id = ? AND deleted_at IS NULL", (video_id,)
        ).fetchone()
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
            updates["description_translation_ar"] = None
            metadata_updates["description"] = payload.description
        if payload.notes is not None:
            updates["notes"] = payload.notes
        if payload.tags is not None:
            updates["tags"] = json.dumps(payload.tags)

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
                    """
                    UPDATE transcripts
                    SET full_text = ?, translation_ar = NULL, cleaned_text = NULL,
                        cleaned_translation_ar = NULL
                    WHERE video_id = ?
                    """,
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


@router.post("/{video_id}/translate-description", response_model=DescriptionTranslationResponse)
def translate_video_description(video_id: int) -> DescriptionTranslationResponse:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, description, description_translation_ar
            FROM videos
            WHERE id = ? AND deleted_at IS NULL
            """,
            (video_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")

        cached = (
            (row["description_translation_ar"] or "").strip()
            if "description_translation_ar" in row.keys()
            else ""
        )
        if cached:
            return DescriptionTranslationResponse(
                video_id=video_id,
                target_language="ar",
                translated_text=cached,
            )

        description = (row["description"] or "").strip()
        if not description:
            raise HTTPException(status_code=400, detail="Description is empty.")

    try:
        translated_text = translate_to_arabic(description)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Arabic description translation failed: {exc}",
        ) from exc

    with get_connection() as conn:
        conn.execute(
            "UPDATE videos SET description_translation_ar = ? WHERE id = ?",
            (translated_text, video_id),
        )

    return DescriptionTranslationResponse(
        video_id=video_id,
        target_language="ar",
        translated_text=translated_text,
    )


@router.post("/{video_id}/translate", response_model=TranscriptTranslationResponse)
def translate_video_transcript(video_id: int) -> TranscriptTranslationResponse:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT v.id, v.status, t.full_text, t.language, t.translation_ar
            FROM videos v
            LEFT JOIN transcripts t ON v.id = t.video_id
            WHERE v.id = ? AND v.deleted_at IS NULL
            """,
            (video_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")
        if row["status"] != "ready":
            raise HTTPException(
                status_code=400,
                detail="Translation is available only after transcription finishes.",
            )

        cached = (row["translation_ar"] or "").strip() if "translation_ar" in row.keys() else ""
        if cached:
            return TranscriptTranslationResponse(
                video_id=video_id,
                target_language="ar",
                translated_text=cached,
            )

        full_text = (row["full_text"] or "").strip() if row["full_text"] else ""
        if not full_text:
            raise HTTPException(status_code=400, detail="Transcript is empty.")

    try:
        translated_text = translate_to_arabic(full_text, row["language"])
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Arabic translation failed: {exc}",
        ) from exc

    with get_connection() as conn:
        conn.execute(
            "UPDATE transcripts SET translation_ar = ? WHERE video_id = ?",
            (translated_text, video_id),
        )

    return TranscriptTranslationResponse(
        video_id=video_id,
        target_language="ar",
        translated_text=translated_text,
    )


@router.post("/{video_id}/cleanup", response_model=TranscriptCleanupResponse)
def clean_video_transcript(video_id: int, target_language: str = "en") -> TranscriptCleanupResponse:
    if target_language not in {"en", "ar"}:
        raise HTTPException(status_code=400, detail="target_language must be 'en' or 'ar'.")

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT v.id, v.status, t.full_text, t.language, t.segments_json,
                   t.cleaned_text, t.cleaned_translation_ar
            FROM videos v
            LEFT JOIN transcripts t ON v.id = t.video_id
            WHERE v.id = ? AND v.deleted_at IS NULL
            """,
            (video_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")
        if row["status"] != "ready":
            raise HTTPException(
                status_code=400,
                detail="Transcript cleanup is available only after transcription finishes.",
            )

        cached_column = "cleaned_translation_ar" if target_language == "ar" else "cleaned_text"
        cached = (row[cached_column] or "").strip() if cached_column in row.keys() else ""
        if cached:
            return TranscriptCleanupResponse(
                video_id=video_id,
                target_language=target_language,
                cleaned_text=cached,
            )

        full_text = (row["full_text"] or "").strip() if row["full_text"] else ""
        if not full_text:
            raise HTTPException(status_code=400, detail="Transcript is empty.")
        segments = json.loads(row["segments_json"]) if row["segments_json"] else None

    try:
        cleaned_text = clean_transcript_text(full_text, segments)
        output_text = (
            translate_to_arabic(cleaned_text, row["language"])
            if target_language == "ar"
            else cleaned_text
        )
    except Exception as exc:
        action = "Arabic transcript cleanup" if target_language == "ar" else "Transcript cleanup"
        raise HTTPException(status_code=502, detail=f"{action} failed: {exc}") from exc

    with get_connection() as conn:
        if target_language == "ar":
            conn.execute(
                """
                UPDATE transcripts
                SET cleaned_text = COALESCE(cleaned_text, ?),
                    cleaned_translation_ar = ?
                WHERE video_id = ?
                """,
                (cleaned_text, output_text, video_id),
            )
        else:
            conn.execute(
                "UPDATE transcripts SET cleaned_text = ? WHERE video_id = ?",
                (output_text, video_id),
            )

    return TranscriptCleanupResponse(
        video_id=video_id,
        target_language=target_language,
        cleaned_text=output_text,
    )


@router.post("/{video_id}/review", response_model=TranscriptReviewResponse)
def review_video_transcript(video_id: int) -> TranscriptReviewResponse:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT v.id, v.status, v.title, v.description, v.platform, v.uploader,
                   v.duration_seconds, t.full_text, t.segments_json, t.professional_review
            FROM videos v
            LEFT JOIN transcripts t ON v.id = t.video_id
            WHERE v.id = ? AND v.deleted_at IS NULL
            """,
            (video_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")
        if row["status"] != "ready":
            raise HTTPException(
                status_code=400,
                detail="Professional review is available only after transcription finishes.",
            )

        cached = (row["professional_review"] or "").strip() if "professional_review" in row.keys() else ""
        if cached:
            return TranscriptReviewResponse(video_id=video_id, review_text=cached)

        full_text = (row["full_text"] or "").strip() if row["full_text"] else ""
        if not full_text:
            raise HTTPException(status_code=400, detail="Transcript is empty.")
        segments = json.loads(row["segments_json"]) if row["segments_json"] else None

    try:
        review_text = build_professional_review(
            full_text,
            segments,
            title=row["title"],
            description=row["description"],
            platform=row["platform"],
            uploader=row["uploader"],
            duration_seconds=row["duration_seconds"],
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Professional review failed: {exc}") from exc

    with get_connection() as conn:
        conn.execute(
            "UPDATE transcripts SET professional_review = ? WHERE video_id = ?",
            (review_text, video_id),
        )

    return TranscriptReviewResponse(video_id=video_id, review_text=review_text)


def _format_chat_answer_language(answer: str, answer_language: str) -> str:
    if answer_language == "english":
        return answer

    try:
        arabic_answer = translate_to_arabic(answer)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Arabic chat translation failed: {exc}",
        ) from exc

    if answer_language == "arabic":
        return arabic_answer

    return f"English:\n{answer}\n\nArabic:\n{arabic_answer}"


@router.delete("/{video_id}", status_code=204)
def delete_video(video_id: int) -> None:
    """Soft-delete: move to trash. Files are kept for 30-day recovery window."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM videos WHERE id = ? AND deleted_at IS NULL", (video_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")
        conn.execute(
            "UPDATE videos SET deleted_at = datetime('now') WHERE id = ?", (video_id,)
        )


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


@router.get("/{video_id}/audio")
def stream_audio(video_id: int, download: bool = False) -> FileResponse:
    """Stream or download the extracted audio for a video.
    Serves MP3 (high quality stereo) if available, falls back to WAV.
    Add ?download=true to trigger a file download instead of inline playback.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT local_audio_path, title FROM videos WHERE id = ?",
            (video_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")
        if not row["local_audio_path"]:
            raise HTTPException(status_code=404, detail="Audio not available for this video")

        wav_path = Path(row["local_audio_path"])
        mp3_path = wav_path.with_suffix(".mp3")

        # Prefer MP3 (high quality stereo), fall back to WAV
        if mp3_path.exists():
            audio_path = mp3_path
            media_type = "audio/mpeg"
        elif wav_path.exists():
            audio_path = wav_path
            media_type = "audio/wav"
        else:
            raise HTTPException(status_code=404, detail="Audio file not found on disk")

        safe_title = (row["title"] or f"video-{video_id}").replace("/", "-")
        filename = f"{safe_title}{audio_path.suffix}"

        headers = {}
        if download:
            headers["Content-Disposition"] = f'attachment; filename="{filename}"'

        return FileResponse(
            audio_path,
            media_type=media_type,
            filename=filename,
            headers=headers,
        )


@router.post("/{video_id}/export-notion")
def export_to_notion(video_id: int, payload: NotionExportRequest) -> dict:
    """Proxy a Notion API page-creation request. API key is never stored server-side."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM videos WHERE id = ? AND deleted_at IS NULL", (video_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")
        transcript_row = conn.execute(
            "SELECT full_text FROM transcripts WHERE video_id = ?", (video_id,)
        ).fetchone()

    title      = (row["title"] or f"Video #{video_id}")[:200]
    creator    = row["uploader"] or ""
    tags       = json.loads(row["tags"]) if row["tags"] else []
    transcript = (transcript_row["full_text"] or "") if transcript_row else ""
    notes_html = row["notes"] or ""
    notes_text = re.sub(r"<[^>]+>", " ", notes_html).strip()

    def text_block(content: str) -> dict:
        return {
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]},
        }

    def h2_block(content: str) -> dict:
        return {
            "object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": content}}]},
        }

    children: list[dict] = []

    # Callout with meta info
    meta = f"👤 {creator}  •  🔗 {row['source_url']}"
    if tags:
        meta += f"  •  🏷 {', '.join(tags)}"
    children.append({
        "object": "block", "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": meta}}],
            "icon": {"emoji": "📹"},
        },
    })

    # Transcript
    if transcript:
        children.append(h2_block("📝 Transcript"))
        for chunk in [transcript[i:i + 2000] for i in range(0, len(transcript), 2000)]:
            children.append(text_block(chunk))

    # Notes
    if notes_text:
        children.append(h2_block("📒 My Notes"))
        for chunk in [notes_text[i:i + 2000] for i in range(0, len(notes_text), 2000)]:
            children.append(text_block(chunk))

    page_data = {
        "parent": {"database_id": payload.database_id.replace("-", "")},
        "properties": {
            "title": {"title": [{"type": "text", "text": {"content": title}}]},
        },
        "children": children[:100],  # Notion max 100 blocks per request
    }

    try:
        data = json.dumps(page_data).encode("utf-8")
        req = urllib.request.Request(
            "https://api.notion.com/v1/pages",
            data=data,
            headers={
                "Authorization": f"Bearer {payload.api_key}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return {"id": result["id"], "url": result.get("url", ""), "title": title}
    except urllib.error.HTTPError as exc:
        detail = json.loads(exc.read().decode("utf-8")).get("message", "Notion API error")
        raise HTTPException(status_code=exc.code, detail=detail)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


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
                transcript_text=full_text or None,
            )
        else:
            answer = answer_from_transcript(message, full_text, segments)

        answer = _format_chat_answer_language(answer, payload.answer_language)

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
