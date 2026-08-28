"""App settings endpoints (private self-hosted use).

YouTube cookies are sensitive session credentials. Only use these endpoints
on a private MyInsta deploy you control — there is no multi-user auth yet.
"""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse, urljoin

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import settings
from app.services.video_downloader import inspect_youtube_cookies

try:
    from yt_dlp.cookies import extract_cookies_from_browser
except Exception:  # pragma: no cover - only happens when yt-dlp import is broken
    extract_cookies_from_browser = None

router = APIRouter(prefix="/settings", tags=["settings"])

# Cap upload size (~2 MiB is far more than a YouTube-only export needs)
_MAX_COOKIE_BYTES = 2 * 1024 * 1024
_SUPPORTED_BROWSERS = {"chrome", "edge", "firefox", "brave", "chromium"}


class YoutubeCookieExtractRequest(BaseModel):
    browser: Literal["chrome", "edge", "firefox", "brave", "chromium"] = "chrome"
    sync_remote: bool = True
    remote_api_base_url: str | None = None


def _youtube_cookie_target() -> Path:
    return settings.youtube_cookies_path


def _remote_cookie_url(remote_api_base_url: str) -> str:
    remote = remote_api_base_url.strip().rstrip("/")
    parsed = urlparse(remote)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(
            status_code=400,
            detail="Remote API URL must be a full http(s) URL.",
        )
    return urljoin(f"{remote}/", "api/settings/youtube-cookies")


def _save_youtube_cookie_text(text: str) -> dict:
    if not text.strip():
        raise HTTPException(status_code=400, detail="Empty file.")
    raw = text.encode("utf-8")
    if len(raw) > _MAX_COOKIE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({len(raw)} bytes). Max {_MAX_COOKIE_BYTES} bytes.",
        )

    if "youtube.com" not in text.lower():
        raise HTTPException(
            status_code=400,
            detail="File does not look like YouTube cookies (no youtube.com entries).",
        )

    # Write to a temp file in the target directory, inspect, then replace.
    target = _youtube_cookie_target()
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        prefix="youtube_cookies_",
        suffix=".txt",
        dir=str(target.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            if not text.endswith("\n"):
                fh.write("\n")

        report = inspect_youtube_cookies(tmp_path)
        if not report.get("has_login_info"):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Upload rejected: missing LOGIN_INFO cookie. "
                    "Export while signed into https://www.youtube.com "
                    "(Get cookies.txt LOCALLY on the YouTube tab), then try again."
                ),
            )
        if not report.get("has_session_ids"):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Upload rejected: missing session cookies (SID / __Secure-1PSID). "
                    "Re-export a full YouTube cookies dump while signed in."
                ),
            )

        os.replace(tmp_path, target)
        tmp_path = None

        try:
            os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)  # 600
        except OSError:
            pass

        return {
            "ok": True,
            "message": "YouTube cookies saved. You can retry a failed video now.",
            "path": str(target),
            "cookies": inspect_youtube_cookies(target),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not save cookies: {exc}") from exc
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


@router.get("/youtube-cookies")
def get_youtube_cookies_status() -> dict:
    """Return cookie health without exposing cookie values."""
    path = _youtube_cookie_target()
    report = inspect_youtube_cookies(path if path.is_file() else None)
    return {
        "path": str(path),
        "configured_env": settings.youtube_cookies_file or None,
        "remote_api_base_url": settings.youtube_cookie_sync_remote_url or None,
        "cookies": report,
        "hint": (
            "Export a Netscape cookies.txt from a browser signed into youtube.com "
            "(must include LOGIN_INFO), then upload it here. Prefer a small YouTube-only export."
        ),
    }


@router.post("/youtube-cookies")
async def upload_youtube_cookies(file: UploadFile = File(...)) -> dict:
    """
    Upload a Netscape cookies.txt for YouTube.

    Rejects files without LOGIN_INFO so incomplete exports cannot replace a good file.
    """
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(raw) > _MAX_COOKIE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({len(raw)} bytes). Max {_MAX_COOKIE_BYTES} bytes.",
        )

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="File must be UTF-8 text (Netscape cookies.txt).",
        ) from exc

    return _save_youtube_cookie_text(text)


@router.post("/youtube-cookies/extract")
def extract_youtube_cookies_from_local_browser(payload: YoutubeCookieExtractRequest) -> dict:
    """
    Extract YouTube cookies from a local browser, save them locally, and optionally
    forward the validated cookies to a remote MyInsta API.

    Cookie contents are never returned to the browser.
    """
    if extract_cookies_from_browser is None:
        raise HTTPException(status_code=500, detail="yt-dlp cookie extraction is not available.")
    if payload.browser not in _SUPPORTED_BROWSERS:
        raise HTTPException(status_code=400, detail="Unsupported browser.")

    target = _youtube_cookie_target()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f"youtube_cookies_from_{payload.browser}_",
        suffix=".txt",
        dir=str(target.parent),
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        try:
            cookie_jar = extract_cookies_from_browser(payload.browser)
            cookie_jar.save(str(tmp_path), ignore_discard=True, ignore_expires=True)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Could not extract cookies from {payload.browser}. "
                    "Make sure you are signed into youtube.com, close private windows, "
                    "and try again. If the browser blocks access, use manual cookies.txt upload."
                ),
            ) from exc

        text = tmp_path.read_text(encoding="utf-8")
        local = _save_youtube_cookie_text(text)
        response = {
            **local,
            "source_browser": payload.browser,
            "remote": None,
        }

        if payload.sync_remote:
            import httpx

            remote_base = payload.remote_api_base_url or settings.youtube_cookie_sync_remote_url
            if not remote_base:
                raise HTTPException(status_code=400, detail="Remote API URL is not configured.")
            remote_url = _remote_cookie_url(remote_base)
            try:
                with httpx.Client(timeout=60.0) as client:
                    remote_response = client.post(
                        remote_url,
                        files={"file": ("youtube_cookies.txt", text.encode("utf-8"), "text/plain")},
                    )
            except httpx.HTTPError as exc:
                raise HTTPException(
                    status_code=502,
                    detail=f"Cookies saved locally, but could not reach the remote MyInsta API: {exc}",
                ) from exc

            if remote_response.status_code >= 400:
                detail = remote_response.text
                try:
                    detail = remote_response.json().get("detail", detail)
                except ValueError:
                    pass
                raise HTTPException(
                    status_code=502,
                    detail=f"Cookies saved locally, but the remote MyInsta API rejected them: {detail}",
                )

            response["remote"] = remote_response.json()
            response["message"] = "YouTube cookies saved locally and sent to the VPS. Retry the YouTube video now."

        return response
    finally:
        tmp_path.unlink(missing_ok=True)


@router.delete("/youtube-cookies")
def delete_youtube_cookies() -> dict:
    """Remove the stored YouTube cookies file (optional cleanup)."""
    path = _youtube_cookie_target()
    if path.is_file():
        path.unlink()
    return {
        "ok": True,
        "message": "YouTube cookies file removed.",
        "path": str(path),
        "cookies": inspect_youtube_cookies(None),
    }
