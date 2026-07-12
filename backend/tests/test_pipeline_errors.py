from app.services.pipeline_errors import friendly_pipeline_error


def test_ffmpeg_missing_message_passthrough():
    msg = friendly_pipeline_error(
        RuntimeError("FFmpeg is not installed or not on PATH. Install FFmpeg and try again.")
    )
    assert "FFmpeg is not installed" in msg


def test_ffmpeg_extraction_maps_invalid_media():
    msg = friendly_pipeline_error(
        RuntimeError("FFmpeg WAV extraction failed: Invalid data found when processing input")
    )
    assert msg.startswith("Audio extraction failed")
    assert "audio track" in msg.lower() or "invalid data" in msg.lower()


def test_youtube_cookie_message_passthrough():
    original = (
        "YouTube blocked this download because it needs browser cookies. "
        "Export a fresh cookies.txt."
    )
    assert friendly_pipeline_error(RuntimeError(original)) == original


def test_download_private_video():
    msg = friendly_pipeline_error(RuntimeError("Video download failed: Private video"))
    assert "private" in msg.lower() or "login" in msg.lower()


def test_whisper_oom():
    msg = friendly_pipeline_error(RuntimeError("CUDA out of memory during transcription"))
    assert "memory" in msg.lower()


def test_generic_fallback_trims_long_message():
    long = "x" * 500
    msg = friendly_pipeline_error(RuntimeError(long))
    assert len(msg) <= 240
