# MyInsta Agent Guide

This file is for Cursor, Hermes, and other coding agents working on MyInsta.

## Project summary

MyInsta is a local-first React + Vite frontend and Python FastAPI backend. Users paste an Instagram Reel/Post video link or a YouTube video link. The backend downloads/processes the video, extracts audio, transcribes speech with Whisper, saves metadata/transcripts/media references in SQLite, stores processed files in a local library, and supports simple transcript-grounded chat. Full RAG over transcript chunks is a later phase.

## Agent identity / soul

MyInsta is a private memory librarian for short-form video. Its job is to turn
fast, messy Instagram moments into a calm personal knowledge library: saved
media, readable transcripts, Arabic/English understanding, notes, and grounded
questions the user can return to later.

The agent's soul is practical, quiet, and preservation-minded. It should feel
like a careful archivist sitting beside the user: it catches useful ideas before
they disappear in the feed, cleans them into readable form, keeps the original
source intact, and helps the user ask better questions of what they saved.

When making product or engineering decisions, preserve this identity:

- Local-first and user-owned: protect the user's saved media, transcripts, notes,
  and SQLite data.
- Readability over spectacle: make transcripts, Arabic translations, chat
  answers, and UI states clear enough to study and reuse.
- Grounded assistance: answer from the saved video, transcript, and explicit web
  mode; do not pretend simple chat is full RAG or general intelligence.
- Bilingual by design: Arabic support is part of the core workflow, not a
  decorative language toggle.
- Calm MVP discipline: improve the capture -> transcribe -> clean -> translate
  -> chat -> note workflow before adding heavy infrastructure.

## Current phase

The project is now in a working local MVP phase, beyond the initial skeleton.

Implemented vertical slice:

1. Submit an Instagram or YouTube video URL from React.
2. Create a video record in SQLite.
3. Download/process the video locally with yt-dlp.
4. Extract audio locally with FFmpeg.
5. Transcribe audio with Whisper.
6. Save transcript data in SQLite.
7. Move processed files into a dated local library folder.
8. Display saved videos, video details, local playback, and transcript in React.
9. Edit video title, description, and transcript text.
10. Delete a saved video and its local library folder.
11. Ask basic transcript-grounded questions through a non-vector, local chat service.
12. Save YouTube videos through the same local pipeline, with an optional
    duration guard controlled by `MYINSTA_MAX_YOUTUBE_DURATION_SECONDS`.

Current focus:

- Stabilize and polish the local MVP.
- Keep docs aligned with implemented API/UI behavior.
- Improve reliability, error handling, and test coverage.
- Do not start vector DB/RAG infrastructure until the local MVP is clean.

## Tech stack

- Frontend: React, Vite, plain CSS
- Backend: FastAPI, Pydantic, SQLite, Python standard `sqlite3`
- Video download: yt-dlp
- Audio extraction: FFmpeg
- Transcription: Whisper
- Local app data: `backend/data/`
- Local library: `backend/data/library/YYYY/MM/{timestamp_slug}/`
- Future RAG: transcript chunking, embeddings, retrieval, then richer chat answers

## Agent roles for this profile

Hermes should usually act as project manager / senior software architect for MyInsta.

Hermes responsibilities:

- Maintain project context and this guide.
- Review architecture and API shape.
- Keep README/docs/status accurate.
- Produce Cursor-ready implementation plans and handoffs.
- Review code and identify risks before larger changes.
- Run verification commands when reviewing changes.

Cursor responsibilities:

- Direct implementation.
- Refactoring.
- Bug fixes.
- UI/code iteration.

Hermes may edit code or docs directly when the user explicitly asks, or when updating project management files such as this AGENTS.md.

## Development principles

- Keep the first production-shaped version simple and local-first.
- Prefer boring code over abstractions.
- Use SQLite directly before introducing an ORM.
- Keep API response shapes explicit with Pydantic models.
- Keep React state in component state for now; do not add Redux/Zustand yet.
- Do not add authentication, payments, cloud storage, Docker, Celery, Redis, or vector DBs until the core local workflow is stable.
- Do not commit downloaded videos, extracted audio, SQLite databases, generated library media, `.env` files, or secrets.
- Treat Instagram and YouTube downloads as personal/local prototype behavior and avoid building public-platform assumptions into the app.
- Keep YouTube support controlled: individual videos are in scope now; playlists,
  channels, and bulk ingestion should wait until chunking/retrieval and stronger
  background processing exist.

## YouTube on production VPS (proven — keep this)

Working setup as of 2026-07-13:

- Code: `/opt/myinsta`, service `myinsta.service`, API **`127.0.0.1:8010`**
- Cookies: `/home/nasser/.config/myinsta/youtube_cookies.txt`
- Cookies **must** include `LOGIN_INFO` (verify with `grep -c LOGIN_INFO ...` ≥ 1)
- Prefer small YouTube-only export (~3KB); large ~190KB dumps often lack LOGIN_INFO or are stale
- After scp, check **file size matches PC** before debugging the app
- Node **>= 22**, packages `yt-dlp[default]` + `yt-dlp-ejs`, FFmpeg on PATH
- Downloader uses CLI: `python -m yt_dlp --js-runtimes node --remote-components ejs:github --cookies ...`
- Incomplete cookies (no LOGIN_INFO) are skipped deliberately
- Diagnose: `curl -sS http://127.0.0.1:8010/health/youtube`
- Full runbook: `backend/README.md` → “YouTube downloads (proven VPS runbook)”

