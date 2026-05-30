import shutil
import subprocess
from pathlib import Path


def _run_ffmpeg(cmd: list[str], label: str) -> None:
    """Run an ffmpeg command and raise RuntimeError on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown error").strip()
        raise RuntimeError(f"FFmpeg {label} failed: {detail}")


def _check_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "FFmpeg is not installed or not on PATH. Install FFmpeg and try again."
        )


def extract_audio(video_path: Path, audio_dir: Path) -> Path:
    """Extract mono 16 kHz WAV — used by Whisper for transcription."""
    _check_ffmpeg()
    audio_dir.mkdir(parents=True, exist_ok=True)
    output_path = audio_dir / f"{video_path.stem}.wav"

    _run_ffmpeg([
        "ffmpeg", "-y", "-i", str(video_path),
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
        str(output_path),
    ], "WAV extraction")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("FFmpeg audio extraction failed: output file missing or empty")

    return output_path.resolve()


def extract_audio_mp3(video_path: Path, audio_dir: Path) -> Path:
    """Extract high-quality stereo MP3 (192 kbps) for playback and download."""
    _check_ffmpeg()
    audio_dir.mkdir(parents=True, exist_ok=True)
    output_path = audio_dir / f"{video_path.stem}.mp3"

    _run_ffmpeg([
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn",                   # drop video stream
        "-ar", "44100",          # standard sample rate
        "-ac", "2",              # stereo
        "-b:a", "192k",          # 192 kbps quality
        "-codec:a", "libmp3lame",
        str(output_path),
    ], "MP3 extraction")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("FFmpeg MP3 extraction failed: output file missing or empty")

    return output_path.resolve()
