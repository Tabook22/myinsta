"""
Optional video compression step.
Re-encodes large downloaded videos to H.264 + AAC at a lower bitrate,
reducing disk usage on the VPS while keeping acceptable quality.

Only activates when the source file exceeds SIZE_THRESHOLD_BYTES.
Replaces the original only when the compressed version is actually smaller.
Failure is silently ignored — the original file is always preserved.
"""
import subprocess
from pathlib import Path

# Only compress files larger than this (default 20 MB)
SIZE_THRESHOLD_BYTES = 20 * 1024 * 1024

# CRF 28 = good quality / significant size reduction for social-media source material
DEFAULT_CRF    = 28
DEFAULT_PRESET = "fast"


def compress_video(source: Path, *, crf: int = DEFAULT_CRF, preset: str = DEFAULT_PRESET) -> Path:
    """
    Re-encode *source* in-place if it exceeds the size threshold.
    Returns the (possibly replaced) video path.
    """
    try:
        if not source.exists() or source.stat().st_size < SIZE_THRESHOLD_BYTES:
            return source  # small enough — skip compression

        tmp = source.with_stem(source.stem + "_compressed")

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(source),
                "-c:v", "libx264",
                "-crf",    str(crf),
                "-preset", preset,
                "-c:a", "aac",
                "-b:a", "96k",
                "-movflags", "+faststart",  # web-optimised MP4
                str(tmp),
            ],
            check=True,
            capture_output=True,
        )

        if tmp.exists() and tmp.stat().st_size < source.stat().st_size:
            source.unlink()
            tmp.rename(source)
        else:
            # Compressed wasn't smaller — discard it
            if tmp.exists():
                tmp.unlink()

    except Exception:
        # Compression is optional — clean up temp file and move on
        tmp_candidate = source.with_stem(source.stem + "_compressed")
        if tmp_candidate.exists():
            tmp_candidate.unlink()

    return source
