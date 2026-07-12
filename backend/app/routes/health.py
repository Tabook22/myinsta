import shutil
import subprocess

from fastapi import APIRouter

from app.core.config import settings
from app.services.video_downloader import inspect_youtube_cookies, _node_version

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/youtube")
def youtube_download_health() -> dict:
    """Diagnose YouTube download prerequisites (cookies, node, yt-dlp, EJS)."""
    yt_dlp_version = None
    yt_dlp_ejs_version = None
    try:
        from importlib.metadata import version

        yt_dlp_version = version("yt-dlp")
        try:
            yt_dlp_ejs_version = version("yt-dlp-ejs")
        except Exception:
            yt_dlp_ejs_version = None
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
    node_ver = _node_version()
    node_version_str = (
        f"{node_ver[0]}.{node_ver[1]}.{node_ver[2]}" if node_ver else None
    )
    node_ok_for_ejs = bool(node_ver and node_ver[0] >= 22)
    deno = shutil.which("deno")
    ffmpeg = shutil.which("ffmpeg")

    ready_hints: list[str] = []
    if not cookies.get("usable"):
        ready_hints.append(
            "Export a fresh Netscape cookies.txt while signed into youtube.com "
            "(need LOGIN_INFO or SID cookies), replace YOUTUBE_COOKIES_FILE, restart."
        )
    if not node and not deno:
        ready_hints.append(
            "Install Node.js 22+ (or Deno 2.3+) — required for YouTube n-challenge / EJS."
        )
    elif node_ver and node_ver[0] < 22 and not deno:
        ready_hints.append(
            f"Node v{node_version_str} is too old for yt-dlp-ejs (needs Node >= 22). "
            "Install Node 22 from NodeSource, then restart myinsta.service."
        )
    if not ffmpeg:
        ready_hints.append("Install FFmpeg (needed when video+audio must be merged).")
    if not yt_dlp_version:
        ready_hints.append("yt-dlp is not installed in this environment.")
    else:
        ready_hints.append("Keep yt-dlp updated: pip install -U 'yt-dlp[default]' yt-dlp-ejs")
    if not yt_dlp_ejs_version:
        ready_hints.append("Install EJS package: pip install -U yt-dlp-ejs")

    ejs_ready = (node_ok_for_ejs or bool(deno)) and bool(yt_dlp_ejs_version or yt_dlp_version)
    overall = "ok" if cookies.get("usable") and ejs_ready and yt_dlp_version else "degraded"

    return {
        "status": overall,
        "yt_dlp_version": yt_dlp_version,
        "yt_dlp_ejs_version": yt_dlp_ejs_version,
        "node_path": node,
        "node_version": node_version_str,
        "node_ok_for_ejs": node_ok_for_ejs,
        "deno_path": deno,
        "ffmpeg_path": ffmpeg,
        "cookies": cookies,
        "youtube_cookies_file_setting": settings.youtube_cookies_file or None,
        "youtube_cookies_from_browser": settings.youtube_cookies_from_browser or None,
        "youtube_proxy_set": bool((settings.youtube_proxy or "").strip()),
        "hints": ready_hints,
    }
