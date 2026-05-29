import shutil
import subprocess
from pathlib import Path


def extract_audio(video_path: Path, audio_dir: Path) -> Path:
    """Extract mono 16 kHz WAV audio with FFmpeg."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "FFmpeg is not installed or not on PATH. Install FFmpeg and try again."
        )

    audio_dir.mkdir(parents=True, exist_ok=True)
    output_path = audio_dir / f"{video_path.stem}.wav"

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown error").strip()
        raise RuntimeError(f"FFmpeg audio extraction failed: {detail}")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("FFmpeg audio extraction failed: output file missing or empty")

    return output_path.resolve()
