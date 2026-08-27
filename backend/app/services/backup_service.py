import json
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings


def _row_dicts(conn: sqlite3.Connection, table: str) -> list[dict]:
    rows = conn.execute(f"SELECT * FROM {table} ORDER BY id ASC").fetchall()
    return [dict(row) for row in rows]


def _write_directory(
    archive: zipfile.ZipFile,
    source_dir: Path,
    archive_dir: str,
    written: set[Path],
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


def _write_referenced_files(
    archive: zipfile.ZipFile,
    videos: list[dict],
    written: set[Path],
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
            included.append(
                {
                    "video_id": video["id"],
                    "source_path": str(resolved),
                    "archive_path": archive_name,
                }
            )

    return included


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


def create_full_backup() -> dict:
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
        manifest["database_included"] = _write_database_snapshot(archive, temp_dir)
        _write_directory(archive, settings.library_path, "library", written_files)
        _write_directory(archive, settings.wiki_path, "mywiki", written_files)
        manifest["referenced_files"] = _write_referenced_files(archive, videos, written_files)

        archive.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
        archive.writestr(
            "data/videos.json",
            json.dumps(videos, indent=2, ensure_ascii=False),
        )
        archive.writestr(
            "data/transcripts.json",
            json.dumps(transcripts, indent=2, ensure_ascii=False),
        )
        archive.writestr(
            "data/chat_messages.json",
            json.dumps(chat_messages, indent=2, ensure_ascii=False),
        )
        archive.writestr(
            "data/wiki_documents.json",
            json.dumps(wiki_documents, indent=2, ensure_ascii=False),
        )
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

    return {
        "path": backup_path,
        "filename": backup_path.name,
        "temp_dir": temp_dir,
    }
