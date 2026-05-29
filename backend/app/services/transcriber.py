import re
from pathlib import Path

from app.core.config import settings

# Whisper outputs these tags when it hears music/noise instead of speech
_MUSIC_ONLY_PATTERN = re.compile(
    r"^[\s\[\]()*♪🎵🎶,.\-–—]*"
    r"(music|applause|singing|instrumental|no speech|background music|"
    r"silence|ambient|noise|drums|guitar|piano|beat|melody|song|track)"
    r"[\s\[\]()*♪,.\-–—]*$",
    re.IGNORECASE,
)


def detect_content_type(full_text: str, duration_seconds: float | None = None) -> str:
    """Return 'speech', 'music', or 'unknown' based on Whisper transcript.

    Rules applied in order:
    1. Empty transcript for a video > 10 s   → music
    2. Text matches known music/noise Whisper tags → music
    3. Fewer than 8 words AND video > 30 s   → music (sparse transcript = noise)
    4. Otherwise                             → speech
    """
    text = (full_text or "").strip()
    duration = duration_seconds or 0

    if not text:
        return "music" if duration > 10 else "unknown"

    if _MUSIC_ONLY_PATTERN.match(text):
        return "music"

    word_count = len(text.split())
    if word_count < 8 and duration > 30:
        return "music"

    return "speech"

_model = None


def _get_model():
    global _model

    try:
        import whisper
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Whisper is not installed on this server. "
            "Install openai-whisper before using transcription."
        ) from exc

    if _model is None:
        _model = whisper.load_model(settings.whisper_model)

    return _model


def transcribe_audio(audio_path: Path) -> dict:
    """Transcribe an audio file with Whisper."""
    model = _get_model()
    result = model.transcribe(str(audio_path), fp16=False)

    segments = []
    for segment in result.get("segments") or []:
        segments.append(
            {
                "id": segment.get("id"),
                "start": segment.get("start"),
                "end": segment.get("end"),
                "text": segment.get("text"),
            }
        )

    return {
        "language": result.get("language"),
        "full_text": (result.get("text") or "").strip(),
        "segments": segments,
    }
