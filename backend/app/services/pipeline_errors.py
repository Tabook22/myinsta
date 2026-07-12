"""Map raw pipeline exceptions to short, user-facing failure messages."""

from __future__ import annotations


def _first_useful_line(text: str, max_len: int = 240) -> str:
    """Pick the first non-empty line and trim it for display."""
    for line in (text or "").splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned[:max_len]
    return (text or "").strip()[:max_len]


def friendly_pipeline_error(exc: Exception) -> str:
    """Convert download / FFmpeg / Whisper failures into readable messages."""
    message = str(exc).strip() or exc.__class__.__name__
    lower = message.lower()

    # Already-friendly messages from download / dependency checks.
    if message.startswith("YouTube blocked") or message.startswith("YouTube did not provide"):
        return message
    if message.startswith("YouTube videos longer than"):
        return message
    if "ffmpeg is not installed" in lower:
        return message
    if "whisper is not installed" in lower:
        return message

    # yt-dlp / download
    if "video download failed" in lower or "download failed" in lower:
        if "private" in lower or "login required" in lower:
            return (
                "This video is private or requires login. "
                "If it is your account content, configure cookies and try again."
            )
        if "not available" in lower or "removed" in lower or "404" in lower:
            return "This video is unavailable or was removed. Check the link and try again."
        if "unsupported url" in lower or "no video formats" in lower:
            return "Could not find a downloadable video at this URL. Confirm it is a public Reel, Post, or YouTube video."
        detail = _first_useful_line(message.replace("Video download failed:", "").strip())
        return f"Download failed: {detail}" if detail else "Download failed. Check the link and try again."

    # FFmpeg
    if "ffmpeg" in lower:
        if "not found" in lower or "no such file" in lower:
            return "Audio extraction failed because the downloaded video file is missing or unreadable."
        if "invalid data" in lower or "does not contain any stream" in lower:
            return "Audio extraction failed: the file has no usable audio track."
        detail = _first_useful_line(message)
        return f"Audio extraction failed: {detail}"

    # Whisper / transcription
    if "whisper" in lower or "transcrib" in lower or "cuda" in lower or "out of memory" in lower:
        if "out of memory" in lower or "cuda" in lower:
            return "Transcription failed due to limited memory. Try a shorter video or a smaller Whisper model."
        detail = _first_useful_line(message)
        return f"Transcription failed: {detail}"

    # Library / disk
    if "permission denied" in lower or "no space" in lower or "disk" in lower:
        return f"Could not save processed files: {_first_useful_line(message)}"

    return _first_useful_line(message) or "Processing failed for an unknown reason."