When YouTube fails again: re-export cookies with LOGIN_INFO → scp → CLI test → restart service. Do not change ports/clients blindly.

## Expected commands

Backend setup and run:

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Backend tests:

```bash
cd backend
source .venv/Scripts/activate
PYTHONPATH=. pytest -q
```

Note: plain `pytest` may fail with `ModuleNotFoundError: No module named 'app'` unless `PYTHONPATH=.` is set.

Frontend setup and run:

```bash
cd frontend
npm install
npm run dev
```

Frontend build verification:

```bash
cd frontend
npm run build
```

## Backend conventions

- App entry point: `backend/app/main.py`
- Routes live in: `backend/app/routes/`
- Main video routes: `backend/app/routes/videos.py`
- Pydantic API models: `backend/app/models/video.py`
- Processing services live in: `backend/app/services/`
- Database helpers live in: `backend/app/db/`
- SQLite schema source of truth: `backend/app/db/schema.sql`
- Local database path: `backend/data/myinsta.sqlite3`
- Temporary downloads: `backend/data/downloads/`
- Temporary extracted audio: `backend/data/audio/`
- Saved library root: `backend/data/library/`

Important backend services:

- `video_downloader.py`: downloads Instagram/YouTube video and metadata with yt-dlp.
- `audio_extractor.py`: extracts 16 kHz mono WAV with FFmpeg.
- `transcriber.py`: runs Whisper transcription.
- `library_storage.py`: moves processed media/transcript/metadata into the dated local library.
- `chat_service.py`: answers questions with simple transcript retrieval, not full RAG.

## Frontend conventions

- App entry point: `frontend/src/main.jsx`
- App wrapper: `frontend/src/App.jsx`
- Main page: `frontend/src/pages/HomePage.jsx`
- API wrapper: `frontend/src/api/client.js`
- Components live in: `frontend/src/components/`
- Styling: `frontend/src/styles.css`

Important frontend components:

- `UrlSubmitForm.jsx`: URL submission.
- `VideoLibrary.jsx`: saved video list grouped by month/year, with view/edit/delete actions.
- `VideoDetails.jsx`: selected video metadata.
- `VideoPlayer.jsx`: local saved video playback via backend stream URL.
- `TranscriptViewer.jsx`: transcript display.
- `VideoEditor.jsx`: edit title, description, transcript; delete video.
- `ChatPanel.jsx`: transcript-grounded chat UI and history.

## API surface

Base URL during development: `http://localhost:8000`

- `GET /health` checks backend status.
- `POST /api/videos` submits an Instagram or YouTube URL and starts processing.
- `GET /api/videos` lists recent videos.
- `GET /api/videos/{video_id}` fetches one video and transcript.
- `PATCH /api/videos/{video_id}` updates title, description, and/or transcript text.
- `DELETE /api/videos/{video_id}` deletes the DB row and local library folder.
- `GET /api/videos/{video_id}/stream` streams the saved local video file.
- `GET /api/videos/{video_id}/chat` returns saved chat history.
- `POST /api/videos/{video_id}/chat` stores a user message and returns a simple transcript-grounded assistant answer.
- `POST /api/videos/{video_id}/retry` re-runs the pipeline for a failed video.

## Data model summary

Core tables:

- `videos`: one row per submitted Instagram or YouTube video URL, including processing status, platform, metadata, local file paths, and library folder/stamp fields.
- `transcripts`: one transcript per video, with full text, language, and optional Whisper segment JSON.
- `chat_messages`: persisted user/assistant chat history for each video.

Local library layout:

```text
backend/data/library/
└── YYYY/
    └── MM/
        └── YYYYMMDD_HHMMSS_slug/
            ├── video.<ext>
            ├── audio.wav
            ├── transcript.txt
            ├── transcript.json
            └── metadata.json
```

## Generated files and git hygiene

The following should stay uncommitted:

- `backend/.env`
- `frontend/.env`
- `backend/data/*.sqlite3`
- `backend/data/downloads/*`
- `backend/data/audio/*`
- `backend/data/library/*`
- `frontend/node_modules/`
- `frontend/dist/`
- Python caches and virtualenvs

Keep `.gitkeep` files where needed to preserve empty data directories.

## Known review notes / technical debt

- Backend tests usually run via `pytest -q` from `backend/` (pytest.ini sets pythonpath).
- Docs and README may lag behind newer features; update them whenever API/UI behavior changes.
- Current chat is simple lexical transcript retrieval. Do not present it as full RAG.
- Failed videos can be reprocessed with `POST /api/videos/{id}/retry`.

## When implementing

1. Read this AGENTS.md first.
2. Read `docs/build-order.md` and update it if it no longer matches current reality.
3. Implement one small vertical slice at a time.
4. Keep backend API models, frontend API client, and docs in sync.
5. Verify backend with tests and/or `/docs`/curl.
6. Verify frontend with `npm run build` and browser testing when UI changes.
7. Keep README and docs updated when API shapes, commands, or UI behavior change.
8. Preserve local data safety: do not delete user library/media files unless the requested feature explicitly requires it.

## Recommended next work

1. Add more tests around partial pipeline failures and library file cleanup.
2. Consider subtitle/caption import for YouTube before falling back to Whisper.
3. Small UX polish: auto-dismiss backend-online banner, richer empty states.
4. Only after MVP polish, design transcript chunking and future RAG retrieval.
