import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from app.core.config import settings
from app.services.library_search import rebuild_library_fts


VIDEO_PATH_COLUMNS = ("local_video_path", "local_audio_path", "local_transcript_path")
ProgressCallback = Callable[[int, int, str], None]


def _row_dicts(conn: sqlite3.Connection, table: str) -> list[dict]:
    rows = conn.execute(f"SELECT * FROM {table} ORDER BY id ASC").fetchall()
    return [dict(row) for row in rows]


def _write_directory(
    archive: zipfile.ZipFile,
    source_dir: Path,
    archive_dir: str,
    written: set[Path],
    *,
    progress: ProgressCallback | None = None,
    progress_state: dict | None = None,
    stage: str = "Adding files",
) -> None:
    if not source_dir.exists():
        return

    root = source_dir.resolve()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        resolved = path.resolve()
        archive.write(resolved, f"{archive_dir}/{resolved.relative_to(root).as_posix()}")
        written.add(resolved)
        if progress and progress_state is not None:
            progress_state["current"] += 1
            progress(progress_state["current"], progress_state["total"], stage)


def _write_referenced_files(
    archive: zipfile.ZipFile,
    videos: list[dict],
    written: set[Path],
    *,
    progress: ProgressCallback | None = None,
    progress_state: dict | None = None,
) -> list[dict]:
    included: list[dict] = []
    path_columns = ("local_video_path", "local_audio_path", "local_transcript_path")

    for video in videos:
        candidates: list[Path] = []
        for column in path_columns:
            value = video.get(column)
            if value:
                candidates.append(Path(value))
                if column == "local_audio_path":
                    candidates.append(Path(value).with_suffix(".mp3"))

        for candidate in candidates:
            if not candidate.exists() or not candidate.is_file():
                continue
            resolved = candidate.resolve()
            if resolved in written:
                continue

            archive_name = f"referenced-files/video-{video['id']}/{resolved.name}"
            archive.write(resolved, archive_name)
            written.add(resolved)
            if progress and progress_state is not None:
                progress_state["current"] += 1
                progress(progress_state["current"], progress_state["total"], "Adding referenced files")
            included.append(
                {
                    "video_id": video["id"],
                    "source_path": str(resolved),
                    "archive_path": archive_name,
                }
            )

    return included


def _list_files(source_dir: Path) -> list[Path]:
    if not source_dir.exists():
        return []
    return [path for path in source_dir.rglob("*") if path.is_file()]


def _count_referenced_files(videos: list[dict], written: set[Path]) -> int:
    count = 0
    for video in videos:
        for column in VIDEO_PATH_COLUMNS:
            value = video.get(column)
            if not value:
                continue
            candidates = [Path(value)]
            if column == "local_audio_path":
                candidates.append(Path(value).with_suffix(".mp3"))
            for candidate in candidates:
                if not candidate.exists() or not candidate.is_file():
                    continue
                resolved = candidate.resolve()
                if resolved in written:
                    continue
                count += 1
                written.add(resolved)
    return count


def _write_database_snapshot(archive: zipfile.ZipFile, temp_dir: Path) -> bool:
    database_file = settings.database_file
    if not database_file.exists():
        return False

    snapshot_path = temp_dir / "myinsta.sqlite3"
    source = sqlite3.connect(database_file)
    try:
        target = sqlite3.connect(snapshot_path)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()

    archive.write(snapshot_path, "database/myinsta.sqlite3")
    return True


def _read_json_member(archive: zipfile.ZipFile, name: str) -> list[dict]:
    try:
        with archive.open(name) as fh:
            payload = json.loads(fh.read().decode("utf-8"))
    except KeyError:
        return []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _safe_archive_target(root: Path, relative_name: str) -> Path:
    target = (root / relative_name).resolve()
    root_resolved = root.resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise ValueError(f"Unsafe archive path: {relative_name}")
    return target


