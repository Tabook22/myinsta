from functools import cached_property
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_path: str = "./data/myinsta.sqlite3"
    download_dir: str = "./data/downloads"
    audio_dir: str = "./data/audio"
    library_dir: str = "./data/library"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    whisper_model: str = "base"
    brave_search_api_key: str = ""   # Get free key at brave.com/search/api/
    max_youtube_duration_seconds: int = 1800
    instagram_cookies_file: str = Field(default="", alias="INSTAGRAM_COOKIES_FILE")
    youtube_cookies_file: str = Field(default="", alias="YOUTUBE_COOKIES_FILE")
    youtube_cookies_from_browser: str = Field(default="", alias="YOUTUBE_COOKIES_FROM_BROWSER")

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


settings = Settings()
