from pathlib import Path

import yt_dlp


def _clear_partial_downloads(output_dir: Path, video_id: int) -> None:
    for path in output_dir.glob(f"{video_id}.*"):
        if path.is_file():
            path.unlink(missing_ok=True)


def download_video(url: str, output_dir: Path, video_id: int) -> dict:
    """Download a video with yt-dlp and return metadata plus local path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str((output_dir / f"{video_id}.%(ext)s").resolve())

    ydl_opts = {
        "outtmpl": output_template,
        "format": "best[ext=mp4]/best",
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "updatetime": False,
        "windowsfilenames": True,
        "retries": 3,
        "fragment_retries": 3,
    }

    last_error = None
    for attempt in range(2):
        try:
            if attempt:
                _clear_partial_downloads(output_dir, video_id)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    raise RuntimeError("no metadata returned")

                local_path = Path(ydl.prepare_filename(info))
            break
        except Exception as exc:
            last_error = exc
    else:
        raise RuntimeError(f"Video download failed: {last_error}") from last_error

    if not local_path.exists():
        matches = sorted(output_dir.glob(f"{video_id}.*"))
        if not matches:
            raise RuntimeError("Video download failed: output file not found")
        local_path = matches[0]

    return {
        "title": info.get("title"),
        "description": info.get("description"),
        "uploader": info.get("uploader") or info.get("channel"),
        "duration_seconds": info.get("duration"),
        "thumbnail_url": info.get("thumbnail"),
        "local_video_path": str(local_path.resolve()),
    }
