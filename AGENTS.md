# MyInsta Agent Guide

This file is for Cursor, Hermes, and other coding agents working on MyInsta.

## Project summary

MyInsta is a local-first React + Vite frontend and Python FastAPI backend. Users paste an Instagram Reel/Post video link. The backend downloads/processes the video, extracts audio, transcribes speech with Whisper, saves metadata/transcripts/media references in SQLite, stores processed files in a local library, and supports simple transcript-grounded chat. Full RAG over transcript chunks is a later phase.

## Current phase

The project is now in a working local MVP phase, beyond the initial skeleton.

Implemented vertical slice:

1. Submit an Instagram video URL from React.
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
- Treat Instagram downloads as personal/local prototype behavior and avoid building public-platform assumptions into the app.

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

- `video_downloader.py`: downloads video and metadata with yt-dlp.
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
- `POST /api/videos` submits a URL and starts processing.
- `GET /api/videos` lists recent videos.
- `GET /api/videos/{video_id}` fetches one video and transcript.
- `PATCH /api/videos/{video_id}` updates title, description, and/or transcript text.
- `DELETE /api/videos/{video_id}` deletes the DB row and local library folder.
- `GET /api/videos/{video_id}/stream` streams the saved local video file.
- `GET /api/videos/{video_id}/chat` returns saved chat history.
- `POST /api/videos/{video_id}/chat` stores a user message and returns a simple transcript-grounded assistant answer.

## Data model summary

Core tables:

- `videos`: one row per submitted Instagram video URL, including processing status, metadata, local file paths, and library folder/stamp fields.
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

- `backend/app/main.py` still uses FastAPI `@app.on_event("startup")`; migrate to lifespan later.
- Backend tests require `PYTHONPATH=.`.
- Docs and README may lag behind newer features; update them whenever API/UI behavior changes.
- Current chat is simple lexical transcript retrieval. Do not present it as full RAG.
- The current project folder was observed without a `.git` repository. If version history is desired, initialize git or move work into a repo before relying on diffs.

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

1. Update README and docs to match the current local MVP feature set.
2. Add or improve tests around edit/delete/library file behavior.
3. Add user-facing failure messages for common yt-dlp, FFmpeg, and Whisper errors.
4. Consider a small backend import/test configuration cleanup so tests do not require manual `PYTHONPATH=.`.
5. Only after MVP polish, design transcript chunking and future RAG retrieval.