def _copy_archive_directory(archive: zipfile.ZipFile, archive_dir: str, target_dir: Path) -> tuple[int, int]:
    imported = 0
    skipped = 0
    prefix = f"{archive_dir.rstrip('/')}/"
    for member in archive.infolist():
        if member.is_dir() or not member.filename.startswith(prefix):
            continue
        relative_name = member.filename.removeprefix(prefix)
        if not relative_name:
            continue
        target = _safe_archive_target(target_dir, relative_name)
        if target.exists() and target.is_file() and target.stat().st_size == member.file_size:
            skipped += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(member) as source, target.open("wb") as destination:
            shutil.copyfileobj(source, destination)
        imported += 1
    return imported, skipped


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


def _local_library_file(storage_folder: str | None, original_path: str | None) -> str | None:
    if not storage_folder or not original_path:
        return None
    filename = Path(original_path).name
    if not filename:
        return None
    path = settings.library_path / storage_folder / filename
    return str(path.resolve()) if path.exists() else None


def _rewrite_video_paths(video: dict) -> dict:
    rewritten = dict(video)
    storage_folder = rewritten.get("storage_folder")
    for column in VIDEO_PATH_COLUMNS:
        rewritten[column] = _local_library_file(storage_folder, rewritten.get(column))
    return rewritten


