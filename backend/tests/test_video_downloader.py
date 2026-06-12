from app.services import video_downloader
from app.services.video_downloader import (
    _apply_cookie_options,
    _extractor_args_for,
    _format_selectors_for,
    _friendly_download_error,
)


def test_youtube_cookie_error_is_actionable():
    message = _friendly_download_error(
        RuntimeError("Sign in to confirm you're not a bot. Use --cookies."),
        "youtube",
    )

    assert "YouTube blocked this download" in message
    assert "YOUTUBE_COOKIES_FILE" in message
    assert "fresh cookies.txt" in message


def test_youtube_format_error_is_actionable():
    message = _friendly_download_error(
        RuntimeError("Requested format is not available. Use --list-formats."),
        "youtube",
    )

    assert "downloadable media format" in message
    assert "updating yt-dlp" in message


def test_youtube_uses_multiple_format_selectors():
    selectors = _format_selectors_for("youtube")

    assert "bestvideo" in selectors[0]
    assert "bestaudio" in selectors[0]
    assert "best" in selectors
    assert selectors[-1] is None
    assert _format_selectors_for("instagram") == ["best[ext=mp4]/best"]


def test_youtube_uses_multiple_extractor_clients():
    args = _extractor_args_for("youtube")

    assert args[0]["youtube"]["player_client"] == ["android"]
    assert args[1]["youtube"]["player_client"] == ["ios"]
    assert args[-1] is None
    assert _extractor_args_for("instagram") == [None]


def test_youtube_cookie_file_setting_is_used(monkeypatch, tmp_path):
    cookies = tmp_path / "youtube_cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    monkeypatch.setattr(video_downloader.settings, "youtube_cookies_file", str(cookies))
    monkeypatch.setattr(video_downloader.settings, "youtube_cookies_from_browser", "")
    monkeypatch.setattr(video_downloader.settings, "instagram_cookies_file", "")

    ydl_opts = {}
    _apply_cookie_options(ydl_opts, "youtube")

    assert ydl_opts["cookiefile"] == str(cookies)


def test_youtube_browser_cookie_setting_wins(monkeypatch):
    monkeypatch.setattr(video_downloader.settings, "youtube_cookies_file", "/tmp/missing.txt")
    monkeypatch.setattr(video_downloader.settings, "youtube_cookies_from_browser", "chrome")
    monkeypatch.setattr(video_downloader.settings, "instagram_cookies_file", "")

    ydl_opts = {}
    _apply_cookie_options(ydl_opts, "youtube")

    assert ydl_opts["cookiesfrombrowser"] == ("chrome",)
    assert "cookiefile" not in ydl_opts
