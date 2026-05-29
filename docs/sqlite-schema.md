# SQLite Database Schema

Source of truth: `backend/app/db/schema.sql`

## Tables

### `videos`

One row per submitted Instagram URL.

Important columns:

- `id`: primary key
- `source_url`: original user-submitted URL
- `platform`: defaults to `instagram`
- `title`, `description`, `uploader`, `duration_seconds`, `thumbnail_url`: metadata from yt-dlp
- `local_video_path`: downloaded video path
- `local_audio_path`: extracted audio path
- `status`: `queued`, `processing`, `ready`, or `failed`
- `error_message`: failure details for debugging
- `created_at`, `updated_at`: timestamps

### `transcripts`

One transcript per video.

Important columns:

- `video_id`: unique foreign key to `videos.id`
- `language`: detected language from Whisper
- `full_text`: complete transcript
- `segments_json`: JSON array of timestamped Whisper segments

### `chat_messages`

Future chat history for each video.

Important columns:

- `video_id`: foreign key to `videos.id`
- `role`: `user` or `assistant`
- `content`: message text
- `created_at`: timestamp

## Why this is enough for v1

This schema supports the full local prototype without auth, users, embeddings, or external storage. Add transcript chunks and embedding tables later when RAG is implemented.
