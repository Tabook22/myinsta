"""Download Instagram/YouTube media with yt-dlp.

YouTube actively challenges automated clients. Strategy (2026):

1. Prefer cookieless modern clients first for public videos
   (stale/banned cookies often *cause* bot checks).
2. Then try a validated cookies.txt with cookie-friendly clients
   (tv_downgraded / web_safari / mweb — not plain ios).
3. Progressive MP4 first to avoid merge failures.
4. Node.js for signature / EJS challenges when available.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
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

    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"

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


def inspect_youtube_cookies(path: Path | None = None) -> dict:
    """Inspect a Netscape cookies.txt for YouTube login usefulness."""
    path = path or _youtube_cookies_file()
    if not path or not path.is_file():
        return {
            "present": False,
            "path": str(path) if path else None,
            "usable": False,
            "issues": ["Cookie file not found."],
        }

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {
            "present": True,
            "path": str(path),
            "usable": False,
            "issues": [f"Cannot read cookie file: {exc}"],
        }

    age_days = max(0.0, (time.time() - path.stat().st_mtime) / 86400)
    lines = text.splitlines()
    data_lines = [ln for ln in lines if ln.strip() and not ln.startswith("#")]

    # Netscape format is tab-separated: domain flag path secure expiry name value
    yt_rows = []
    names: set[str] = set()
    for ln in data_lines:
        if "youtube.com" not in ln and "google.com" not in ln:
            continue
        parts = ln.split("\t")
        if len(parts) < 7:
            # Some exporters use spaces — still count domain hits
            if "youtube.com" in ln or "google.com" in ln:
                yt_rows.append(ln)
            continue
        domain, name = parts[0], parts[5]
        if "youtube.com" in domain or "google.com" in domain:
            yt_rows.append(ln)
            names.add(name)

    has_netscape_header = any(
        "Netscape" in ln or "HTTP Cookie File" in ln for ln in lines[:8]
    )
    # Detect LOGIN_INFO even if a line is malformed / not 7 tab fields
    has_login = ("LOGIN_INFO" in names) or any(
        "LOGIN_INFO" in ln and "youtube.com" in ln for ln in data_lines
    )
    has_sid = bool(
        names
        & {
            "SID",
            "__Secure-1PSID",
            "__Secure-3PSID",
            "SAPISID",
            "__Secure-1PSIDTS",
            "APISID",
            "HSID",
            "SSID",
        }
    ) or any(
        f"\t{n}\t" in ln or f"\t{n} " in ln
        for ln in data_lines
        for n in ("__Secure-1PSID", "SAPISID", "SID")
        if "youtube.com" in ln or "google.com" in ln
    )

    issues: list[str] = []
    if not has_netscape_header and not yt_rows:
        issues.append(
            "File does not look like a Netscape cookies.txt (wrong export format)."
        )
    if len(yt_rows) < 3:
        issues.append(
            "Very few youtube.com/google.com cookies — re-export while signed into youtube.com."
        )
    if not has_login:
        issues.append(
            "Missing LOGIN_INFO cookie — YouTube will bot-block downloads. "
            "Export while fully signed into https://www.youtube.com (not google.com only)."
        )
    if not has_sid:
        issues.append(
            "Missing session cookies (SID / __Secure-1PSID / SAPISID). "
            "Re-export a full youtube.com cookie dump while signed in."
        )
    if age_days >= 14:
        issues.append(
            f"Cookie file is {age_days:.0f} days old — YouTube sessions expire; export a fresh file."
        )
    elif age_days >= 7:
        issues.append(
            f"Cookie file is {age_days:.0f} days old — refresh if downloads keep failing."
        )

    # LOGIN_INFO is required in practice for bot checks (SID alone is not enough)
    usable = (
        bool(yt_rows)
        and has_login
        and has_sid
        and age_days < 21
        and (has_netscape_header or bool(yt_rows))
    )

    return {
        "present": True,
        "path": str(path),
        "size": path.stat().st_size,
        "age_days": round(age_days, 1),
        "youtube_rows": len(yt_rows),
        "has_login_info": has_login,
        "has_session_ids": has_sid,
        "usable": usable and not (age_days >= 21),
        "issues": issues,
    }


def _cookie_modes_for(platform: str) -> list[dict]:
    """
    Cookie configurations to try.

    For YouTube with a usable cookies.txt, prefer cookies first (matches the
    working VPS CLI). Cookieless is a fallback for public videos.
    """
    if platform != "youtube":
        modes: list[dict] = []
        cookies = settings.instagram_cookies_file
        if cookies and Path(cookies).is_file():
            modes.append({"cookiefile": cookies})
        modes.append({})
        return modes

    modes: list[dict] = []
    cookie_file = _youtube_cookies_file()
    report = inspect_youtube_cookies(cookie_file) if cookie_file else None
    # Only attach cookies when LOGIN_INFO is present — incomplete files worsen bot checks
    if cookie_file and report and report.get("usable"):
        modes.append({"cookiefile": str(cookie_file)})

    browser = _youtube_browser()
    if browser:
        modes.append({"cookiesfrombrowser": (browser,)})

    # Anonymous fallback (public videos; incomplete cookies intentionally skipped)
    modes.append({})

    seen: set[str] = set()
    unique: list[dict] = []
    for mode in modes:
        key = repr(sorted(mode.items()))
        if key not in seen:
            seen.add(key)
            unique.append(mode)
    return unique


def _node_version() -> tuple[int, int, int] | None:
    """Return (major, minor, patch) for `node`, or None if missing/unparseable."""
    node = shutil.which("node")
    if not node:
        return None
    try:
        import subprocess

        out = subprocess.run(
            [node, "-v"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        raw = (out.stdout or out.stderr or "").strip().lstrip("v")
        parts = raw.split(".")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2].split("-")[0]) if len(parts) > 2 else 0
        return major, minor, patch
    except Exception:
        return None


def _js_runtime_opts() -> dict:
    """
    Configure JS challenge solving for YouTube (EJS).

    yt-dlp-ejs requires Node >= 22 (or Deno >= 2.3). Older Node is ignored so
    we can fall back to remote components / other runtimes.
    """
    opts: dict = {}
    runtimes: dict = {}

    node_ver = _node_version()
    if node_ver and node_ver[0] >= 22:
        runtimes["node"] = {}
    elif shutil.which("deno"):
        runtimes["deno"] = {}
    elif node_ver:
        # Too old for ejs — still try; remote components may help on some builds
        runtimes["node"] = {}

    if runtimes:
        opts["js_runtimes"] = runtimes

    # Allow yt-dlp to fetch the challenge solver scripts (CLI: --remote-components ejs:github)
    opts["remote_components"] = {"ejs:github"}
    return opts


def _apply_youtube_runtime_options(ydl_opts: dict, platform: str) -> None:
    if platform != "youtube":
        return
    ydl_opts.update(_js_runtime_opts())

def _cookie_status_for(platform: str) -> str:
    if platform != "youtube":
        return ""

    parts: list[str] = []
    report = inspect_youtube_cookies()
    if report.get("present"):
        parts.append(
            f"Cookie file: {report.get('path')} "
            f"({report.get('size', 0)} bytes, {report.get('age_days', '?')} days old, "
            f"{report.get('youtube_rows', 0)} YouTube rows, "
            f"login={'yes' if report.get('has_login_info') else 'no'}, "
            f"session={'yes' if report.get('has_session_ids') else 'no'})."
        )
        for issue in report.get("issues") or []:
            parts.append(f"⚠ {issue}")
    else:
        configured = settings.youtube_cookies_file or settings.instagram_cookies_file
        if configured:
            parts.append(f"Configured cookie file missing: {configured}.")
        else:
            parts.append("No YOUTUBE_COOKIES_FILE is configured.")

    browser = _youtube_browser()
    if browser:
        parts.append(f"Browser cookie source: {browser}.")

    node_ver = _node_version()
    if not node_ver:
        parts.append(
            "Node.js is not on PATH. Install Node 22+ (required for YouTube n-challenge / EJS)."
        )
    elif node_ver[0] < 22:
        parts.append(
            f"Node.js v{node_ver[0]}.{node_ver[1]} is too old — yt-dlp EJS needs Node >= 22 "
            "(or Deno >= 2.3). Upgrade Node, then: pip install -U 'yt-dlp[default]' yt-dlp-ejs"
        )
    else:
        parts.append(f"Node.js v{node_ver[0]}.{node_ver[1]} OK for EJS.")

    return " ".join(parts)


def _format_selectors_for(platform: str, *, with_cookies: bool) -> list[str | None]:
    """Prefer progressive MP4; slightly different order with cookies."""
    if platform != "youtube":
        return ["best[ext=mp4]/best"]

    progressive = "best[ext=mp4][vcodec!=none][acodec!=none]/best[ext=mp4]/best"
    merged = (
        "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/"
        "bestvideo[height<=1080]+bestaudio/best[ext=mp4]/best"
    )
    if with_cookies:
        # Logged-in clients often expose dash/hls that need merge
        return [progressive, merged, "bestvideo+bestaudio/best", "best", None]
    return [progressive, merged, "best", None]


def _extractor_args_for(platform: str, *, with_cookies: bool) -> list[dict | None]:
    """
    Player clients ordered by likelihood of success.

    With cookies: tv_downgraded + web_safari (yt-dlp default for logged-in free accounts).
    Without: android_vr + web_safari (yt-dlp default for anonymous).
    Avoid plain `ios` (HTTP 400 on many builds).
    """
    if platform != "youtube":
        return [None]

    if with_cookies:
        return [
            # yt-dlp picks tv_downgraded,web_safari when it detects account cookies
            None,
            {"youtube": {"player_client": ["tv_downgraded", "web_safari"]}},
            {"youtube": {"player_client": ["mweb", "web_safari"]}},
            {"youtube": {"player_client": ["web", "web_safari"]}},
            {"youtube": {"player_client": ["tv", "web_embedded"]}},
            {"youtube": {"player_client": ["default"]}},
        ]

    return [
        None,
        {"youtube": {"player_client": ["android_vr", "web_safari"]}},
        {"youtube": {"player_client": ["mweb", "android_vr"]}},
        {"youtube": {"player_client": ["web_safari", "web"]}},
        {"youtube": {"player_client": ["web_embedded", "mweb"]}},
        {"youtube": {"player_client": ["android"]}},
    ]


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
        # Small pauses reduce YouTube rate-limit / bot scoring
        "sleep_interval_requests": 1,
        "sleep_interval": 1,
        "max_sleep_interval": 3,
    }

    if platform == "youtube":
        opts["http_headers"] = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://www.youtube.com",
            "Referer": "https://www.youtube.com/",
        }

    _apply_youtube_runtime_options(opts, platform)

    proxy = (getattr(settings, "youtube_proxy", None) or "").strip()
    if platform == "youtube" and proxy:
        opts["proxy"] = proxy

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
            report = inspect_youtube_cookies()
            raw = re.sub(r"\s+", " ", message).strip()
            if len(raw) > 220:
                raw = raw[:217] + "..."
            login_note = ""
            if report.get("present") and not report.get("has_login_info"):
                login_note = (
                    "CRITICAL: cookie file has NO LOGIN_INFO cookie — YouTube treats this "
                    "as logged-out/bot. Re-export while signed into youtube.com. "
                )
            return (
                "YouTube blocked this download (bot/sign-in check). "
                f"{login_note}"
                f"{_cookie_status_for(platform)} "
                "Export a NEW cookies.txt while signed into youtube.com "
                "(extension: Get cookies.txt LOCALLY), scp to the VPS, restart myinsta.service. "
                f"Raw yt-dlp error: {raw}"
            )

        if (
            "n challenge" in lower
            or "js interpreter" in lower
            or "ejs" in lower
            or "challenge solver" in lower
            or (
                "no video formats" in lower
                and ("challenge" in lower or "jsc" in lower or "signature" in lower)
            )
            or "no video formats found" in lower
        ):
            node_ver = _node_version()
            node_note = (
                f"Node is v{node_ver[0]}.{node_ver[1]} (need >= 22)."
                if node_ver and node_ver[0] < 22
                else (
                    "Node not found."
                    if not node_ver
                    else f"Node v{node_ver[0]} OK — enable remote EJS components."
                )
            )
            return (
                "YouTube JS challenge failed (n-challenge / no formats). "
                f"{node_note} "
                "On the VPS: install Node 22+, then "
                "pip install -U 'yt-dlp[default]' yt-dlp-ejs && "
                "sudo systemctl restart myinsta.service. "
                "CLI test: yt-dlp --js-runtimes node --remote-components ejs:github "
                "--cookies /path/to/youtube_cookies.txt -f 'best[ext=mp4]/best' URL"
            )

        if "requested format is not available" in lower:
            return (
                "YouTube did not provide a downloadable format for this video. "
                "Update yt-dlp (`pip install -U 'yt-dlp[default]'`), refresh cookies, "
                "and confirm the video is public (not members-only / region-locked)."
            )

        if "private video" in lower or "this video is private" in lower:
            return (
                "This YouTube video is private. Use cookies from an account that can "
                "watch it, or pick a public link."
            )

        if "video unavailable" in lower or "has been removed" in lower:
            return "This YouTube video is unavailable or was removed. Check the link."

        if "age" in lower and ("restrict" in lower or "confirm your age" in lower):
            return (
                "This video is age-restricted. Export cookies from a signed-in adult "
                "YouTube account, set YOUTUBE_COOKIES_FILE, and retry."
            )

        if "http error 403" in lower or re.search(r"\b403\b", lower):
            return (
                "YouTube returned HTTP 403 (forbidden). Refresh cookies, update yt-dlp, "
                "and try again. If cookies are old, export a fresh file."
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


def _resolve_output_path(
    info: dict, ydl: yt_dlp.YoutubeDL, output_dir: Path, video_id: int
) -> Path:
    """Find the real file after download (handles merge renames)."""
    requested = Path(ydl.prepare_filename(info))
    if requested.exists():
        return requested

    stem = output_dir / str(video_id)
    for ext in (".mp4", ".mkv", ".webm", ".m4a", ".mp3"):
        candidate = Path(str(stem) + ext)
        if candidate.exists():
            return candidate

    matches = sorted(
        p
        for p in output_dir.glob(f"{video_id}.*")
        if p.is_file() and p.suffix.lower() not in {".part", ".ytdl", ".temp"}
    )
    if matches:
        matches.sort(key=lambda p: p.stat().st_size, reverse=True)
        if matches[0].stat().st_size > 0:
            return matches[0]

    raise RuntimeError("Video download failed: output file not found")


def _attempt_download(
    url: str,
    output_dir: Path,
    video_id: int,
    platform: str,
    base_opts: dict,
    cookie_mode: dict,
    extractor_args: dict | None,
    selector: str | None,
) -> tuple[dict, Path]:
    current_opts = dict(base_opts)
    current_opts.update(cookie_mode)
    # Always re-apply EJS/runtime opts last so they are never dropped
    if platform == "youtube":
        current_opts.update(_js_runtime_opts())

    if extractor_args:
        current_opts["extractor_args"] = extractor_args
    else:
        current_opts.pop("extractor_args", None)

    if selector:
        current_opts["format"] = selector
    else:
        current_opts.pop("format", None)

    with yt_dlp.YoutubeDL(current_opts) as ydl:
        extracted = ydl.extract_info(url, download=True)
        if extracted is None:
            raise RuntimeError("no metadata returned")

        if extracted.get("_type") == "playlist" and extracted.get("entries"):
            extracted = next((e for e in extracted["entries"] if e), None)
            if extracted is None:
                raise RuntimeError("playlist contained no videos")

        _check_duration(extracted, platform)
        path = _resolve_output_path(extracted, ydl, output_dir, video_id)
        if path.stat().st_size <= 0:
            raise RuntimeError("downloaded file is empty")
        return extracted, path


def _youtube_cli_env() -> dict:
    """Build env so systemd can find node/ffmpeg like an interactive shell."""
    import os

    env = os.environ.copy()
    path_parts = env.get("PATH", "").split(os.pathsep)
    for extra in ("/usr/local/bin", "/usr/bin", "/bin"):
        if extra not in path_parts:
            path_parts.insert(0, extra)
    env["PATH"] = os.pathsep.join(path_parts)
    return env


def _download_youtube_via_cli(
    url: str, output_dir: Path, video_id: int, cookie_file: Path | None
) -> tuple[dict, Path]:
    """
    Download YouTube using the exact yt-dlp CLI flags proven on the VPS.

    Matches the working command:
      yt-dlp --js-runtimes node --remote-components ejs:github
             --cookies FILE -f "best[ext=mp4]/best" -o OUT URL
    """
    outtmpl = str((output_dir / f"{video_id}.%(ext)s").resolve())
    # Same format string as the successful manual VPS test
    fmt = "best[ext=mp4]/best"

    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--js-runtimes",
        "node",
        "--remote-components",
        "ejs:github",
        "-f",
        fmt,
        "--merge-output-format",
        "mp4",
        "--no-playlist",
        "--no-warnings",
        "-o",
        outtmpl,
    ]
    if cookie_file and cookie_file.is_file():
        cmd.extend(["--cookies", str(cookie_file)])

    proxy = (getattr(settings, "youtube_proxy", None) or "").strip()
    if proxy:
        cmd.extend(["--proxy", proxy])

    cmd.append(url)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
        env=_youtube_cli_env(),
        cwd=str(output_dir),
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "yt-dlp failed").strip()
        lines = [ln for ln in err.splitlines() if ln.strip()]
        detail = "\n".join(lines[-15:]) if lines else "yt-dlp failed"
        raise RuntimeError(detail)

    matches = sorted(
        p
        for p in output_dir.glob(f"{video_id}.*")
        if p.is_file() and p.suffix.lower() not in {".part", ".ytdl", ".temp", ".json"}
    )
    if not matches:
        raise RuntimeError(
            "yt-dlp CLI finished but output file not found. "
            f"stdout={ (result.stdout or '')[-200:] } stderr={ (result.stderr or '')[-200:] }"
        )
    matches.sort(key=lambda p: p.stat().st_size, reverse=True)
    path = matches[0]
    if path.stat().st_size <= 0:
        raise RuntimeError("downloaded file is empty")

    # Second lightweight call for metadata (no download)
    info: dict = {"title": None, "duration": None}
    meta_cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--js-runtimes",
        "node",
        "--remote-components",
        "ejs:github",
        "--skip-download",
        "--no-playlist",
        "-J",
    ]
    if cookie_file and cookie_file.is_file():
        meta_cmd.extend(["--cookies", str(cookie_file)])
    if proxy:
        meta_cmd.extend(["--proxy", proxy])
    meta_cmd.append(url)

    meta = subprocess.run(
        meta_cmd,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        env=_youtube_cli_env(),
    )
    if meta.returncode == 0 and meta.stdout.strip().startswith("{"):
        try:
            info = json.loads(meta.stdout)
        except json.JSONDecodeError:
            pass

    _check_duration(info, "youtube")
    return info, path


def _metadata_from_info(info: dict, platform: str, local_path: Path) -> dict:
    uploader_url = info.get("uploader_url") or info.get("channel_url") or None
    uploader_id = info.get("uploader_id") or info.get("channel_id") or None

    if not uploader_url and uploader_id and platform == "instagram":
        uploader_url = f"https://www.instagram.com/{uploader_id}/"

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


def download_video(
    url: str, output_dir: Path, video_id: int, platform: str = "instagram"
) -> dict:
    """Download a video with yt-dlp and return metadata plus local path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    url = _normalize_url(url, platform)
    output_template = str((output_dir / f"{video_id}.%(ext)s").resolve())

    # ── YouTube: CLI path first (proven on VPS with Node 22 + EJS + cookies) ──
    if platform == "youtube":
        last_cli_error: Exception | None = None
        cookie_file = _youtube_cookies_file()
        report = inspect_youtube_cookies(cookie_file) if cookie_file else None
        cookie_tries: list[Path | None] = []
        # Only use cookies that include LOGIN_INFO (usable)
        if cookie_file and report and report.get("usable"):
            cookie_tries.append(cookie_file)
        # Always try cookieless with EJS (public videos)
        cookie_tries.append(None)

        for cookies in cookie_tries:
            try:
                _clear_partial_downloads(output_dir, video_id)
                info, path = _download_youtube_via_cli(
                    url, output_dir, video_id, cookies
                )
                return _metadata_from_info(info, platform, path)
            except Exception as exc:
                last_cli_error = exc

        # Fall through to Python API as secondary path
        last_error: Exception | None = last_cli_error
    else:
        last_error = None

    base_opts = _base_ydl_opts(output_template, platform)
    local_path: Path | None = None
    info: dict | None = None

    cookie_modes = _cookie_modes_for(platform)

    # Fewer attempts for YouTube (CLI already tried the good path)
    max_attempts = 8 if platform == "youtube" else 18
    attempt_index = 0

    for cookie_mode in cookie_modes:
        with_cookies = bool(cookie_mode)
        extractor_modes = _extractor_args_for(platform, with_cookies=with_cookies)
        format_modes = _format_selectors_for(platform, with_cookies=with_cookies)

        for extractor_args in extractor_modes:
            for selector in format_modes:
                attempt_index += 1
                if attempt_index > max_attempts:
                    break
                try:
                    if attempt_index > 1:
                        _clear_partial_downloads(output_dir, video_id)
                    extracted, path = _attempt_download(
                        url,
                        output_dir,
                        video_id,
                        platform,
                        base_opts,
                        cookie_mode,
                        extractor_args,
                        selector,
                    )
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
        raise RuntimeError(
            _friendly_download_error(last_error or RuntimeError("unknown"), platform)
        ) from last_error

    return _metadata_from_info(info, platform, local_path)
