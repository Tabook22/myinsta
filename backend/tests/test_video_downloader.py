from app.services.video_downloader import _friendly_download_error


def test_youtube_cookie_error_is_actionable():
    message = _friendly_download_error(
        RuntimeError("Sign in to confirm you're not a bot. Use --cookies."),
        "youtube",
    )

    assert "YouTube blocked this download" in message
    assert "YOUTUBE_COOKIES_FILE" in message
    assert "YOUTUBE_COOKIES_FROM_BROWSER" in message
