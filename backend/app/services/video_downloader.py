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


def _apply_cookie_options(ydl_opts: dict, platform: str) -> None:
    cookies_file = settings.instagram_cookies_file
    if platform == "youtube":
        cookies_file = settings.youtube_cookies_file or cookies_file

        browser = settings.youtube_cookies_from_browser.strip().lower()
        if browser:
            ydl_opts["cookiesfrombrowser"] = (browser,)
            return

    if cookies_file and Path(cookies_file).exists():
        ydl_opts["cookiefile"] = cookies_file


def _cookie_status_for(platform: str) -> str:
    if platform != "youtube":
        return ""

    cookies_file = settings.youtube_cookies_file or settings.instagram_cookies_file
    if not cookies_file:
        return "No YOUTUBE_COOKIES_FILE is configured."

    path = Path(cookies_file)
    if not path.exists():
        return f"Configured cookie file does not exist: {cookies_file}"

    size = path.stat().st_size
    return f"Cookie file found at {cookies_file} ({size} bytes), but YouTube rejected it."


def _format_selectors_for(platform: str) -> list[str | None]:
    if platform == "youtube":
        return [
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
            "bestvideo+bestaudio/best",
            "best",
            None,
        ]
    return ["best[ext=mp4]/best"]


def _extractor_args_for(platform: str) -> list[dict | None]:
    if platform == "youtube":
        return [
            {"youtube": {"player_client": ["android"]}},
            {"youtube": {"player_client": ["ios"]}},
            {"youtube": {"player_client": ["android", "ios"]}},
            None,
        ]
    return [None]


def _friendly_download_error(error: Exception, platform: str) -> str:
    message = str(error)
    if platform == "youtube" and (
        "Sign in to confirm" in message
        or "not a bot" in message
        or "cookies" in message.lower()
    ):
        return (
            "YouTube blocked this download because it needs browser cookies. "
            f"{_cookie_status_for(platform)} "
            "Export a fresh cookies.txt from a browser that is signed in to YouTube, "
            "upload it to YOUTUBE_COOKIES_FILE, then restart the backend."
        )
    if platform == "youtube" and "Requested format is not available" in message:
        return (
            "YouTube did not provide a downloadable media format for this video. "
            "Try refreshing your YouTube cookies file or updating yt-dlp, then submit the video again."
        )
    return f"Video download failed: {message}"


def download_video(url: str, output_dir: Path, video_id: int, platform: str = "instagram") -> dict:
    """Download a video with yt-dlp and return metadata plus local path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str((output_dir / f"{video_id}.%(ext)s").resolve())

    ydl_opts = {
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "noplaylist": True,
        "updatetime": False,
        "windowsfilenames": True,
        "retries": 3,
        "fragment_retries": 3,
    }

    _apply_cookie_options(ydl_opts, platform)

    last_error = None
    local_path = None
    for extractor_index, extractor_args in enumerate(_extractor_args_for(platform)):
        for selector_index, selector in enumerate(_format_selectors_for(platform)):
            current_opts = dict(ydl_opts)
            if extractor_args:
                current_opts["extractor_args"] = extractor_args
            if selector:
                current_opts["format"] = selector

            for attempt in range(2):
                try:
                    if extractor_index or selector_index or attempt:
                        _clear_partial_downloads(output_dir, video_id)
                    with yt_dlp.YoutubeDL(current_opts) as ydl:
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
            if local_path:
                break
        if local_path:
            break
    else:
        raise RuntimeError(_friendly_download_error(last_error, platform)) from last_error

    if not local_path or not local_path.exists():
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