def _int_or_none(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _row_matches(existing: sqlite3.Row, payload: dict) -> bool:
    for key, value in payload.items():
        if existing[key] != value:
            return False
    return True


def _upsert_by_columns(
    conn: sqlite3.Connection,
    table: str,
    row: dict,
    *,
    conflict_column: str,
    conflict_value,
    skip_update_columns: set[str] | None = None,
) -> str:
    columns = _table_columns(conn, table)
    payload = {
        key: value
        for key, value in row.items()
        if key in columns and key != "id"
    }
    existing = conn.execute(
        f"SELECT * FROM {table} WHERE {conflict_column} = ?",
        (conflict_value,),
    ).fetchone()

    if existing:
        skipped = skip_update_columns or set()
        server_managed_columns = {"created_at", "updated_at"}
        update_payload = {
            key: value
            for key, value in payload.items()
            if key not in skipped and key != conflict_column and key not in server_managed_columns
        }
        if not update_payload or _row_matches(existing, update_payload):
            return "unchanged"
        if update_payload:
            assignments = ", ".join(f"{key} = ?" for key in update_payload)
            conn.execute(
                f"UPDATE {table} SET {assignments} WHERE id = ?",
                (*update_payload.values(), existing["id"]),
            )
        return "updated"

    if not payload:
        return "unchanged"

    names = ", ".join(payload)
    placeholders = ", ".join("?" for _ in payload)
    conn.execute(
        f"INSERT INTO {table} ({names}) VALUES ({placeholders})",
        tuple(payload.values()),
    )
    return "created"


def import_backup_archive(backup_file: Path) -> dict:
    """Merge a MyInsta backup zip into the current local library."""
    if not zipfile.is_zipfile(backup_file):
        raise ValueError("File is not a valid zip archive.")

    result = {
        "ok": True,
        "message": "Backup imported.",
        "videos_created": 0,
        "videos_updated": 0,
        "transcripts_imported": 0,
        "chat_messages_imported": 0,
        "wiki_documents_imported": 0,
        "files_imported": 0,
        "files_skipped": 0,
        "already_exists": False,
    }

    settings.library_path.mkdir(parents=True, exist_ok=True)
    settings.wiki_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(backup_file) as archive:
        names = set(archive.namelist())
        if "manifest.json" not in names or "data/videos.json" not in names:
            raise ValueError("This does not look like a MyInsta backup zip.")

        imported, skipped = _copy_archive_directory(
            archive,
            "library",
            settings.library_path,
        )
        result["files_imported"] += imported
        result["files_skipped"] += skipped
        imported, skipped = _copy_archive_directory(
            archive,
            "mywiki",
            settings.wiki_path,
        )
        result["files_imported"] += imported
        result["files_skipped"] += skipped

        videos = _read_json_member(archive, "data/videos.json")
        transcripts = _read_json_member(archive, "data/transcripts.json")
        chat_messages = _read_json_member(archive, "data/chat_messages.json")
        wiki_documents = _read_json_member(archive, "data/wiki_documents.json")

    id_map: dict[int, int] = {}
    with sqlite3.connect(settings.database_file) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        for original_video in videos:
            source_url = original_video.get("source_url")
            if not source_url:
                continue
            incoming_id = _int_or_none(original_video.get("id"))
            video = _rewrite_video_paths(original_video)
            existing = conn.execute(
                "SELECT id FROM videos WHERE source_url = ?",
                (source_url,),
            ).fetchone()
            action = _upsert_by_columns(
                conn,
                "videos",
                video,
                conflict_column="source_url",
                conflict_value=source_url,
                skip_update_columns={"source_url"},
            )
            local = conn.execute(
                "SELECT id FROM videos WHERE source_url = ?",
                (source_url,),
            ).fetchone()
            if incoming_id is not None and local:
                id_map[incoming_id] = int(local["id"])
            if action == "created":
                result["videos_created"] += 1
            elif action == "updated":
                result["videos_updated"] += 1

        for transcript in transcripts:
            original_video_id = _int_or_none(transcript.get("video_id"))
            if original_video_id is None or original_video_id not in id_map:
                continue
            local_video_id = id_map[original_video_id]
            payload = dict(transcript)
            payload["video_id"] = local_video_id
            action = _upsert_by_columns(
                conn,
                "transcripts",
                payload,
                conflict_column="video_id",
                conflict_value=local_video_id,
                skip_update_columns={"video_id"},
            )
            if action in {"created", "updated"}:
                result["transcripts_imported"] += 1

        chat_columns = _table_columns(conn, "chat_messages")
        for message in chat_messages:
            original_video_id = _int_or_none(message.get("video_id"))
            if original_video_id is None or original_video_id not in id_map:
                continue
            local_video_id = id_map[original_video_id]
            role = message.get("role")
            content = message.get("content")
            created_at = message.get("created_at")
            if not role or not content:
                continue
            existing = conn.execute(
                """
                SELECT id FROM chat_messages
                WHERE video_id = ? AND role = ? AND content = ? AND created_at = ?
                """,
                (local_video_id, role, content, created_at),
            ).fetchone()
            if existing:
                continue
            payload = {
                key: value
                for key, value in message.items()
                if key in chat_columns and key not in {"id", "video_id"}
            }
            payload["video_id"] = local_video_id
            names = ", ".join(payload)
            placeholders = ", ".join("?" for _ in payload)
            conn.execute(
                f"INSERT INTO chat_messages ({names}) VALUES ({placeholders})",
                tuple(payload.values()),
            )
            result["chat_messages_imported"] += 1

        for document in wiki_documents:
            original_video_id = _int_or_none(document.get("video_id"))
            if original_video_id is None or original_video_id not in id_map:
                continue
            local_video_id = id_map[original_video_id]
            payload = dict(document)
            payload["video_id"] = local_video_id
            if payload.get("filename"):
                payload["file_path"] = str((settings.wiki_path / payload["filename"]).resolve())
            action = _upsert_by_columns(
                conn,
                "wiki_documents",
                payload,
                conflict_column="video_id",
                conflict_value=local_video_id,
                skip_update_columns={"video_id"},
            )
            if action in {"created", "updated"}:
                result["wiki_documents_imported"] += 1

        rebuild_library_fts(conn)

    changed_count = (
        result["videos_created"]
        + result["videos_updated"]
        + result["transcripts_imported"]
        + result["chat_messages_imported"]
        + result["wiki_documents_imported"]
        + result["files_imported"]
    )
    if changed_count == 0:
        result["already_exists"] = True
        result["message"] = "Everything in this backup already exists locally. Nothing new was added."

    return result


def create_full_backup(progress: ProgressCallback | None = None) -> dict:
    """Create a zip backup containing app data, library media, and manifests."""
    created_at = datetime.now(timezone.utc)
    stamp = created_at.strftime("%Y%m%d_%H%M%S")
    temp_dir = Path(tempfile.mkdtemp(prefix="myinsta-backup-"))
    backup_path = temp_dir / f"myinsta-backup-{stamp}.zip"
    written_files: set[Path] = set()

    with sqlite3.connect(settings.database_file) as conn:
        conn.row_factory = sqlite3.Row
        videos = _row_dicts(conn, "videos")
        transcripts = _row_dicts(conn, "transcripts")
        chat_messages = _row_dicts(conn, "chat_messages")
        wiki_documents = _row_dicts(conn, "wiki_documents")

    counted_files: set[Path] = set()
    library_file_count = len(_list_files(settings.library_path))
    wiki_file_count = len(_list_files(settings.wiki_path))
    for path in _list_files(settings.library_path):
        counted_files.add(path.resolve())
    for path in _list_files(settings.wiki_path):
        counted_files.add(path.resolve())
    referenced_file_count = _count_referenced_files(videos, counted_files)
    progress_state = {
        "current": 0,
        "total": max(1, 7 + library_file_count + wiki_file_count + referenced_file_count),
    }

    def tick(stage: str) -> None:
        progress_state["current"] += 1
        if progress:
            progress(progress_state["current"], progress_state["total"], stage)

    if progress:
        progress(0, progress_state["total"], "Reading database")

    manifest = {
        "app": "MyInsta",
        "backup_version": 1,
        "created_at": created_at.isoformat(),
        "database_included": False,
        "counts": {
            "videos": len(videos),
            "transcripts": len(transcripts),
            "chat_messages": len(chat_messages),
            "wiki_documents": len(wiki_documents),
        },
        "paths": {
            "library": str(settings.library_path.resolve()),
            "wiki": str(settings.wiki_path.resolve()),
        },
        "referenced_files": [],
    }

    with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        tick("Copying database")
        manifest["database_included"] = _write_database_snapshot(archive, temp_dir)
        _write_directory(
            archive,
            settings.library_path,
            "library",
            written_files,
            progress=progress,
            progress_state=progress_state,
            stage="Adding library files",
        )
        _write_directory(
            archive,
            settings.wiki_path,
            "mywiki",
            written_files,
            progress=progress,
            progress_state=progress_state,
            stage="Adding MyWiki files",
        )
        manifest["referenced_files"] = _write_referenced_files(
            archive,
            videos,
            written_files,
            progress=progress,
            progress_state=progress_state,
        )

        tick("Writing manifest")
        archive.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
        tick("Writing video data")
        archive.writestr(
            "data/videos.json",
            json.dumps(videos, indent=2, ensure_ascii=False),
        )
        tick("Writing transcript data")
        archive.writestr(
            "data/transcripts.json",
            json.dumps(transcripts, indent=2, ensure_ascii=False),
        )
        tick("Writing chat history")
        archive.writestr(
            "data/chat_messages.json",
            json.dumps(chat_messages, indent=2, ensure_ascii=False),
        )
        tick("Writing wiki data")
        archive.writestr(
            "data/wiki_documents.json",
            json.dumps(wiki_documents, indent=2, ensure_ascii=False),
        )
        tick("Finalizing backup")
        archive.writestr(
            "README.txt",
            (
                "MyInsta full backup\n\n"
                "This archive contains a SQLite database snapshot, saved library "
                "media/transcript files, MyWiki markdown files, and JSON exports "
                "of the main app tables. It intentionally does not include .env "
                "files or YouTube/Instagram cookie files.\n"
            ),
        )

    if progress:
        progress(progress_state["total"], progress_state["total"], "Ready to download")

    return {
        "path": backup_path,
        "filename": backup_path.name,
        "temp_dir": temp_dir,
    }
