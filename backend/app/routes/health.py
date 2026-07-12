import shutil

from fastapi import APIRouter

from app.core.config import settings
from app.services.video_downloader import inspect_youtube_cookies

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/youtube")
def youtube_download_health() -> dict:
    """Diagnose YouTube download prerequisites (cookies, node, yt-dlp)."""
    yt_dlp_version = None
    try:
        from importlib.metadata import version

        yt_dlp_version = version("yt-dlp")
    except Exception:
        try:
            import yt_dlp

            yt_dlp_version = getattr(yt_dlp, "version", None)
            if hasattr(yt_dlp_version, "__version__"):
                yt_dlp_version = yt_dlp_version.__version__
            elif not isinstance(yt_dlp_version, str):
                yt_dlp_version = "installed"
        except Exception:
            yt_dlp_version = None

    cookies = inspect_youtube_cookies()
    node = shutil.which("node")
    ffmpeg = shutil.which("ffmpeg")

    ready_hints: list[str] = []
    if not cookies.get("usable"):
        ready_hints.append(
            "Export a fresh Netscape cookies.txt while signed into youtube.com "
            "(need LOGIN_INFO or SID cookies), replace YOUTUBE_COOKIES_FILE, restart."
        )
    if not node:
        ready_hints.append("Install Node.js (required for many YouTube signature challenges).")
    if not ffmpeg:
        ready_hints.append("Install FFmpeg (needed when video+audio must be merged).")
    if not yt_dlp_version:
        ready_hints.append("yt-dlp is not installed in this environment.")
    else:
        ready_hints.append("Keep yt-dlp updated: pip install -U 'yt-dlp[default]'")

    return {
        "status": "ok" if cookies.get("usable") and node and yt_dlp_version else "degraded",
        "yt_dlp_version": yt_dlp_version,
        "node_path": node,
        "ffmpeg_path": ffmpeg,
        "cookies": cookies,
        "youtube_cookies_file_setting": settings.youtube_cookies_file or None,
        "youtube_cookies_from_browser": settings.youtube_cookies_from_browser or None,
        "youtube_proxy_set": bool((settings.youtube_proxy or "").strip()),
        "hints": ready_hints,
    }
