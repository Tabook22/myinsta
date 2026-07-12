from app.services import video_downloader
from app.services.video_downloader import (
    _apply_youtube_runtime_options,
    _check_duration,
    _cookie_modes_for,
    _extractor_args_for,
    _format_selectors_for,
    _friendly_download_error,
    _normalize_url,
)


def test_youtube_cookie_error_is_actionable():
    message = _friendly_download_error(
        RuntimeError("Sign in to confirm you're not a bot. Use --cookies."),
        "youtube",
    )

    assert "YouTube blocked this download" in message
    assert "YOUTUBE_COOKIES_FILE" in message
    assert "cookies.txt" in message.lower()


def test_youtube_format_error_is_actionable():
    message = _friendly_download_error(
        RuntimeError("Requested format is not available. Use --list-formats."),
        "youtube",
    )

    assert "downloadable format" in message
    assert "yt-dlp" in message


def test_youtube_403_error_is_actionable():
    message = _friendly_download_error(RuntimeError("HTTP Error 403: Forbidden"), "youtube")
    assert "403" in message
    assert "cookies" in message.lower()


def test_youtube_uses_progressive_format_first():
    selectors = _format_selectors_for("youtube")

    assert "best[ext=mp4]" in selectors[0]
    assert "bestvideo" in selectors[1]
    assert selectors[-1] is None
    assert _format_selectors_for("instagram") == ["best[ext=mp4]/best"]


def test_youtube_uses_modern_extractor_clients():
    args = _extractor_args_for("youtube")

    # First attempt: yt-dlp defaults
    assert args[0] is None
    # Must include modern clients, not legacy ios-only
    serialized = repr(args)
    assert "android_vr" in serialized or "default" in serialized
    assert "web_safari" in serialized or "mweb" in serialized
    assert "['ios']" not in serialized
    assert _extractor_args_for("instagram") == [None]


def test_youtube_enables_node_runtime_when_available(monkeypatch):
    monkeypatch.setattr(video_downloader.shutil, "which", lambda name: "/usr/bin/node")
    ydl_opts = {}
    _apply_youtube_runtime_options(ydl_opts, "youtube")

    assert ydl_opts["js_runtimes"] == {"node": {}}
    assert "remote_components" in ydl_opts


def test_instagram_does_not_set_js_runtime():
    ydl_opts = {}
    _apply_youtube_runtime_options(ydl_opts, "instagram")

    assert "js_runtimes" not in ydl_opts


def test_zero_youtube_duration_limit_allows_long_videos(monkeypatch):
    monkeypatch.setattr(video_downloader.settings, "max_youtube_duration_seconds", 0)

    _check_duration({"duration": 7200}, "youtube")


def test_configured_youtube_duration_limit_blocks_long_videos(monkeypatch):
    monkeypatch.setattr(video_downloader.settings, "max_youtube_duration_seconds", 1800)

    try:
        _check_duration({"duration": 7200}, "youtube")
    except RuntimeError as exc:
        assert "longer than 30 minutes" in str(exc)
    else:
        raise AssertionError("Expected long video to be rejected")


def test_youtube_cookie_file_setting_is_used(monkeypatch, tmp_path):
    cookies = tmp_path / "youtube_cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n" + ("x" * 40), encoding="utf-8")
    monkeypatch.setattr(video_downloader.settings, "youtube_cookies_file", str(cookies))
    monkeypatch.setattr(video_downloader.settings, "youtube_cookies_from_browser", "")
    monkeypatch.setattr(video_downloader.settings, "instagram_cookies_file", "")

    modes = _cookie_modes_for("youtube")
    assert any(m.get("cookiefile") == str(cookies) for m in modes)
    assert modes[-1] == {}


def test_youtube_browser_cookie_mode_is_available(monkeypatch, tmp_path):
    cookies = tmp_path / "youtube_cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n" + ("x" * 40), encoding="utf-8")
    monkeypatch.setattr(video_downloader.settings, "youtube_cookies_file", str(cookies))
    monkeypatch.setattr(video_downloader.settings, "youtube_cookies_from_browser", "chrome")
    monkeypatch.setattr(video_downloader.settings, "instagram_cookies_file", "")

    modes = _cookie_modes_for("youtube")
    assert any(m.get("cookiefile") == str(cookies) for m in modes)
    assert any(m.get("cookiesfrombrowser") == ("chrome",) for m in modes)


def test_normalize_youtube_short_urls():
    assert (
        _normalize_url("https://youtu.be/dQw4w9WgXcQ", "youtube")
        == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )
    assert (
        _normalize_url("https://www.youtube.com/shorts/abc123XYZ", "youtube")
        == "https://www.youtube.com/watch?v=abc123XYZ"
    )
    assert (
        _normalize_url("https://www.youtube.com/watch?v=abc123XYZ&t=10s", "youtube")
        == "https://www.youtube.com/watch?v=abc123XYZ"
    )
