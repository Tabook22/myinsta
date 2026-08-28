from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import settings as settings_routes


@pytest.fixture()
def client(tmp_path, monkeypatch):
    cookies_path = tmp_path / "youtube_cookies.txt"
    monkeypatch.setattr(
        "app.core.config.settings.youtube_cookies_file",
        str(cookies_path),
    )
    # Invalidate cached_property if any — youtube_cookies_path is a property
    return TestClient(app), cookies_path


def _good_cookies() -> bytes:
    return (
        b"# Netscape HTTP Cookie File\n"
        b".youtube.com\tTRUE\t/\tTRUE\t1893456000\tLOGIN_INFO\tabc\n"
        b".youtube.com\tTRUE\t/\tTRUE\t1893456000\tSID\txyz\n"
        b".youtube.com\tTRUE\t/\tTRUE\t1893456000\t__Secure-1PSID\tpsid\n"
    )


def test_upload_rejects_missing_login_info(client):
    api, path = client
    bad = (
        b"# Netscape HTTP Cookie File\n"
        b".youtube.com\tTRUE\t/\tTRUE\t1893456000\tSID\tonly\n"
    )
    response = api.post(
        "/api/settings/youtube-cookies",
        files={"file": ("cookies.txt", bad, "text/plain")},
    )
    assert response.status_code == 400
    assert "LOGIN_INFO" in response.json()["detail"]
    assert not path.exists()


def test_upload_saves_good_cookies(client):
    api, path = client
    response = api.post(
        "/api/settings/youtube-cookies",
        files={"file": ("cookies.txt", _good_cookies(), "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["cookies"]["has_login_info"] is True
    assert body["cookies"]["usable"] is True
    assert path.is_file()
    assert "LOGIN_INFO" in path.read_text(encoding="utf-8")

    status = api.get("/api/settings/youtube-cookies")
    assert status.status_code == 200
    assert status.json()["cookies"]["usable"] is True


def test_extract_from_browser_saves_good_cookies(client, monkeypatch):
    api, path = client

    class FakeCookieJar:
        def save(self, filename=None, ignore_discard=True, ignore_expires=True):
            Path(filename).write_bytes(_good_cookies())

    monkeypatch.setattr(
        settings_routes,
        "extract_cookies_from_browser",
        lambda browser: FakeCookieJar(),
    )

    response = api.post(
        "/api/settings/youtube-cookies/extract",
        json={"browser": "chrome", "sync_remote": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["source_browser"] == "chrome"
    assert body["remote"] is None
    assert body["cookies"]["usable"] is True
    assert path.is_file()
    assert "LOGIN_INFO" in path.read_text(encoding="utf-8")


def test_extract_from_browser_rejects_missing_login_info(client, monkeypatch):
    api, path = client

    class FakeCookieJar:
        def save(self, filename=None, ignore_discard=True, ignore_expires=True):
            Path(filename).write_text(
                "# Netscape HTTP Cookie File\n"
                ".youtube.com\tTRUE\t/\tTRUE\t1893456000\tSID\tonly\n",
                encoding="utf-8",
            )

    monkeypatch.setattr(
        settings_routes,
        "extract_cookies_from_browser",
        lambda browser: FakeCookieJar(),
    )

    response = api.post(
        "/api/settings/youtube-cookies/extract",
        json={"browser": "chrome", "sync_remote": False},
    )

    assert response.status_code == 400
    assert "LOGIN_INFO" in response.json()["detail"]
    assert not path.exists()
