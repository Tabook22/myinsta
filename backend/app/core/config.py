from functools import cached_property
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_path: str = "./data/myinsta.sqlite3"
    download_dir: str = "./data/downloads"
    audio_dir: str = "./data/audio"
    library_dir: str = "./data/library"
    wiki_dir: str = "./data/mywiki"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    whisper_model: str = "base"
    brave_search_api_key: str = ""   # Get free key at brave.com/search/api/
    max_youtube_duration_seconds: int = 0
    instagram_cookies_file: str = Field(default="", alias="INSTAGRAM_COOKIES_FILE")
    youtube_cookies_file: str = Field(default="", alias="YOUTUBE_COOKIES_FILE")
    youtube_cookies_from_browser: str = Field(default="", alias="YOUTUBE_COOKIES_FROM_BROWSER")
    # Optional HTTP(S) proxy for YouTube only, e.g. http://user:pass@host:port
    youtube_proxy: str = Field(default="", alias="YOUTUBE_PROXY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MYINSTA_",
        extra="ignore",
        populate_by_name=True,
    )

    @cached_property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @cached_property
    def database_file(self) -> Path:
        return Path(self.database_path)

    @cached_property
    def download_path(self) -> Path:
        return Path(self.download_dir)

    @cached_property
    def audio_path(self) -> Path:
        return Path(self.audio_dir)

    @cached_property
    def library_path(self) -> Path:
        return Path(self.library_dir)

    @cached_property
    def wiki_path(self) -> Path:
        return Path(self.wiki_dir)

    @property
    def youtube_cookies_path(self) -> Path:
        """Resolved path for the YouTube cookies.txt file (upload target)."""
        if self.youtube_cookies_file.strip():
            return Path(self.youtube_cookies_file).expanduser()
        # Default app-managed location (gitignored under data/)
        return Path(self.download_dir).resolve().parent / "youtube_cookies.txt"


settings = Settings()
