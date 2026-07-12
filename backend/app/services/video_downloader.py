"""Download Instagram/YouTube media with yt-dlp.

YouTube changes player clients often. This module:
- prefers progressive MP4 when possible (no merge)
- tries modern player clients (default, android_vr, mweb, web_safari, tv…)
- avoids broken legacy clients (plain ios)
- uses cookies file and/or browser cookies with clear failures
- solves JS challenges via Node when available
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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


def _normalize_url(url: str, platform: str) -> str:
    """Normalize short/share YouTube URLs so yt-dlp sees a clean watch URL."""
    if platform != "youtube":
        return url

    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().removeprefix("www.")

    # youtu.be/<id>
    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"

    # youtube.com/shorts/<id> or /live/<id> or /embed/<id>
    if "youtube.com" in host:
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2 and parts[0] in {"shorts", "live", "embed", "v"}:
            return f"https://www.youtube.com/watch?v={parts[1]}"
        qs = parse_qs(parsed.query)
        if "v" in qs and qs["v"]:
            return f"https://www.youtube.com/watch?v={qs['v'][0]}"

    return url


def _youtube_cookies_file() -> Path | None:
    for candidate in (
        settings.youtube_cookies_file,
        settings.instagram_cookies_file,
    ):
        if not candidate:
            continue
        path = Path(candidate)
        if path.is_file() and path.stat().st_size > 32:
            return path
    return None


def _youtube_browser() -> str | None:
    browser = (settings.youtube_cookies_from_browser or "").strip().lower()
    return browser or None


def _cookie_modes_for(platform: str) -> list[dict]:
    """
    Return cookie configurations to try, most reliable first.

    Each item is a partial ydl_opts dict (cookiefile and/or cookiesfrombrowser).
    Always ends with {} so a cookieless attempt still runs for public videos.
    """
    if platform != "youtube":
        modes: list[dict] = []
        cookies = settings.instagram_cookies_file
        if cookies and Path(cookies).is_file():
            modes.append({"cookiefile": cookies})
        modes.append({})
        return modes

    modes = []
    browser = _youtube_browser()
    cookie_file = _youtube_cookies_file()

    # Prefer an explicit Netscape cookies file on servers (stable).
    if cookie_file:
        modes.append({"cookiefile": str(cookie_file)})

    # Browser profile is handy on local Windows/macOS.
    if browser:
        modes.append({"cookiesfrombrowser": (browser,)})

    # Public videos sometimes work without cookies.
    modes.append({})

    # De-dupe while preserving order
    seen: set[str] = set()
    unique: list[dict] = []
    for mode in modes:
        key = repr(sorted(mode.items()))
        if key not in seen:
            seen.add(key)
            unique.append(mode)
    return unique


def _apply_youtube_runtime_options(ydl_opts: dict, platform: str) -> None:
    if platform != "youtube":
        return

    # Needed for "n" signature / EJS challenge solving on many videos.
    if shutil.which("node"):
        ydl_opts["js_runtimes"] = {"node": {}}

    # Let yt-dlp pull remote EJS components when the package supports it.
    ydl_opts.setdefault("remote_components", ["ejs:github"])


def _cookie_status_for(platform: str) -> str:
    if platform != "youtube":
        return ""

    parts: list[str] = []
    cookie_file = _youtube_cookies_file()
    browser = _youtube_browser()

    if cookie_file:
        parts.append(
            f"Cookie file OK: {cookie_file} ({cookie_file.stat().st_size} bytes)."
        )
    else:
        configured = settings.youtube_cookies_file or settings.instagram_cookies_file
        if configured:
            parts.append(f"Configured cookie file missing or empty: {configured}.")
        else:
            parts.append("No YOUTUBE_COOKIES_FILE is configured.")

    if browser:
        parts.append(f"Browser cookie source: {browser}.")
    else:
        parts.append("YOUTUBE_COOKIES_FROM_BROWSER is not set.")

    if not shutil.which("node"):
        parts.append(
            "Node.js is not on PATH (recommended for YouTube signature solving)."
        )

    return " ".join(parts)


def _format_selectors_for(platform: str) -> list[str | None]:
    """Prefer simple progressive MP4 first — fewer merge failures."""
    if platform == "youtube":
        return [
            # Progressive MP4 only (single file, no ffmpeg merge)
            "best[ext=mp4][vcodec!=none][acodec!=none]/best[ext=mp4]/best",
            # Separate streams merged to mp4
            "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[ext=mp4]/best",
            "bestvideo+bestaudio/best",
            "best",
            None,
        ]
    return ["best[ext=mp4]/best"]


def _extractor_args_for(platform: str) -> list[dict | None]:
    """
    Modern YouTube player clients (2026).

    Avoid plain `ios` (often HTTP 400). Prefer yt-dlp defaults, then
    android_vr / mweb / web_safari / tv clients used by current yt-dlp.
    """
    if platform == "youtube":
        return [
            # Let yt-dlp choose (android_vr + web_safari, or tv_downgraded when cookies)
            None,
            {"youtube": {"player_client": ["default"]}},
            {"youtube": {"player_client": ["android_vr", "web_safari"]}},
            {"youtube": {"player_client": ["mweb", "web_safari"]}},
            {"youtube": {"player_client": ["tv", "tv_downgraded"]}},
            {"youtube": {"player_client": ["web_embedded", "web"]}},
            # Last resort: android only (sometimes still works for public videos)
            {"youtube": {"player_client": ["android"]}},
        ]
    return [None]


def _base_ydl_opts(output_template: str, platform: str) -> dict:
    opts: dict = {
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "noplaylist": True,
        "updatetime": False,
        "windowsfilenames": True,
        "retries": 5,
        "fragment_retries": 5,
        "extractor_retries": 3,
        "file_access_retries": 3,
        "socket_timeout": 30,
        "concurrent_fragment_downloads": 1,
        # Prefer free formats when SABR/premium-only streams appear
        "extractor_args": {},
    }

    if platform == "youtube":
        opts["http_headers"] = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

    _apply_youtube_runtime_options(opts, platform)
    return opts

def _friendly_download_error(error: Exception, platform: str) -> str:
    message = str(error)
    lower = message.lower()

    if platform == "youtube":
        if (
            "sign in to confirm" in lower
            or "not a bot" in lower
            or "login required" in lower
            or "confirm you're not a bot" in lower
            or ("cookies" in lower and ("required" in lower or "use --cookies" in lower))
        ):
            return (
                "YouTube blocked this download (bot/sign-in check). "
                f"{_cookie_status_for(platform)} "
                "Fix: export a fresh cookies.txt from a browser signed into YouTube "
                "(extension: 'Get cookies.txt LOCALLY'), set YOUTUBE_COOKIES_FILE, "
                "upgrade yt-dlp[default], ensure Node.js is installed, then retry."
            )

        if "requested format is not available" in lower or "no video formats" in lower:
            return (
                "YouTube did not provide a downloadable format for this video. "
                "Update yt-dlp (`pip install -U 'yt-dlp[default]'`), refresh cookies, "
                "and confirm the video is public (not members-only / region-locked)."
            )

        if "private video" in lower or "this video is private" in lower:
            return "This YouTube video is private. Sign in with cookies that can access it, or use a public link."

        if "video unavailable" in lower or "has been removed" in lower:
            return "This YouTube video is unavailable or was removed. Check the link."

        if "age" in lower and ("restrict" in lower or "confirm your age" in lower):
            return (
                "This video is age-restricted. Export cookies from a signed-in YouTube "
                "account that can watch it, set YOUTUBE_COOKIES_FILE, and retry."
            )

        if "http error 403" in lower or "403" in lower:
            return (
                "YouTube returned HTTP 403 (forbidden). Refresh cookies, update yt-dlp, "
                "and try again. Some formats need a logged-in session."
            )

        if "n challenge" in lower or "js interpreter" in lower or "ejs" in lower:
            return (
                "YouTube signature challenge failed. Install Node.js on the server and run: "
                "pip install -U 'yt-dlp[default]' then restart the backend."
            )

        if "ffmpeg" in lower and ("not found" in lower or "merging" in lower):
            return (
                "Download needed FFmpeg to merge video+audio, but FFmpeg failed or is missing. "
                "Install FFmpeg on PATH and retry."
            )

    detail = re.sub(r"\s+", " ", message).strip()
    if len(detail) > 280:
        detail = detail[:277] + "..."
    return f"Video download failed: {detail}"


def _resolve_output_path(info: dict, ydl: yt_dlp.YoutubeDL, output_dir: Path, video_id: int) -> Path:
    """Find the real file after download (handles merge renames)."""
    requested = Path(ydl.prepare_filename(info))
    if requested.exists():
        return requested

    # After merge, extension is often mp4 regardless of original
    stem = output_dir / str(video_id)
    for ext in (".mp4", ".mkv", ".webm", ".m4a", ".mp3"):
        candidate = Path(str(stem) + ext)
        if candidate.exists():
            return candidate

    matches = sorted(
        p for p in output_dir.glob(f"{video_id}.*")
        if p.is_file() and p.suffix.lower() not in {".part", ".ytdl", ".temp"}
    )
    if matches:
        # Prefer largest non-empty file
        matches.sort(key=lambda p: p.stat().st_size, reverse=True)
        if matches[0].stat().st_size > 0:
            return matches[0]

    raise RuntimeError("Video download failed: output file not found")


def download_video(url: str, output_dir: Path, video_id: int, platform: str = "instagram") -> dict:
    """Download a video with yt-dlp and return metadata plus local path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    url = _normalize_url(url, platform)
    output_template = str((output_dir / f"{video_id}.%(ext)s").resolve())

    base_opts = _base_ydl_opts(output_template, platform)
    last_error: Exception | None = None
    local_path: Path | None = None
    info: dict | None = None

    cookie_modes = _cookie_modes_for(platform)
    extractor_modes = _extractor_args_for(platform)
    format_modes = _format_selectors_for(platform)

    attempt_index = 0
    for cookie_mode in cookie_modes:
        for extractor_args in extractor_modes:
            for selector in format_modes:
                attempt_index += 1
                current_opts = dict(base_opts)
                current_opts.update(cookie_mode)

                # Merge extractor_args carefully (base may already have empty dict)
                if extractor_args:
                    current_opts["extractor_args"] = extractor_args
                else:
                    current_opts.pop("extractor_args", None)

                if selector:
                    current_opts["format"] = selector
                else:
                    current_opts.pop("format", None)

                try:
                    if attempt_index > 1:
                        _clear_partial_downloads(output_dir, video_id)

                    with yt_dlp.YoutubeDL(current_opts) as ydl:
                        # Single pass: download + metadata (avoids double YouTube hits)
                        extracted = ydl.extract_info(url, download=True)
                        if extracted is None:
                            raise RuntimeError("no metadata returned")

                        # Playlist safety — take first entry if nested
                        if extracted.get("_type") == "playlist" and extracted.get("entries"):
                            extracted = next(
                                (e for e in extracted["entries"] if e),
                                None,
                            )
                            if extracted is None:
                                raise RuntimeError("playlist contained no videos")

                        _check_duration(extracted, platform)
                        path = _resolve_output_path(extracted, ydl, output_dir, video_id)
                        if path.stat().st_size <= 0:
                            raise RuntimeError("downloaded file is empty")

                        info = extracted
                        local_path = path
                    break
                except Exception as exc:
                    last_error = exc
                    continue
            if local_path:
                break
        if local_path:
            break

    if not local_path or not info:
        raise RuntimeError(_friendly_download_error(last_error or RuntimeError("unknown"), platform)) from last_error

    uploader_url = info.get("uploader_url") or info.get("channel_url") or None
    uploader_id = info.get("uploader_id") or info.get("channel_id") or None

    if not uploader_url and uploader_id and platform == "instagram":
        uploader_url = f"https://www.instagram.com/{uploader_id}/"

    # Prefer highest-res thumbnail when list is present
    thumbnail = info.get("thumbnail")
    thumbnails = info.get("thumbnails") or []
    if thumbnails:
        best_thumb = max(
            (t for t in thumbnails if t.get("url")),
            key=lambda t: (t.get("height") or 0) * (t.get("width") or 0),
            default=None,
        )
        if best_thumb:
            thumbnail = best_thumb.get("url") or thumbnail

    return {
        "platform": platform,
        "title": info.get("title"),
        "description": info.get("description"),
        "uploader": info.get("uploader") or info.get("channel"),
        "uploader_url": uploader_url,
        "duration_seconds": info.get("duration"),
        "thumbnail_url": thumbnail,
        "local_video_path": str(local_path.resolve()),
    }
