import os
from pathlib import Path

import yt_dlp

from app.core.config import settings


def _clear_partial_downloads(output_dir: Path, video_id: int) -> None:
    for path in output_dir.glob(f"{video_id}.*"):
        if path.is_file():
            path.unlink(missing_ok=True)


def _duration_limit_for(platform: str) -> int | None:
    if platform == "youtube":
        return settings.max_youtube_duration_seconds
    return None


def _check_duration(info: dict, platform: str) -> None:
    limit = _duration_limit_for(platform)
    duration = info.get("duration")
    if limit and duration and duration > limit:
        minutes = int(limit // 60)
        raise RuntimeError(
            f"YouTube videos longer than {minutes} minutes are not supported yet. "
            "Choose a shorter video or raise MYINSTA_MAX_YOUTUBE_DURATION_SECONDS."
        )


def download_video(url: str, output_dir: Path, video_id: int, platform: str = "instagram") -> dict:
    """Download a video with yt-dlp and return metadata plus local path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str((output_dir / f"{video_id}.%(ext)s").resolve())

    ydl_opts = {
        "outtmpl": output_template,
        "format": "best[ext=mp4]/best",
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "noplaylist": True,
        "updatetime": False,
        "windowsfilenames": True,
        "retries": 3,
        "fragment_retries": 3,
    }

    cookies_file = os.getenv("INSTAGRAM_COOKIES_FILE")
    if cookies_file and Path(cookies_file).exists():
        ydl_opts["cookiefile"] = cookies_file
    elif platform == "youtube":
        cookies_file = os.getenv("YOUTUBE_COOKIES_FILE")
        if cookies_file and Path(cookies_file).exists():
            ydl_opts["cookiefile"] = cookies_file

    last_error = None
    for attempt in range(2):
        try:
            if attempt:
                _clear_partial_downloads(output_dir, video_id)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info is None:
                    raise RuntimeError("no metadata returned")
                _check_duration(info, platform)
                info = ydl.extract_info(url, download=True)
                if info is None:
                    raise RuntimeError("no metadata returned")
                _check_duration(info, platform)

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

    # uploader_url  → full profile URL  e.g. https://www.instagram.com/regita_aya/
    # uploader_id   → username           e.g. regita_aya
    # uploader      → display name       e.g. Regita Darsono Putri
    uploader_url = info.get("uploader_url") or info.get("channel_url") or None
    uploader_id  = info.get("uploader_id") or info.get("channel_id") or None

    # Build profile URL from username if yt-dlp didn't return one directly
    if not uploader_url and uploader_id and "instagram" in url.lower():
        uploader_url = f"https://www.instagram.com/{uploader_id}/"

    return {
        "platform": platform,
        "title": info.get("title"),
        "description": info.get("description"),
        "uploader": info.get("uploader") or info.get("channel"),
        "uploader_url": uploader_url,
        "duration_seconds": info.get("duration"),
        "thumbnail_url": info.get("thumbnail"),
        "local_video_path": str(local_path.resolve()),
    }
