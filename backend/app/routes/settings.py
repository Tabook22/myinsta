"""App settings endpoints (private self-hosted use).

YouTube cookies are sensitive session credentials. Only use these endpoints
on a private MyInsta deploy you control — there is no multi-user auth yet.
"""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.services.video_downloader import inspect_youtube_cookies

router = APIRouter(prefix="/settings", tags=["settings"])

# Cap upload size (~2 MiB is far more than a YouTube-only export needs)
_MAX_COOKIE_BYTES = 2 * 1024 * 1024


def _youtube_cookie_target() -> Path:
    return settings.youtube_cookies_path


@router.get("/youtube-cookies")
def get_youtube_cookies_status() -> dict:
    """Return cookie health without exposing cookie values."""
    path = _youtube_cookie_target()
    report = inspect_youtube_cookies(path if path.is_file() else None)
    return {
        "path": str(path),
        "configured_env": settings.youtube_cookies_file or None,
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

    if "youtube.com" not in text.lower():
        raise HTTPException(
            status_code=400,
            detail="File does not look like YouTube cookies (no youtube.com entries).",
        )

    # Write to a temp file in the target directory, inspect, then replace
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

        # Atomic replace
        os.replace(tmp_path, target)
        tmp_path = None  # noqa: do not unlink after move

        try:
            os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)  # 600
        except OSError:
            pass

        final = inspect_youtube_cookies(target)
        return {
            "ok": True,
            "message": "YouTube cookies saved. You can retry a failed video now.",
            "path": str(target),
            "cookies": final,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not save cookies: {exc}") from exc
    finally:
        if tmp_path is not None and tmp_path.exists():
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
