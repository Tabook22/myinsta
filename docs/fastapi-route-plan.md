# FastAPI Route Plan

## `GET /health`

Purpose: verify the backend is running.

Response:

```json
{ "status": "ok" }
```

## `POST /api/videos`

Purpose: submit an Instagram or YouTube video URL and start processing.

Request:

```json
{ "url": "https://www.youtube.com/watch?v=..." }
```

Prototype behavior:

1. Validate URL with Pydantic.
2. Detect the supported source platform and insert a row into `videos` with
   `status = processing`.
3. Start processing in a FastAPI `BackgroundTasks` job.
4. Return the video record.

Later processing steps:

1. Download video with yt-dlp.
2. Save metadata and video path.
3. Extract audio with FFmpeg.
4. Transcribe with Whisper.
5. Save transcript.
6. Mark video `ready` or `failed`.

## `GET /api/videos`

Purpose: list recent submitted videos.

Response: array of video records without transcript details by default.

## `GET /api/videos/{video_id}`

Purpose: fetch one video and its transcript if available.

Response includes:

- metadata
- status
- error message if failed
- transcript object if ready

## `POST /api/videos/{video_id}/chat`

Purpose: chat with a video transcript.

Current behavior: save the user message, answer from the transcript or web mode,
and optionally return the answer in English, Arabic, or bilingual mode with
`answer_language`.

Future RAG behavior:

1. Save user message.
2. Retrieve relevant transcript chunks.
3. Send prompt + chunks to an LLM.
4. Save assistant response.
5. Return answer with citations/timestamps.

## `POST /api/videos/{video_id}/translate`

Purpose: translate a ready transcript to Arabic.

Behavior:

1. Fetch the saved transcript for the video.
2. Return cached Arabic text if it already exists.
3. Translate the transcript to Arabic on demand.
4. Save the Arabic translation on the transcript row.
5. Return `video_id`, `target_language`, and `translated_text`.

## `POST /api/videos/{video_id}/cleanup`

Purpose: clean a ready transcript into more readable text.

Query:

```text
target_language=en | ar
```

Behavior:

1. Fetch the saved transcript and Whisper segments.
2. Return cached cleaned text if it already exists.
3. Remove immediate repeated words/phrases.
4. Add simple punctuation and paragraph breaks.
5. Preserve speaker labels when segment metadata includes them.
6. For `target_language=ar`, translate the cleaned text to Arabic.
7. Save the cleaned English or cleaned Arabic text on the transcript row.
