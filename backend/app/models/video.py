from typing import Any, Literal

from pydantic import BaseModel, HttpUrl


VideoStatus = Literal["queued", "processing", "ready", "failed"]
ContentType = Literal["speech", "music", "unknown"]
ChatMode = Literal["transcript", "web"]


class VideoCreateRequest(BaseModel):
    url: HttpUrl


class VideoUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    transcript_text: str | None = None
    notes: str | None = None


class TranscriptResponse(BaseModel):
    language: str | None = None
    full_text: str = ""
    segments: list[dict[str, Any]] | None = None


class VideoResponse(BaseModel):
    id: int
    source_url: str
    platform: str
    title: str | None = None
    description: str | None = None
    uploader: str | None = None
    duration_seconds: float | None = None
    thumbnail_url: str | None = None
    storage_stamp: str | None = None
    storage_folder: str | None = None
    status: VideoStatus
    content_type: ContentType = "unknown"
    creator_url: str | None = None
    error_message: str | None = None
    video_url: str | None = None
    audio_url: str | None = None
    notes: str | None = None
    transcript: TranscriptResponse | None = None
    created_at: str
    updated_at: str


class ChatRequest(BaseModel):
    message: str
    mode: ChatMode = "transcript"


class ChatMessageResponse(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: str


class ChatResponse(BaseModel):
    video_id: int
    answer: str
    message: ChatMessageResponse


class ChatHistoryResponse(BaseModel):
    video_id: int
    messages: list[ChatMessageResponse]
