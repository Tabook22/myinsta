import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


def slugify(text: str, max_len: int = 48) -> str:
    if not text:
        return "untitled"
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug[:max_len] or "untitled"


def make_storage_stamp(title: str, when: datetime | None = None) -> str:
    when = when or datetime.now(timezone.utc)
    return f"{when.strftime('%Y%m%d_%H%M%S')}_{slugify(title)}"


def build_library_folder(library_root: Path, stamp: str, when: datetime) -> Path:
    return library_root / when.strftime("%Y") / when.strftime("%m") / stamp


def _unique_folder(base_folder: Path) -> Path:
    if not base_folder.exists():
        return base_folder
    counter = 1
    while True:
        candidate = base_folder.parent / f"{base_folder.name}_{counter}"
        if not candidate.exists():
            return candidate
        counter += 1


def save_to_library(
    library_root: Path,
    *,
    title: str,
    source_url: str,
    video_path: Path,
    audio_path: Path,
    transcript: dict,
    metadata: dict,
    when: datetime | None = None,
) -> dict:
    """Move media into a stamped library folder and write linked transcript files."""
    when = when or datetime.now(timezone.utc)
    stamp = make_storage_stamp(title, when)
    folder = _unique_folder(build_library_folder(library_root, stamp, when))
    folder.mkdir(parents=True, exist_ok=True)

    video_ext = video_path.suffix or ".mp4"
    library_video = folder / f"video{video_ext}"
    library_audio = folder / "audio.wav"
    library_transcript_txt = folder / "transcript.txt"
    library_transcript_json = folder / "transcript.json"
    library_metadata = folder / "metadata.json"

    shutil.move(str(video_path), library_video)
    if audio_path.exists():
        if audio_path.resolve() != library_audio.resolve():
            shutil.move(str(audio_path), library_audio)
    else:
        library_audio = None

    library_transcript_txt.write_text(transcript.get("full_text", ""), encoding="utf-8")
    library_transcript_json.write_text(
        json.dumps(
            {
                "language": transcript.get("language"),
                "full_text": transcript.get("full_text", ""),
                "segments": transcript.get("segments", []),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    payload = {
        "storage_stamp": folder.name,
        "storage_folder": str(folder.relative_to(library_root)).replace("\\", "/"),
        "source_url": source_url,
        "title": title,
        "saved_at": when.isoformat(),
        **metadata,
    }
    library_metadata.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "storage_stamp": folder.name,
        "storage_folder": payload["storage_folder"],
        "local_video_path": str(library_video.resolve()),
        "local_audio_path": str(library_audio.resolve()) if library_audio else None,
        "local_transcript_path": str(library_transcript_txt.resolve()),
    }


def update_transcript_file(transcript_path: Path, full_text: str, language: str | None = None) -> None:
    transcript_path.write_text(full_text, encoding="utf-8")
    json_path = transcript_path.with_name("transcript.json")
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        data["full_text"] = full_text
        if language is not None:
            data["language"] = language
        json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def update_metadata_file(folder: Path, updates: dict) -> None:
    metadata_path = folder / "metadata.json"
    if not metadata_path.exists():
        return
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    data.update(updates)
    metadata_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def delete_library_folder(library_root: Path, storage_folder: str | None) -> None:
    if not storage_folder:
        return
    folder = library_root / storage_folder
    if folder.exists() and folder.is_dir():
        shutil.rmtree(folder)
