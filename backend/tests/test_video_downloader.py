from app.services import video_downloader
from app.services.video_downloader import _apply_cookie_options, _friendly_download_error


def test_youtube_cookie_error_is_actionable():
    message = _friendly_download_error(
        RuntimeError("Sign in to confirm you're not a bot. Use --cookies."),
        "youtube",
    )

    assert "YouTube blocked this download" in message
    assert "YOUTUBE_COOKIES_FILE" in message
    assert "YOUTUBE_COOKIES_FROM_BROWSER" in message


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
