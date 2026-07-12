from pathlib import Path

from app.services import video_downloader
from app.services.video_downloader import (
    _apply_youtube_runtime_options,
    _check_duration,
    _cookie_modes_for,
    _extractor_args_for,
    _format_selectors_for,
    _friendly_download_error,
    _normalize_url,
    inspect_youtube_cookies,
)


def test_youtube_cookie_error_is_actionable():
    message = _friendly_download_error(
        RuntimeError("Sign in to confirm you're not a bot. Use --cookies."),
        "youtube",
    )

    assert "YouTube blocked this download" in message
    assert "YOUTUBE_COOKIES_FILE" in message or "cookies.txt" in message.lower()
    assert "fresh" in message.lower() or "NEW" in message or "export" in message.lower()


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
    selectors = _format_selectors_for("youtube", with_cookies=False)

    assert "best[ext=mp4]" in selectors[0]
    assert "bestvideo" in selectors[1]
    assert selectors[-1] is None
    assert _format_selectors_for("instagram", with_cookies=False) == ["best[ext=mp4]/best"]


def test_youtube_cookie_clients_prefer_tv_web():
    args = _extractor_args_for("youtube", with_cookies=True)
    assert args[0] is None
    serialized = repr(args)
    assert "tv_downgraded" in serialized or "web_safari" in serialized
    assert "['ios']" not in serialized


def test_youtube_anonymous_clients_prefer_android_vr():
    args = _extractor_args_for("youtube", with_cookies=False)
    serialized = repr(args)
    assert "android_vr" in serialized or args[0] is None
    assert "['ios']" not in serialized


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


def test_youtube_tries_cookieless_before_cookie_file(monkeypatch, tmp_path):
    cookies = tmp_path / "youtube_cookies.txt"
    cookies.write_text(
        "# Netscape HTTP Cookie File\n"
        ".youtube.com\tTRUE\t/\tTRUE\t1893456000\tLOGIN_INFO\tabc\n"
        ".youtube.com\tTRUE\t/\tTRUE\t1893456000\tSID\txyz\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(video_downloader.settings, "youtube_cookies_file", str(cookies))
    monkeypatch.setattr(video_downloader.settings, "youtube_cookies_from_browser", "")
    monkeypatch.setattr(video_downloader.settings, "instagram_cookies_file", "")

    modes = _cookie_modes_for("youtube")
    assert modes[0] == {}
    assert any(m.get("cookiefile") == str(cookies) for m in modes)


def test_inspect_youtube_cookies_detects_login(tmp_path):
    cookies = tmp_path / "youtube_cookies.txt"
    cookies.write_text(
        "# Netscape HTTP Cookie File\n"
        ".youtube.com\tTRUE\t/\tTRUE\t1893456000\tLOGIN_INFO\tabc\n"
        ".youtube.com\tTRUE\t/\tTRUE\t1893456000\t__Secure-1PSID\txyz\n",
        encoding="utf-8",
    )
    report = inspect_youtube_cookies(cookies)
    assert report["present"] is True
    assert report["has_login_info"] is True
    assert report["has_session_ids"] is True
    assert report["youtube_rows"] >= 2


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
