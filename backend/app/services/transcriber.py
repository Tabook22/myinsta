from pathlib import Path

from app.core.config import settings

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
